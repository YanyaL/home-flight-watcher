from __future__ import annotations


def _money(price: float | int | None, currency: str) -> str:
    if price is None:
        return "—"
    return f"{currency} {round(float(price))}"


def _offer_line(offer: dict | None, currency: str | None = None) -> str:
    if not offer:
        return "无"
    cur = currency or offer.get("currency") or ""
    stops = offer.get("stops", 0)
    stop_label = "直飞" if stops == 0 else f"{stops} 停"
    flights = "+".join(
        seg.get("flight_no") or "?" for seg in (offer.get("segments") or [])
    )
    duration = offer.get("duration_min") or 0
    hours, mins = divmod(int(duration), 60)
    via = ""
    segs = offer.get("segments") or []
    if len(segs) > 1:
        vias = [s.get("dest", "?") for s in segs[:-1]]
        via = f"，经 {'/'.join(vias)}"
    book = ""
    options = offer.get("booking_options") or []
    if options and options[0].get("url"):
        book = f"\n  购买: {options[0]['url']}"
    elif offer.get("booking_url"):
        book = f"\n  购买: {offer['booking_url']}"
    return (
        f"{_money(offer.get('price'), cur)} · {stop_label} · "
        f"{hours}h{mins:02d}m · {flights}{via}{book}"
    )


def summarize_quick_search(payload: dict) -> str:
    """Short Chinese blurb for chat agents."""
    q = payload.get("query") or {}
    s = payload.get("summary") or {}
    origin = q.get("origin", "?")
    dest = q.get("dest", "?")
    date = q.get("depart_date", "?")
    currency = q.get("currency", "AUD")
    lines = [
        f"{origin} → {dest} · {date}（{q.get('provider', '?')}）",
        f"共 {s.get('total', 0)} 条：直飞 {s.get('direct_count', 0)} / "
        f"转机 {s.get('connecting_count', 0)}",
        "",
        f"最便宜直飞：{_offer_line(payload.get('cheapest_direct'), currency)}",
    ]
    connecting = payload.get("cheapest_connecting") or []
    if connecting:
        lines.append("最便宜转机 TOP：")
        for i, offer in enumerate(connecting, 1):
            lines.append(f"  {i}. {_offer_line(offer, currency)}")
    elif int(q.get("max_stops") or 0) >= 1:
        lines.append("最便宜转机：无符合条件的航班")
    return "\n".join(lines)


def summarize_dashboard(payload: dict) -> str:
    """Short Chinese blurb for monitor status."""
    cfg = payload.get("config") or {}
    snap = payload.get("snapshot")
    currency = cfg.get("currency", "AUD")
    origins = "/".join(cfg.get("origins") or []) or "?"
    dests = "/".join(cfg.get("destinations") or []) or "?"
    lines = [
        f"监测航线 {origins} → {dests}",
        f"日期 {cfg.get('date_from', '?')} → {cfg.get('date_to', '?')} · "
        f"预算 {_money(cfg.get('budget'), currency)} · provider={cfg.get('provider', '?')}",
    ]
    if snap:
        lines.append(
            f"最近扫描 #{snap.get('id')} · {snap.get('scanned_at')} · "
            f"{snap.get('offer_count', 0)} 条 · {snap.get('provider')}"
        )
    else:
        lines.append("尚未扫描，请在网页点「立刻扫票」或运行 manage.py scan")

    best = payload.get("best")
    cheapest = payload.get("cheapest")
    lines.append(f"性价比首选：{_offer_line(best, currency)}")
    lines.append(f"最便宜：{_offer_line(cheapest, currency)}")

    alerts = payload.get("alerts") or []
    if alerts:
        lines.append("最近告警：")
        for item in alerts[:3]:
            lines.append(f"  - {item.get('message', '')}")
    return "\n".join(lines)


def wants_agent_format(request, body: dict | None = None) -> bool:
    """True when query/body asks for agent-friendly summary."""
    fmt = (request.query_params.get("format") or "").strip().lower()
    if fmt == "agent":
        return True
    if body and str(body.get("format") or "").strip().lower() == "agent":
        return True
    return False
