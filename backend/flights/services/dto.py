from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Segment(BaseModel):
    origin: str
    dest: str
    depart: datetime
    arrive: datetime
    airline: str
    flight_no: str


class FlightOfferDTO(BaseModel):
    offer_id: str
    origin: str
    dest: str
    depart_date: str
    price: float
    currency: str
    stops: int
    duration_min: int
    airlines: list[str]
    segments: list[Segment]
    provider: str
    booking_url: str = ""
    booking_token: str = ""
    booking_options: list[dict] = Field(default_factory=list)
    score: float = 0.0
    badges: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    quality: str = "ok"
    vibe: str = "npc"
    vibe_zh: str = "NPC"
    vibe_en: str = "NPC ENERGY"
    vibe_blurb: str = ""
    vibe_blurb_en: str = ""

    @property
    def depart_at(self) -> datetime:
        return self.segments[0].depart

    @property
    def arrive_at(self) -> datetime:
        return self.segments[-1].arrive

    @property
    def via_airports(self) -> list[str]:
        return [seg.dest for seg in self.segments[:-1]]


class CalendarCell(BaseModel):
    date: str
    min_price: float | None
    offer_id: str | None = None
    origin: str | None = None
    dest: str | None = None
    stops: int | None = None


class AlertDTO(BaseModel):
    created_at: str
    kind: str
    message: str
    offer_id: str | None = None
    price: float | None = None


class ScanSummary(BaseModel):
    scanned_at: str
    provider: str
    offer_count: int
    kept_count: int
    cheapest: FlightOfferDTO | None = None
    best: FlightOfferDTO | None = None
    alerts: list[AlertDTO] = Field(default_factory=list)
