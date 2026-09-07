from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import quote

from .config import AppConfig
from .dto import FlightOfferDTO, Segment

ITINERARIES: list[dict] = [
    {"origin": "BNE", "dest": "PVG", "airlines": ["CZ"], "duration": 640, "hub": None},
    {"origin": "BNE", "dest": "PVG", "airlines": ["MU"], "duration": 620, "hub": None},
    {"origin": "BNE", "dest": "PVG", "airlines": ["CZ", "CZ"], "duration": 800, "hub": "CAN"},
    {"origin": "BNE", "dest": "PVG", "airlines": ["VJ", "VJ"], "duration": 1640, "hub": "SGN"},
    {"origin": "SYD", "dest": "PVG", "airlines": ["MU"], "duration": 675, "hub": None},
    {"origin": "MEL", "dest": "PVG", "airlines": ["CZ"], "duration": 670, "hub": None},
]


class MockProvider:
    name = "mock"

    def search(self, cfg: AppConfig) -> list[FlightOfferDTO]:
        dates = list(_daterange(cfg.routes.date_from, cfg.routes.date_to))
        offers: list[FlightOfferDTO] = []
        for day in dates:
            for origin in cfg.routes.origins:
                for dest in cfg.routes.destinations:
                    offers.extend(self.search_day(cfg, origin, dest, day))
        return offers

    def search_day(
        self,
        cfg: AppConfig,
        origin: str,
        dest: str,
        day: date,
        client=None,  # noqa: ANN001 - parity with SerpAPI signature
    ) -> list[FlightOfferDTO]:
        wanted_origins = {origin.upper()}
        wanted_dests = {dest.upper()}
        templates = [
            item
            for item in ITINERARIES
            if item["origin"] in wanted_origins and item["dest"] in wanted_dests
        ]
        if not templates:
            templates = [
                {
                    "origin": origin.upper(),
                    "dest": dest.upper(),
                    "airlines": ["SQ", "SQ"],
                    "duration": 1100,
                    "hub": "SIN",
                }
            ]
        return [
            _build_offer(template, day, cfg.traveler.currency) for template in templates
        ]

    def attach_booking_links(
        self,
        offers: list[FlightOfferDTO],
        cfg: AppConfig,
        limit: int = 8,
    ) -> list[FlightOfferDTO]:
        return offers


def _daterange(start: str, end: str) -> Iterable[date]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while current <= last:
        yield current
        current += timedelta(days=1)


def _build_offer(template: dict, day: date, currency: str) -> FlightOfferDTO:
    origin = template["origin"]
    dest = template["dest"]
    airlines: list[str] = template["airlines"]
    duration = int(template["duration"])
    hub = template["hub"]
    seed = _seed(origin, dest, day.isoformat(), "".join(airlines))
    price = _price_for(origin, dest, day, airlines, 0 if hub is None else 1)
    depart_hour = 8 + (seed % 12)
    depart = datetime(day.year, day.month, day.day, depart_hour, (seed * 7) % 60)
    arrive = depart + timedelta(minutes=duration)
    segments = _segments(origin, dest, hub, airlines, depart, arrive, duration, seed)
    offer_id = f"mock-{origin}{dest}-{day.isoformat()}-{''.join(airlines)}"
    query = quote(f"One way flights from {origin} to {dest} on {day.isoformat()}")
    return FlightOfferDTO(
        offer_id=offer_id,
        origin=origin,
        dest=dest,
        depart_date=day.isoformat(),
        price=price,
        currency=currency,
        stops=0 if hub is None else 1,
        duration_min=duration,
        airlines=airlines,
        segments=segments,
        provider="mock",
        booking_url=f"https://www.google.com/travel/flights?hl=en&gl=au&curr={currency}&q={query}",
        booking_options=[
            {
                "book_with": airlines[0],
                "price": price,
                "airline": True,
                "url": f"https://www.google.com/travel/flights?hl=en&gl=au&curr={currency}&q={query}",
            }
        ],
    )


def _segments(
    origin: str,
    dest: str,
    hub: str | None,
    airlines: list[str],
    depart: datetime,
    arrive: datetime,
    duration: int,
    seed: int,
) -> list[Segment]:
    if hub is None:
        return [
            Segment(
                origin=origin,
                dest=dest,
                depart=depart,
                arrive=arrive,
                airline=airlines[0],
                flight_no=f"{airlines[0]}{100 + seed % 800}",
            )
        ]
    first_leg = max(180, int(duration * 0.45))
    layover = 90 + (seed % 80)
    mid = depart + timedelta(minutes=first_leg)
    second_depart = mid + timedelta(minutes=layover)
    return [
        Segment(
            origin=origin,
            dest=hub,
            depart=depart,
            arrive=mid,
            airline=airlines[0],
            flight_no=f"{airlines[0]}{200 + seed % 700}",
        ),
        Segment(
            origin=hub,
            dest=dest,
            depart=second_depart,
            arrive=arrive,
            airline=airlines[-1],
            flight_no=f"{airlines[-1]}{300 + seed % 600}",
        ),
    ]


def _price_for(origin: str, dest: str, day: date, airlines: list[str], stops: int) -> float:
    base = 780 + _seed(origin, dest, "base", "") % 220
    if stops == 0:
        base += 90
    if day.weekday() in (1, 2):
        base *= 0.86
    elif day.weekday() in (4, 5, 6):
        base *= 1.11
    noise = (_seed(origin, dest, day.isoformat(), "".join(airlines)) % 160) - 70
    wave = 35 * math.sin(day.toordinal() / 6 + _seed(origin, dest, "wave", "") % 7)
    drift = 18 * math.sin(datetime.now(timezone.utc).timestamp() / 3600)
    return round(max(489.0, base + noise + wave + drift), 0)


def _seed(*parts: str) -> int:
    raw = hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()
    return int(raw[:8], 16)
