from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from django.conf import settings
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(settings.BASE_DIR).parent

Cabin = Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]
TripType = Literal["one_way", "round_trip"]
ProviderName = Literal["mock", "serpapi"]


class TravelerConfig(BaseModel):
    currency: str = "AUD"
    cabin: Cabin = "ECONOMY"
    adults: int = 1
    budget: float = 1200


class RoutesConfig(BaseModel):
    origins: list[str]
    destinations: list[str]
    date_from: str
    date_to: str
    trip_type: TripType = "one_way"

    @field_validator("origins", "destinations")
    @classmethod
    def upper_codes(cls, value: list[str]) -> list[str]:
        return [item.upper() for item in value]


class FiltersConfig(BaseModel):
    max_stops: int = 1
    max_duration_hours: int = 32
    preferred_airlines: list[str] = Field(default_factory=list)
    banned_airlines: list[str] = Field(default_factory=list)

    @field_validator("preferred_airlines", "banned_airlines")
    @classmethod
    def upper_codes(cls, value: list[str]) -> list[str]:
        return [item.upper() for item in value]


class WatcherConfig(BaseModel):
    interval_minutes: int = 720
    alert_on_drop_percent: float = 8
    serpapi_date_step_days: int = 7
    booking_link_limit: int = 8


class ScoringConfig(BaseModel):
    price: float = 0.55
    duration: float = 0.20
    stops: float = 0.15
    convenience: float = 0.10


class AppConfig(BaseModel):
    traveler: TravelerConfig
    routes: RoutesConfig
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    flight_provider: ProviderName = "mock"
    serpapi_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or Path(settings.WATCH_CONFIG_PATH)
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def load_settings() -> EnvSettings:
    return EnvSettings()
