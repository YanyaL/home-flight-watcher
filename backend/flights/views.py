from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.agent_summary import (
    summarize_dashboard,
    summarize_quick_search,
    wants_agent_format,
)
from .services.quick_search import quick_search
from .services.scanner import dashboard_payload, history_payload, run_scan

# Future: if AGENT_API_TOKEN is set in .env, require header X-Agent-Token here.
# Plugins should send the same value via FLIGHT_WATCHER_API_TOKEN.


@api_view(["GET"])
def dashboard(request):
    payload = dashboard_payload()
    if wants_agent_format(request):
        payload["agent_summary"] = summarize_dashboard(payload)
    return Response(payload)


@api_view(["POST"])
def scan(request):
    summary = run_scan()
    payload = dashboard_payload()
    payload["scan"] = summary.model_dump(mode="json")
    if wants_agent_format(request, request.data if isinstance(request.data, dict) else None):
        payload["agent_summary"] = summarize_dashboard(payload)
    return Response(payload)


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
