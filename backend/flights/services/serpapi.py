from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Iterable
from urllib.parse import quote

import httpx

from .config import AppConfig
from .dto import FlightOfferDTO, Segment


CABIN_MAP = {
    "ECONOMY": "1",
    "PREMIUM_ECONOMY": "2",
    "BUSINESS": "3",
    "FIRST": "4",
}
STOPS_MAP = {
    0: "1",
    1: "2",
    2: "3",
}
FLIGHT_NO_RE = re.compile(r"^([A-Z0-9]{2})\s*(\d+)$", re.I)


class SerpApiProvider:
    """Google Flights via SerpAPI. One HTTP call = one origin/dest/date."""

    name = "serpapi"

    def __init__(self, api_key: str = "", date_step_days: int = 3) -> None:
        self.api_key = api_key
        self.date_step_days = max(1, date_step_days)

    def search(self, cfg: AppConfig) -> list[FlightOfferDTO]:
        if not self.api_key:
            raise RuntimeError("未配置 SERPAPI_API_KEY，请到 https://serpapi.com 注册免费 Key")
        offers: list[FlightOfferDTO] = []
        dates = list(_sample_dates(cfg.routes.date_from, cfg.routes.date_to, self.date_step_days))
        planned = len(cfg.routes.origins) * len(cfg.routes.destinations) * len(dates)
        print(
            f"SerpAPI 计划查询 {planned} 次 "
            f"（{len(cfg.routes.origins)} 出发 × {len(cfg.routes.destinations)} 到达 × {len(dates)} 天，"
            f"步长 {self.date_step_days} 天）。免费档约 100 次/月，请省着用。"
        )
        with httpx.Client(timeout=60) as client:
            for origin in cfg.routes.origins:
                for dest in cfg.routes.destinations:
                    for day in dates:
                        offers.extend(self.search_day(cfg, origin, dest, day, client=client))
        return offers

    def search_day(
        self,
        cfg: AppConfig,
        origin: str,
        dest: str,
        day: date,
        client: httpx.Client | None = None,
    ) -> list[FlightOfferDTO]:
        """One origin/dest/date unit — used by progressive ScanJob runner."""
        if not self.api_key:
            raise RuntimeError("未配置 SERPAPI_API_KEY，请到 https://serpapi.com 注册免费 Key")
        owns_client = client is None
        http = client or httpx.Client(timeout=60)
        try:
            return self._search_one(http, cfg, origin, dest, day)
        finally:
            if owns_client:
                http.close()

    def attach_booking_links(
        self,
        offers: list[FlightOfferDTO],
        cfg: AppConfig,
        limit: int = 8,
    ) -> list[FlightOfferDTO]:
        """Resolve Google Flights booking_token into clickable purchase links."""
        if not self.api_key:
            return offers
        with httpx.Client(timeout=60) as client:
            for offer in offers[:limit]:
                if not offer.booking_token:
                    continue
                options = self._booking_options(client, cfg, offer)
                offer.booking_options = options
                if options:
                    offer.booking_url = options[0]["url"]
        return offers

    def _search_one(
        self,
        client: httpx.Client,
        cfg: AppConfig,
        origin: str,
        dest: str,
        day: date,
    ) -> list[FlightOfferDTO]:
        params = _base_params(cfg, origin, dest, day, self.api_key)
        try:
            response = client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            print(f"SerpAPI 查询失败 {origin}-{dest} {day}: {exc}")
            return []
        if payload.get("error"):
            print(f"SerpAPI 返回错误 {origin}-{dest} {day}: {payload['error']}")
            return []
        rows = list(payload.get("best_flights") or []) + list(payload.get("other_flights") or [])
        offers = [
            _to_offer(item, origin, dest, day, cfg.traveler.currency) for item in rows
        ]
        return [offer for offer in offers if offer is not None][:8]

    def _booking_options(
        self,
        client: httpx.Client,
        cfg: AppConfig,
        offer: FlightOfferDTO,
    ) -> list[dict]:
        params = _base_params(
            cfg,
            offer.origin,
            offer.dest,
            date.fromisoformat(offer.depart_date),
            self.api_key,
        )
        params["booking_token"] = offer.booking_token
        try:
            response = client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            print(f"购买链接查询失败 {offer.offer_id}: {exc}")
            return []
        if payload.get("error"):
            print(f"购买链接返回错误 {offer.offer_id}: {payload['error']}")
            return []
        return _extract_booking_options(payload.get("booking_options") or [])


def _base_params(
    cfg: AppConfig,
    origin: str,
    dest: str,
    day: date,
    api_key: str,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": origin,
        "arrival_id": dest,
        "outbound_date": day.isoformat(),
        "type": "2",
        "currency": cfg.traveler.currency,
        "hl": "en",
        "gl": "au",
        "adults": cfg.traveler.adults,
        "travel_class": CABIN_MAP.get(cfg.traveler.cabin, "1"),
        "sort_by": "2",
    }
    stops = STOPS_MAP.get(cfg.filters.max_stops)
    if stops:
        params["stops"] = stops
    if cfg.filters.max_duration_hours:
        params["max_duration"] = cfg.filters.max_duration_hours * 60
    return params


def _to_offer(
    item: dict,
    origin: str,
    dest: str,
    day: date,
    currency: str,
) -> FlightOfferDTO | None:
    price = item.get("price")
    if price is None:
        return None
    raw_flights = item.get("flights") or []
    if not raw_flights:
        return None
    segments: list[Segment] = []
    airlines: list[str] = []
    for seg in raw_flights:
        airline, flight_no = _parse_flight_no(seg.get("flight_number", ""), seg.get("airline", ""))
        airlines.append(airline)
        segments.append(
            Segment(
                origin=seg["departure_airport"]["id"],
                dest=seg["arrival_airport"]["id"],
                depart=_parse_dt(seg["departure_airport"]["time"]),
                arrive=_parse_dt(seg["arrival_airport"]["time"]),
                airline=airline,
                flight_no=flight_no,
            )
        )
    duration = int(
        item.get("total_duration")
        or sum(int(seg.get("duration") or 0) for seg in raw_flights)
    )
    token = item.get("booking_token") or ""
    offer_id = (
        f"serpapi-{origin}{dest}-{day.isoformat()}-"
        f"{'-'.join(s.flight_no for s in segments)}"
    )
    return FlightOfferDTO(
        offer_id=offer_id,
        origin=origin,
        dest=dest,
        depart_date=day.isoformat(),
        price=float(price),
        currency=currency,
        stops=max(len(segments) - 1, 0),
        duration_min=duration,
        airlines=airlines,
        segments=segments,
        provider="serpapi",
        booking_token=token,
        booking_url=_google_flights_url(origin, dest, day.isoformat(), currency),
    )


def _extract_booking_options(raw_options: list[dict]) -> list[dict]:
    parsed: list[dict] = []
    for option in raw_options:
        tickets: list[dict] = []
        together = option.get("together")
        if together and together.get("booking_request"):
            tickets.append(together)
        elif option.get("departing", {}).get("booking_request"):
            tickets.append(option["departing"])
        for ticket in tickets:
            request = ticket.get("booking_request") or {}
            url = _clickable_booking_url(request.get("url", ""), request.get("post_data", ""))
            if not url:
                continue
            parsed.append(
                {
                    "book_with": ticket.get("book_with")
                    or (together.get("book_with") if together else "Unknown"),
                    "price": ticket.get("price"),
                    "airline": bool(ticket.get("airline")),
                    "url": url,
                }
            )
    parsed.sort(key=lambda item: (item.get("price") is None, item.get("price") or 10**9))
    # Prefer airline official first among same-ish prices, keep top few
    parsed.sort(key=lambda item: (0 if item.get("airline") else 1, item.get("price") or 10**9))
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in parsed:
        key = f"{item.get('book_with')}|{item.get('price')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:5]


def _clickable_booking_url(base_url: str, post_data: str) -> str:
    if not base_url:
        return ""
    if not post_data:
        return base_url
    # SerpAPI/community pattern: append POST body as query so it becomes a GET deeplink.
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}{post_data}"


def _parse_flight_no(flight_number: str, airline_name: str) -> tuple[str, str]:
    cleaned = (flight_number or "").strip().upper()
    match = FLIGHT_NO_RE.match(cleaned)
    if match:
        code = match.group(1)
        return code, f"{code}{match.group(2)}"
    fallback = re.sub(r"[^A-Z0-9]", "", (airline_name or "XX").upper())[:2] or "XX"
    digits = re.sub(r"\D", "", cleaned) or "0"
    return fallback, f"{fallback}{digits}"


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def _sample_dates(start: str, end: str, step_days: int) -> Iterable[date]:
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while current <= last:
        yield current
        current += timedelta(days=step_days)


def _google_flights_url(origin: str, dest: str, day: str, currency: str) -> str:
    query = quote(f"One way flights from {origin} to {dest} on {day}")
    curr = currency.upper()
    return (
        f"https://www.google.com/travel/flights?hl=en&gl=au&curr={curr}&q={query}"
    )
