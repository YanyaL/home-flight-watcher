from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.agent_summary import (
    summarize_dashboard,
    summarize_quick_search,
    wants_agent_format,
)
from .services.fx import DISPLAY_CURRENCIES, convert_amount, get_rate_table
from .services.quick_search import quick_search
from .services.scan_jobs import (
    create_scan_job,
    job_payload,
    request_cancel,
    retry_failed_tasks,
    start_scan_job,
)
from .services.scanner import dashboard_payload, history_payload
from flights.models import ScanJob

# Future: if AGENT_API_TOKEN is set in .env, require header X-Agent-Token here.
# Plugins should send the same value via FLIGHT_WATCHER_API_TOKEN.


@api_view(["GET"])
def fx_rates(request):
    """ECB reference rates via Frankfurter (EUR pivot)."""
    try:
        force = str(request.query_params.get("refresh") or "").lower() in {"1", "true", "yes"}
        payload = get_rate_table(force_refresh=force)
    except Exception as exc:  # noqa: BLE001
        return Response({"detail": f"汇率拉取失败: {exc}"}, status=502)
    return Response(payload)


@api_view(["POST"])
def fx_convert(request):
    """Convert an amount from any supported currency to another."""
    body = request.data or {}
    try:
        amount = float(body.get("amount"))
    except (TypeError, ValueError):
        return Response({"detail": "amount 必须是数字"}, status=400)
    from_currency = str(body.get("from") or body.get("from_currency") or "").strip().upper()
    to_currency = str(body.get("to") or body.get("to_currency") or "").strip().upper()
    if not from_currency or not to_currency:
        return Response({"detail": "需要 from / to 货币代码，如 AUD → CNY"}, status=400)
    if from_currency not in DISPLAY_CURRENCIES or to_currency not in DISPLAY_CURRENCIES:
        return Response(
            {"detail": f"请使用支持的货币之一: {', '.join(DISPLAY_CURRENCIES)}"},
            status=400,
        )
    try:
        table = get_rate_table()
        converted = convert_amount(amount, from_currency, to_currency, table)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001
        return Response({"detail": f"汇率转换失败: {exc}"}, status=502)
    return Response(
        {
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
            "converted": round(converted, 2),
            "rate_date": table.get("date"),
            "source": table.get("source"),
        }
    )


@api_view(["GET"])
def dashboard(request):
    payload = dashboard_payload()
    if wants_agent_format(request):
        payload["agent_summary"] = summarize_dashboard(payload)
    return Response(payload)


@api_view(["POST"])
def scan(request):
    """Start an async progressive scan job (date × route tasks)."""
    body = request.data if isinstance(request.data, dict) else {}
    attach = body.get("attach_bookings")
    attach_bookings = True if attach is None else bool(attach)
    job = create_scan_job(attach_bookings=attach_bookings)
    start_scan_job(job.id)
    return Response(job_payload(ScanJob.objects.get(pk=job.id)), status=202)


@api_view(["GET"])
def scan_job_detail(request, job_id: int):
    try:
        job = ScanJob.objects.get(pk=job_id)
    except ScanJob.DoesNotExist:
        return Response({"detail": "扫票任务不存在"}, status=404)
    return Response(job_payload(job))


@api_view(["POST"])
def scan_job_cancel(request, job_id: int):
    try:
        job = request_cancel(job_id)
    except ScanJob.DoesNotExist:
        return Response({"detail": "扫票任务不存在"}, status=404)
    return Response(job_payload(job))


@api_view(["POST"])
def scan_job_retry(request, job_id: int):
    try:
        job = retry_failed_tasks(job_id)
    except ScanJob.DoesNotExist:
        return Response({"detail": "扫票任务不存在"}, status=404)
    return Response(job_payload(ScanJob.objects.get(pk=job.id)))


@api_view(["GET"])
def history(request):
    origin = request.query_params.get("origin", "")
    dest = request.query_params.get("dest", "")
    return Response(history_payload(origin, dest))


@api_view(["POST"])
def quick_search_view(request):
    body = request.data or {}
    origin = str(body.get("origin") or "").strip()
    dest = str(body.get("dest") or "").strip()
    depart_date = str(body.get("depart_date") or "").strip()
    if not origin or not dest or not depart_date:
        return Response(
            {"detail": "需要 origin、dest、depart_date（YYYY-MM-DD）"},
            status=400,
        )
    try:
        max_stops = int(body.get("max_stops", 1))
        connecting_limit = int(body.get("connecting_limit", 3))
    except (TypeError, ValueError):
        return Response({"detail": "max_stops / connecting_limit 必须是数字"}, status=400)

    currency = body.get("currency")
    try:
        payload = quick_search(
            origin=origin,
            dest=dest,
            depart_date=depart_date,
            max_stops=max_stops,
            connecting_limit=connecting_limit,
            currency=str(currency) if currency else None,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001 - surface provider errors to UI
        return Response({"detail": str(exc)}, status=502)

    if wants_agent_format(request, body if isinstance(body, dict) else None):
        payload["agent_summary"] = summarize_quick_search(payload)
    return Response(payload)
