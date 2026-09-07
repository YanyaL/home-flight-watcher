from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .config import EnvSettings
from .dto import AlertDTO, FlightOfferDTO


def detect_alerts(
    offers: list[FlightOfferDTO],
    previous: dict[tuple[str, str, str], float],
    budget: float,
    drop_percent: float,
) -> list[AlertDTO]:
    now = datetime.now(timezone.utc).isoformat()
    alerts: list[AlertDTO] = []

    for offer in offers:
        key = (offer.origin, offer.dest, offer.depart_date)
        old = previous.get(key)
        if old and offer.price <= old * (1 - drop_percent / 100):
            alerts.append(
                AlertDTO(
                    created_at=now,
                    kind="price_drop",
                    message=(
                        f"{offer.origin}→{offer.dest} {offer.depart_date} "
                        f"从 {old:.0f} 降到 {offer.price:.0f} {offer.currency}"
                    ),
                    offer_id=offer.offer_id,
                    price=offer.price,
                )
            )

    under_budget = sorted(
        (offer for offer in offers if offer.price <= budget),
        key=lambda item: item.price,
    )[:3]
    for offer in under_budget:
        alerts.append(
            AlertDTO(
                created_at=now,
                kind="under_budget",
                message=(
                    f"{offer.origin}→{offer.dest} {offer.depart_date} "
                    f"{offer.price:.0f} {offer.currency} 已进入预算"
                ),
                offer_id=offer.offer_id,
                price=offer.price,
            )
        )
    return alerts[:12]


def notify(alerts: list[AlertDTO], settings: EnvSettings) -> None:
    if not alerts:
        return
    for alert in alerts:
        print(f"[{alert.kind}] {alert.message}")
    if settings.telegram_bot_token and settings.telegram_chat_id:
        text = "回国机票提醒\n" + "\n".join(f"• {item.message}" for item in alerts[:8])
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        try:
            httpx.post(
                url,
                json={"chat_id": settings.telegram_chat_id, "text": text},
                timeout=15,
            )
        except httpx.HTTPError as exc:
            print(f"Telegram 发送失败: {exc}")
