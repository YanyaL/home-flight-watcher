from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from .config import AppConfig
from .dto import FlightOfferDTO

QualityLevel = Literal["ok", "warning", "error"]
VibeKey = Literal["hang", "ren_shang_ren", "npc", "cooked"]

# Soft floors for "suspiciously cheap" long-haul style tickets (reference only).
_PRICE_FLOOR = {
    "AUD": 120.0,
    "USD": 80.0,
    "EUR": 75.0,
    "GBP": 65.0,
    "NZD": 130.0,
    "CAD": 100.0,
    "SGD": 100.0,
    "HKD": 600.0,
    "CNY": 550.0,
    "JPY": 12000.0,
}

_MIN_LAYOVER_MIN = 40
_MAX_LAYOVER_MIN = 12 * 60
_LONG_TRIP_MIN = 28 * 60

# Four-tier vibe labels — CN slang + hard EN slang.
VIBE_LABELS: dict[VibeKey, dict[str, str]] = {
    "hang": {
        "zh": "夯",
        "en": "GOATED",
        "blurb_zh": "这班直接夯住，闭眼冲也行",
        "blurb_en": "This itinerary is goated. Lock it in.",
    },
    "ren_shang_ren": {
        "zh": "人上人",
        "en": "BUILT DIFFERENT",
        "blurb_zh": "人上人档：稳、体面、不丢人",
        "blurb_en": "Built different — clean flex, not try-hard.",
    },
    "npc": {
        "zh": "NPC",
        "en": "NPC ENERGY",
        "blurb_zh": "NPC 航线：能飞，但别指望它给你面子",
        "blurb_en": "Straight NPC energy. Usable, unremarkable.",
    },
    "cooked": {
        "zh": "拉完了",
        "en": "COOKED",
        "blurb_zh": "拉完了：数据不对劲或体验崩了，先别付款",
        "blurb_en": "Cooked. It's so over — do not tap buy yet.",
    },
}


def annotate_offer_quality(
    offer: FlightOfferDTO,
    cfg: AppConfig | None = None,
    *,
    peer_prices: list[float] | None = None,
) -> FlightOfferDTO:
    """Attach warnings / quality / vibe tier onto an offer (mutates and returns it)."""
    warnings: list[str] = []
    level: QualityLevel = "ok"

    currency = (offer.currency or "").strip().upper()
    if not currency:
        warnings.append("缺少货币代码")
        level = _raise(level, "error")
    else:
        offer.currency = currency

    if offer.price is None or offer.price <= 0:
        warnings.append("价格无效或缺失")
        level = _raise(level, "error")
    else:
        floor = _PRICE_FLOOR.get(currency, 50.0)
        if offer.price < floor:
            warnings.append(f"价格异常偏低（<{floor:g} {currency}），请核对后再下单")
            level = _raise(level, "warning")
        if cfg and cfg.traveler.budget > 0 and offer.price < cfg.traveler.budget * 0.18:
            warnings.append("相对预算明显偏低，可能是残段/误标价")
            level = _raise(level, "warning")
        if peer_prices and len(peer_prices) >= 3:
            median = sorted(peer_prices)[len(peer_prices) // 2]
            if median > 0 and offer.price < median * 0.45:
                warnings.append("明显低于同批报价中位数，请谨慎")
                level = _raise(level, "warning")

    has_book = bool(offer.booking_url) or any(
        isinstance(opt, dict) and opt.get("url") for opt in (offer.booking_options or [])
    )
    if not has_book:
        warnings.append("暂无购买链接")
        level = _raise(level, "warning")

    if offer.duration_min >= _LONG_TRIP_MIN:
        hours = offer.duration_min // 60
        warnings.append(f"总行程约 {hours} 小时，偏长")
        level = _raise(level, "warning")

    for layover in _layovers_min(offer):
        if layover < _MIN_LAYOVER_MIN:
            warnings.append(f"转机间隔仅 {int(layover)} 分钟，可能过紧")
            level = _raise(level, "warning")
        elif layover > _MAX_LAYOVER_MIN:
            warnings.append(f"转机等待约 {int(layover // 60)} 小时，偏长")
            level = _raise(level, "warning")

    if not offer.segments:
        warnings.append("缺少航段信息")
        level = _raise(level, "error")

    offer.warnings = warnings
    offer.quality = level
    _apply_vibe(offer, level, warnings)
    return offer


def annotate_offers_quality(
    offers: list[FlightOfferDTO],
    cfg: AppConfig | None = None,
) -> list[FlightOfferDTO]:
    peers = [o.price for o in offers if o.price and o.price > 0]
    return [annotate_offer_quality(o, cfg, peer_prices=peers) for o in offers]


def quality_summary(offers: list[FlightOfferDTO] | list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate gate stats for API / agent_summary."""
    warning_msgs: list[str] = []
    error_msgs: list[str] = []
    warn_n = 0
    err_n = 0
    vibe_counts = {"hang": 0, "ren_shang_ren": 0, "npc": 0, "cooked": 0}
    for item in offers:
        if isinstance(item, FlightOfferDTO):
            level = item.quality
            notes = item.warnings
            vibe = item.vibe or "npc"
            label = f"{item.origin}→{item.dest} {item.depart_date}"
        else:
            level = str(item.get("quality") or "ok")
            notes = list(item.get("warnings") or [])
            vibe = str(item.get("vibe") or "npc")
            label = (
                f"{item.get('origin', '?')}→{item.get('dest', '?')} "
                f"{item.get('depart_date', '')}"
            ).strip()
        if vibe in vibe_counts:
            vibe_counts[vibe] += 1
        if level == "error":
            err_n += 1
            for note in notes:
                error_msgs.append(f"{label}: {note}")
        elif level == "warning" or notes:
            warn_n += 1
            for note in notes:
                warning_msgs.append(f"{label}: {note}")
    return {
        "ok": err_n == 0,
        "warning_count": warn_n,
        "error_count": err_n,
        "warnings": warning_msgs[:12],
        "errors": error_msgs[:12],
        "vibes": {
            "hang": {"zh": "夯", "en": "GOATED", "count": vibe_counts["hang"]},
            "ren_shang_ren": {
                "zh": "人上人",
                "en": "BUILT DIFFERENT",
                "count": vibe_counts["ren_shang_ren"],
            },
            "npc": {"zh": "NPC", "en": "NPC ENERGY", "count": vibe_counts["npc"]},
            "cooked": {"zh": "拉完了", "en": "COOKED", "count": vibe_counts["cooked"]},
        },
    }


def annotate_offer_dict(data: dict[str, Any], cfg: AppConfig | None = None) -> dict[str, Any]:
    offer = FlightOfferDTO.model_validate(data)
    annotate_offer_quality(offer, cfg)
    return offer.model_dump(mode="json")


def _apply_vibe(offer: FlightOfferDTO, level: QualityLevel, warnings: list[str]) -> None:
    key = _vibe_key(offer, level, warnings)
    meta = VIBE_LABELS[key]
    offer.vibe = key
    offer.vibe_zh = meta["zh"]
    offer.vibe_en = meta["en"]
    offer.vibe_blurb = meta["blurb_zh"]
    offer.vibe_blurb_en = meta["blurb_en"]


def _vibe_key(offer: FlightOfferDTO, level: QualityLevel, warnings: list[str]) -> VibeKey:
    if level == "error" or len(warnings) >= 3:
        return "cooked"
    if level == "warning":
        return "npc"

    # Clean ticket — split top-tier vs solid.
    score = float(offer.score or 0)
    under_budget = "低于预算" in (offer.badges or [])
    high_score = score >= 80 or "性价比高" in (offer.badges or [])
    nonstop = offer.stops == 0
    has_book = bool(offer.booking_url) or bool(offer.booking_options)

    if (high_score and has_book) or (nonstop and under_budget and has_book) or (
        nonstop and score >= 70 and has_book
    ):
        return "hang"
    if has_book and (under_budget or nonstop or score >= 55 or offer.stops <= 1):
        return "ren_shang_ren"
    if has_book:
        return "ren_shang_ren"
    return "npc"


def _layovers_min(offer: FlightOfferDTO) -> list[float]:
    segs = offer.segments or []
    if len(segs) < 2:
        return []
    out: list[float] = []
    for i in range(len(segs) - 1):
        arrive = segs[i].arrive
        depart = segs[i + 1].depart
        if isinstance(arrive, str):
            arrive = datetime.fromisoformat(arrive.replace("Z", "+00:00"))
        if isinstance(depart, str):
            depart = datetime.fromisoformat(depart.replace("Z", "+00:00"))
        out.append((depart - arrive).total_seconds() / 60.0)
    return out


def _raise(current: QualityLevel, new: QualityLevel) -> QualityLevel:
    order = {"ok": 0, "warning": 1, "error": 2}
    return new if order[new] > order[current] else current
