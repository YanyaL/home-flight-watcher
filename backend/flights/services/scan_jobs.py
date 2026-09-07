from __future__ import annotations

import threading
from datetime import date, datetime, timedelta, timezone

from django.db import close_old_connections, transaction

from flights.models import ScanJob, ScanTask

from .alerts import detect_alerts, notify
from .config import AppConfig, load_config, load_settings
from .dto import FlightOfferDTO
from .providers import get_provider
from .scanner import previous_min_prices, save_snapshot
from .scoring import apply_filters, score_offers

_ACTIVE_THREADS: dict[int, threading.Thread] = {}
_LOCK = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sample_dates(start: str, end: str, step_days: int) -> list[date]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    step = max(1, int(step_days))
    days: list[date] = []
    while current <= last:
        days.append(current)
        current += timedelta(days=step)
    return days


def create_scan_job(attach_bookings: bool = True) -> ScanJob:
    cfg = load_config()
    settings = load_settings()
    step = max(1, cfg.watcher.serpapi_date_step_days)
    dates = _sample_dates(cfg.routes.date_from, cfg.routes.date_to, step)

    with transaction.atomic():
        job = ScanJob.objects.create(
            status=ScanJob.STATUS_PENDING,
            attach_bookings=attach_bookings,
            provider=settings.flight_provider,
        )
        ScanTask.objects.bulk_create(
            [
                ScanTask(
                    job=job,
                    origin=origin,
                    dest=dest,
                    depart_date=day,
                )
                for origin in cfg.routes.origins
                for dest in cfg.routes.destinations
                for day in dates
            ]
        )
    return job


def start_scan_job(job_id: int) -> None:
    with _LOCK:
        existing = _ACTIVE_THREADS.get(job_id)
        if existing and existing.is_alive():
            return
        thread = threading.Thread(
            target=_run_job_worker,
            args=(job_id,),
            name=f"scan-job-{job_id}",
            daemon=True,
        )
        _ACTIVE_THREADS[job_id] = thread
        thread.start()


def request_cancel(job_id: int) -> ScanJob:
    job = ScanJob.objects.get(pk=job_id)
    if job.status in {
        ScanJob.STATUS_COMPLETED,
        ScanJob.STATUS_CANCELLED,
        ScanJob.STATUS_FAILED,
    }:
        return job
    job.cancel_requested = True
    job.save(update_fields=["cancel_requested"])
    return job


def retry_failed_tasks(job_id: int) -> ScanJob:
    job = ScanJob.objects.get(pk=job_id)
    failed = job.tasks.filter(status=ScanTask.STATUS_FAILED)
    if not failed.exists():
        return job
    failed.update(
        status=ScanTask.STATUS_PENDING,
        error_message="",
        result_payload=[],
        started_at=None,
        finished_at=None,
        offer_count=0,
    )
    job.status = ScanJob.STATUS_PENDING
    job.cancel_requested = False
    job.error_message = ""
    job.finished_at = None
    job.save(
        update_fields=["status", "cancel_requested", "error_message", "finished_at"]
    )
    start_scan_job(job.id)
    return job


def job_payload(job: ScanJob) -> dict:
    tasks = list(job.tasks.all())
    total = len(tasks)
    counts = {
        "pending": 0,
        "running": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for task in tasks:
        counts[task.status] = counts.get(task.status, 0) + 1
    done = counts["succeeded"] + counts["failed"] + counts["cancelled"]
    percent = round((done / total) * 100) if total else 100
    return {
        "id": job.id,
        "status": job.status,
        "provider": job.provider,
        "cancel_requested": job.cancel_requested,
        "attach_bookings": job.attach_bookings,
        "offer_count": job.offer_count,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "snapshot_id": job.snapshot_id,
        "progress": {
            "total": total,
            "done": done,
            "percent": percent,
            **counts,
        },
        "tasks": [
            {
                "id": task.id,
                "origin": task.origin,
                "dest": task.dest,
                "depart_date": task.depart_date.isoformat(),
                "status": task.status,
                "offer_count": task.offer_count,
                "error_message": task.error_message,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            }
            for task in tasks
        ],
    }


def _run_job_worker(job_id: int) -> None:
    close_old_connections()
    try:
        job = ScanJob.objects.get(pk=job_id)
        cfg = load_config()
        settings = load_settings()
        provider = get_provider(
            settings.flight_provider,
            api_key=settings.serpapi_api_key,
            date_step_days=cfg.watcher.serpapi_date_step_days,
        )
        job.status = ScanJob.STATUS_RUNNING
        job.started_at = job.started_at or _utcnow()
        job.provider = provider.name
        job.save(update_fields=["status", "started_at", "provider"])

        while True:
            close_old_connections()
            job.refresh_from_db()
            if job.cancel_requested:
                job.tasks.filter(status=ScanTask.STATUS_PENDING).update(
                    status=ScanTask.STATUS_CANCELLED,
                    finished_at=_utcnow(),
                    error_message="已取消",
                )
                # Still finalize whatever succeeded so far.
                _finalize_job(job, provider, cfg, settings)
                job.refresh_from_db()
                if job.status == ScanJob.STATUS_COMPLETED:
                    job.status = ScanJob.STATUS_CANCELLED
                    job.save(update_fields=["status"])
                break

            task = (
                job.tasks.filter(status=ScanTask.STATUS_PENDING).order_by("id").first()
            )
            if task is None:
                _finalize_job(job, provider, cfg, settings)
                break

            task.status = ScanTask.STATUS_RUNNING
            task.started_at = _utcnow()
            task.save(update_fields=["status", "started_at"])
            try:
                day_offers = provider.search_day(
                    cfg, task.origin, task.dest, task.depart_date
                )
                task.status = ScanTask.STATUS_SUCCEEDED
                task.offer_count = len(day_offers)
                task.result_payload = [
                    offer.model_dump(mode="json") for offer in day_offers
                ]
                task.error_message = ""
            except Exception as exc:  # noqa: BLE001
                task.status = ScanTask.STATUS_FAILED
                task.offer_count = 0
                task.result_payload = []
                task.error_message = str(exc)[:500]
            task.finished_at = _utcnow()
            task.save(
                update_fields=[
                    "status",
                    "offer_count",
                    "result_payload",
                    "error_message",
                    "finished_at",
                ]
            )

    except Exception as exc:  # noqa: BLE001
        close_old_connections()
        ScanJob.objects.filter(pk=job_id).update(
            status=ScanJob.STATUS_FAILED,
            error_message=str(exc)[:500],
            finished_at=_utcnow(),
        )
    finally:
        close_old_connections()
        with _LOCK:
            _ACTIVE_THREADS.pop(job_id, None)


def _finalize_job(
    job: ScanJob,
    provider,
    cfg: AppConfig,
    settings,
) -> None:
    job.refresh_from_db()
    offers: list[FlightOfferDTO] = []
    for task in job.tasks.filter(status=ScanTask.STATUS_SUCCEEDED):
        for row in task.result_payload or []:
            offers.append(FlightOfferDTO.model_validate(row))

    by_id = {offer.offer_id: offer for offer in offers}
    offers = list(by_id.values())
    kept = score_offers(apply_filters(offers, cfg), cfg)
    if job.attach_bookings and hasattr(provider, "attach_booking_links") and kept:
        shortlist = kept[: cfg.watcher.booking_link_limit]
        provider.attach_booking_links(shortlist, cfg, limit=len(shortlist))

    previous = previous_min_prices()
    alerts = detect_alerts(
        kept,
        previous,
        budget=cfg.traveler.budget,
        drop_percent=cfg.watcher.alert_on_drop_percent,
    )
    snapshot = save_snapshot(kept, provider.name, alerts)
    notify(alerts, settings)

    failed_count = job.tasks.filter(status=ScanTask.STATUS_FAILED).count()
    cancelled = job.cancel_requested
    job.snapshot = snapshot
    job.offer_count = len(kept)
    job.finished_at = _utcnow()
    if cancelled:
        job.status = ScanJob.STATUS_CANCELLED
        job.error_message = "用户取消；已保存已完成部分"
    elif failed_count and job.tasks.filter(status=ScanTask.STATUS_SUCCEEDED).exists():
        job.status = ScanJob.STATUS_COMPLETED
        job.error_message = f"{failed_count} 个任务失败，可单独重试"
    elif failed_count:
        job.status = ScanJob.STATUS_FAILED
        job.error_message = "全部任务失败"
    else:
        job.status = ScanJob.STATUS_COMPLETED
        job.error_message = ""
    job.save(
        update_fields=[
            "snapshot",
            "offer_count",
            "finished_at",
            "status",
            "error_message",
        ]
    )
