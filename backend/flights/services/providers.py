from __future__ import annotations

from .mock import MockProvider
from .serpapi import SerpApiProvider


def get_provider(name: str, **kwargs):
    if name == "serpapi":
        return SerpApiProvider(
            api_key=kwargs.get("api_key", ""),
            date_step_days=int(kwargs.get("date_step_days", 7)),
        )
    if name == "mock":
        return MockProvider()
    raise ValueError(f"未知数据源: {name}")
