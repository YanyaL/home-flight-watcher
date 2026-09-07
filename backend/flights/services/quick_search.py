from __future__ import annotations

from datetime import date

from .config import AppConfig, load_config, load_settings
from .dto import FlightOfferDTO
from .providers import get_provider


def quick_search(
    origin: str,
    dest: str,
    depart_date: str,
    max_stops: int = 1,
    connecting_limit: int = 3,
    currency: str | None = None,
) -> dict:
    """One-shot search shaped for the common user query.

    Returns:
    - cheapest_direct: single cheapest nonstop (or null)
    - cheapest_connecting: up to N cheapest flights with 1..max_stops stops
    """
    origin = origin.upper().strip()
    dest = dest.upper().strip()
    max_stops = max(0, min(int(max_stops), 2))
    connecting_limit = max(1, min(int(connecting_limit), 10))
    # Validate date early
    date.fromisoformat(depart_date)

    cfg = load_config()
    settings = load_settings()
    cfg.routes.origins = [origin]
    cfg.routes.destinations = [dest]
    cfg.routes.date_from = depart_date
    cfg.routes.date_to = depart_date
    cfg.filters.max_stops = max_stops
    cfg.watcher.serpapi_date_step_days = 1
    if currency:
        cfg.traveler.currency = currency.upper()

    provider = get_provider(
        settings.flight_provider,
        api_key=settings.serpapi_api_key,
        date_step_days=1,
    )
    raw = provider.search(cfg)
    # Soft local filter in case provider returns extras
    offers = [o for o in raw if o.stops <= max_stops]
    offers.sort(key=lambda item: (item.price, item.duration_min))

    direct = [o for o in offers if o.stops == 0]
    connecting = [o for o in offers if 1 <= o.stops <= max_stops]

    cheapest_direct = direct[0] if direct else None
    cheapest_connecting = connecting[:connecting_limit] if max_stops >= 1 else []

    shortlist: list[FlightOfferDTO] = []
    if cheapest_direct:
        shortlist.append(cheapest_direct)
    shortlist.extend(cheapest_connecting)

    if hasattr(provider, "attach_booking_links"):
        provider.attach_booking_links(shortlist, cfg, limit=len(shortlist))

    from .quality import annotate_offers_quality, quality_summary

    annotate_offers_quality(shortlist, cfg)
    # Keep full list lightly annotated for summary counts (no booking required).
    annotate_offers_quality(offers, cfg)

    payload = {
        "query": {
            "origin": origin,
            "dest": dest,
            "depart_date": depart_date,
            "max_stops": max_stops,
            "connecting_limit": connecting_limit,
            "currency": cfg.traveler.currency,
            "provider": provider.name,
        },
        "summary": {
            "total": len(offers),
            "direct_count": len(direct),
            "connecting_count": len(connecting),
        },
        "cheapest_direct": cheapest_direct.model_dump(mode="json") if cheapest_direct else None,
        "cheapest_connecting": [o.model_dump(mode="json") for o in cheapest_connecting],
        "quality": quality_summary(shortlist),
    }
    return payload
