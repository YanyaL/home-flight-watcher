from __future__ import annotations

import math

from .airports import airline_name
from .config import AppConfig
from .dto import FlightOfferDTO

STOP_SCORE = {0: 1.0, 1: 0.72, 2: 0.28}
PRICE_SCALE = 200.0
DURATION_SCALE = 180.0


def apply_filters(offers: list[FlightOfferDTO], cfg: AppConfig) -> list[FlightOfferDTO]:
    max_duration = cfg.filters.max_duration_hours * 60
    banned = set(cfg.filters.banned_airlines)
    kept: list[FlightOfferDTO] = []
    for offer in offers:
        if offer.stops > cfg.filters.max_stops:
            continue
        if offer.duration_min > max_duration:
            continue
        if offer.price > cfg.traveler.budget * 1.35:
            continue
        if banned.intersection(offer.airlines):
            continue
        kept.append(offer)
    return kept


def score_offers(offers: list[FlightOfferDTO], cfg: AppConfig) -> list[FlightOfferDTO]:
    if not offers:
        return []

    prices = [offer.price for offer in offers]
    durations = [offer.duration_min for offer in offers]
    min_price = min(prices)
    min_duration = min(durations)
    preferred = set(cfg.filters.preferred_airlines)
    weights = cfg.scoring

    for offer in offers:
        price_s = math.exp(-(offer.price - min_price) / PRICE_SCALE)
        duration_s = math.exp(-(offer.duration_min - min_duration) / DURATION_SCALE)
        stops_s = STOP_SCORE.get(offer.stops, 0.1)
        convenience = 0.35
        if preferred.intersection(offer.airlines):
            convenience += 0.35
        arrival_hour = offer.arrive_at.hour
        if 8 <= arrival_hour <= 22:
            convenience += 0.30
        elif 6 <= arrival_hour <= 23:
            convenience += 0.12
        convenience = min(convenience, 1.0)
        offer.score = round(
            (
                weights.price * price_s
                + weights.duration * duration_s
                + weights.stops * stops_s
                + weights.convenience * convenience
            )
            * 100,
            1,
        )
        offer.badges = _badges(offer, cfg, min_price)
    scored = sorted(offers, key=lambda item: (-item.score, item.price))
    return scored


def _badges(offer: FlightOfferDTO, cfg: AppConfig, cheapest: float) -> list[str]:
    badges: list[str] = []
    if offer.price <= cfg.traveler.budget:
        badges.append("低于预算")
    if offer.stops == 0:
        badges.append("直飞")
    elif offer.stops == 1:
        badges.append("1次转机")
    if abs(offer.price - cheapest) < 0.5:
        badges.append("本轮最低")
    if offer.score >= 80:
        badges.append("性价比高")
    preferred = set(cfg.filters.preferred_airlines)
    if preferred.intersection(offer.airlines):
        badges.append(airline_name(offer.airlines[0]))
    return badges
