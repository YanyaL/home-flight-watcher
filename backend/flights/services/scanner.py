from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from django.db.models import Min

from flights.models import Alert, FlightOfferRecord, ScanJob, ScanSnapshot

from .airports import city_of, label_of
from .alerts import detect_alerts, notify
from .config import AppConfig, EnvSettings, load_config, load_settings
from .dto import CalendarCell, FlightOfferDTO, ScanSummary
from .providers import get_provider
from .scoring import apply_filters, score_offers


def run_scan(
    cfg: AppConfig | None = None,
    settings: EnvSettings | None = None,
    attach_bookings: bool = True,
) -> ScanSummary:
    cfg = cfg or load_config()
    settings = settings or load_settings()
    provider = get_provider(
        settings.flight_provider,
        api_key=settings.serpapi_api_key,
        date_step_days=cfg.watcher.serpapi_date_step_days,
    )
    raw = provider.search(cfg)
    kept = score_offers(apply_filters(raw, cfg), cfg)
    if attach_bookings and hasattr(provider, "attach_booking_links"):
        shortlist = kept[: cfg.watcher.booking_link_limit]
        provider.attach_booking_links(shortlist, cfg, limit=len(shortlist))
    from .quality import annotate_offers_quality

    kept = annotate_offers_quality(kept, cfg)
    previous = previous_min_prices()
    alerts = detect_alerts(
        kept,
        previous,
        budget=cfg.traveler.budget,
        drop_percent=cfg.watcher.alert_on_drop_percent,
    )
    save_snapshot(kept, provider.name, alerts)
    notify(alerts, settings)
    cheapest = min(kept, key=lambda item: item.price) if kept else None
    best = kept[0] if kept else None
    return ScanSummary(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        provider=provider.name,
        offer_count=len(raw),
        kept_count=len(kept),
        cheapest=cheapest,
        best=best,
        alerts=alerts,
    )


def dashboard_payload() -> dict:
    cfg = load_config()
    settings = load_settings()
    snapshot = ScanSnapshot.objects.first()
    offers = (
        [FlightOfferDTO.model_validate(row.payload) for row in snapshot.offers.all()]
        if snapshot
        else []
    )
    from .quality import annotate_offers_quality, quality_summary

    offers = annotate_offers_quality(offers, cfg)
    usable = [o for o in offers if o.quality != "error"] or offers
    calendar = build_calendar(cfg, offers)
    cheapest = min(usable, key=lambda item: item.price) if usable else None
    best = sorted(usable, key=lambda item: (-item.score, item.price))[0] if usable else None
    alerts = [
        {
            "created_at": item.created_at.isoformat(),
            "kind": item.kind,
            "message": item.message,
            "offer_id": item.offer_id or None,
            "price": item.price,
        }
        for item in Alert.objects.all()[:20]
    ]
    from .scan_jobs import job_payload  # local import avoids circular dependency

    return {
        "config": {
            "origins": [label_of(code) for code in cfg.routes.origins],
            "destinations": [label_of(code) for code in cfg.routes.destinations],
            "date_from": cfg.routes.date_from,
            "date_to": cfg.routes.date_to,
            "budget": cfg.traveler.budget,
            "currency": cfg.traveler.currency,
            "cabin": cfg.traveler.cabin,
            "max_stops": cfg.filters.max_stops,
            "provider": settings.flight_provider,
        },
        "snapshot": (
            {
                "id": snapshot.id,
                "scanned_at": snapshot.scanned_at.isoformat(),
                "provider": snapshot.provider,
                "offer_count": snapshot.offer_count,
            }
            if snapshot
            else None
        ),
        "calendar": [cell.model_dump() for cell in calendar],
        "offers": [offer.model_dump(mode="json") for offer in offers],
        "cheapest": cheapest.model_dump(mode="json") if cheapest else None,
        "best": best.model_dump(mode="json") if best else None,
        "alerts": alerts,
        "quality": quality_summary(offers),
        "cities": {
            code: city_of(code)
            for code in cfg.routes.origins + cfg.routes.destinations
        },
        "latest_job": job_payload(ScanJob.objects.first()) if ScanJob.objects.exists() else None,
    }


def history_payload(origin: str, dest: str) -> dict:
    rows = (
        FlightOfferRecord.objects.filter(origin=origin.upper(), dest=dest.upper())
        .values("snapshot_id", "snapshot__scanned_at")
        .annotate(min_price=Min("price"))
        .order_by("snapshot_id")[:30]
    )
    points = [
        {"scanned_at": row["snapshot__scanned_at"].isoformat(), "min_price": row["min_price"]}
        for row in rows
    ]
    return {"origin": origin.upper(), "dest": dest.upper(), "points": points}


def build_calendar(cfg: AppConfig, offers: list[FlightOfferDTO]) -> list[CalendarCell]:
    by_date: dict[str, list[FlightOfferDTO]] = defaultdict(list)
    for offer in offers:
        by_date[offer.depart_date].append(offer)
    start = date.fromisoformat(cfg.routes.date_from)
    end = date.fromisoformat(cfg.routes.date_to)
    cells: list[CalendarCell] = []
    cursor = start
    while cursor <= end:
        day = cursor.isoformat()
        day_offers = by_date.get(day, [])
        if day_offers:
            winner = min(day_offers, key=lambda item: item.price)
            cells.append(
                CalendarCell(
                    date=day,
                    min_price=winner.price,
                    offer_id=winner.offer_id,
                    origin=winner.origin,
                    dest=winner.dest,
                    stops=winner.stops,
                )
            )
        else:
            cells.append(CalendarCell(date=day, min_price=None))
        cursor += timedelta(days=1)
    return cells


def previous_min_prices() -> dict[tuple[str, str, str], float]:
    rows = (
        FlightOfferRecord.objects.values("origin", "dest", "depart_date")
        .annotate(min_price=Min("price"))
    )
    return {
        (row["origin"], row["dest"], row["depart_date"].isoformat()): row["min_price"]
        for row in rows
    }


def save_snapshot(
    offers: list[FlightOfferDTO],
    provider: str,
    alerts,
) -> ScanSnapshot:
    snapshot = ScanSnapshot.objects.create(provider=provider, offer_count=len(offers))
    FlightOfferRecord.objects.bulk_create(
        [
            FlightOfferRecord(
                snapshot=snapshot,
                offer_id=offer.offer_id,
                origin=offer.origin,
                dest=offer.dest,
                depart_date=date.fromisoformat(offer.depart_date),
                price=offer.price,
                currency=offer.currency,
                stops=offer.stops,
                duration_min=offer.duration_min,
                airlines=",".join(offer.airlines),
                score=offer.score,
                payload=offer.model_dump(mode="json"),
            )
            for offer in offers
        ]
    )
    Alert.objects.bulk_create(
        [
            Alert(
                kind=alert.kind,
                message=alert.message,
                offer_id=alert.offer_id or "",
                price=alert.price,
            )
            for alert in alerts
        ]
    )
    return snapshot
