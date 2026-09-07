from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

# Frankfurter serves ECB (and related) reference rates — free, no API key.
FRANKFURTER_LATEST = "https://api.frankfurter.app/latest"
FX_SOURCE = "Frankfurter (ECB reference rates)"

# Currencies exposed in the UI / convert API.
DISPLAY_CURRENCIES = [
    "AUD",
    "CNY",
    "USD",
    "EUR",
    "GBP",
    "HKD",
    "SGD",
    "JPY",
    "NZD",
    "CAD",
]

_CACHE: dict[str, Any] = {"payload": None, "expires_at": None}
_CACHE_TTL = timedelta(hours=6)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_rate_table(force_refresh: bool = False) -> dict[str, Any]:
    """Return rates with EUR as pivot base (ECB native)."""
    cached = _CACHE.get("payload")
    expires_at = _CACHE.get("expires_at")
    if (
        not force_refresh
        and cached is not None
        and expires_at is not None
        and _now() < expires_at
    ):
        return cached

    symbols = ",".join(c for c in DISPLAY_CURRENCIES if c != "EUR")
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(FRANKFURTER_LATEST, params={"from": "EUR", "to": symbols})
        resp.raise_for_status()
        data = resp.json()

    rates = {str(k).upper(): float(v) for k, v in (data.get("rates") or {}).items()}
    rates["EUR"] = 1.0
    payload = {
        "base": "EUR",
        "date": data.get("date"),
        "source": FX_SOURCE,
        "provider_url": "https://www.frankfurter.app/",
        "currencies": DISPLAY_CURRENCIES,
        "rates": rates,
        "fetched_at": _now().isoformat(),
    }
    _CACHE["payload"] = payload
    _CACHE["expires_at"] = _now() + _CACHE_TTL
    return payload


def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates_payload: dict[str, Any] | None = None,
) -> float:
    """Convert amount between currencies using the cached EUR-pivot table."""
    from_c = (from_currency or "").upper().strip()
    to_c = (to_currency or "").upper().strip()
    if not from_c or not to_c:
        raise ValueError("from_currency / to_currency 不能为空")
    if from_c == to_c:
        return float(amount)

    table = rates_payload or get_rate_table()
    rates: dict[str, float] = table["rates"]
    if from_c not in rates:
        raise ValueError(f"暂不支持源货币 {from_c}")
    if to_c not in rates:
        raise ValueError(f"暂不支持目标货币 {to_c}")

    # amount_in_eur = amount / rate[from] where rate means "1 EUR = rate units"
    in_eur = float(amount) / rates[from_c]
    return in_eur * rates[to_c]


def convert_money(
    amount: float | None,
    from_currency: str,
    to_currency: str,
    rates_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if amount is None:
        return None
    value = convert_amount(amount, from_currency, to_currency, rates_payload)
    return {
        "amount": round(value, 2),
        "currency": to_currency.upper(),
        "original_amount": float(amount),
        "original_currency": from_currency.upper(),
    }
