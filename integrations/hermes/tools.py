"""Hermes tool handlers — thin HTTP wrappers around Django."""

from __future__ import annotations

import json

from . import client


def flight_quick_search(args: dict, **kwargs) -> str:
    ctx = kwargs.get("ctx")
    try:
        base = client.api_base(ctx)
        body = {
            "origin": str(args.get("origin") or "").strip().upper(),
            "dest": str(args.get("dest") or "").strip().upper(),
            "depart_date": str(args.get("depart_date") or "").strip(),
            "max_stops": int(args.get("max_stops", 1)),
            "connecting_limit": int(args.get("connecting_limit", 3)),
            "format": "agent",
        }
        if not body["origin"] or not body["dest"] or not body["depart_date"]:
            return json.dumps({"error": "Need origin, dest, and depart_date"})
        payload = client.http_json(
            "POST",
            f"{base}/api/quick-search?format=agent",
            body,
        )
        return json.dumps(
            {
                "agent_summary": payload.get("agent_summary"),
                "query": payload.get("query"),
                "summary": payload.get("summary"),
                "cheapest_direct": payload.get("cheapest_direct"),
                "cheapest_connecting": payload.get("cheapest_connecting"),
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def flight_scan_status(args: dict, **kwargs) -> str:
    ctx = kwargs.get("ctx")
    try:
        base = client.api_base(ctx)
        payload = client.http_json("GET", f"{base}/api/dashboard?format=agent")
        return json.dumps(
            {
                "agent_summary": payload.get("agent_summary"),
                "snapshot": payload.get("snapshot"),
                "config": {
                    "origins": (payload.get("config") or {}).get("origins"),
                    "destinations": (payload.get("config") or {}).get("destinations"),
                    "date_from": (payload.get("config") or {}).get("date_from"),
                    "date_to": (payload.get("config") or {}).get("date_to"),
                    "budget": (payload.get("config") or {}).get("budget"),
                    "currency": (payload.get("config") or {}).get("currency"),
                    "provider": (payload.get("config") or {}).get("provider"),
                },
                "best": payload.get("best"),
                "cheapest": payload.get("cheapest"),
                "alerts": (payload.get("alerts") or [])[:5],
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
