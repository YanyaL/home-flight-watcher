from __future__ import annotations

AIRPORTS: dict[str, dict[str, str]] = {
    "SYD": {"city": "悉尼", "name": "金斯福德·史密斯", "country": "AU"},
    "MEL": {"city": "墨尔本", "name": "图拉马林", "country": "AU"},
    "BNE": {"city": "布里斯班", "name": "布里斯班", "country": "AU"},
    "ADL": {"city": "阿德莱德", "name": "阿德莱德", "country": "AU"},
    "PER": {"city": "珀斯", "name": "珀斯", "country": "AU"},
    "PVG": {"city": "上海", "name": "浦东", "country": "CN"},
    "SHA": {"city": "上海", "name": "虹桥", "country": "CN"},
    "PEK": {"city": "北京", "name": "首都", "country": "CN"},
    "PKX": {"city": "北京", "name": "大兴", "country": "CN"},
    "CAN": {"city": "广州", "name": "白云", "country": "CN"},
    "SZX": {"city": "深圳", "name": "宝安", "country": "CN"},
    "SIN": {"city": "新加坡", "name": "樟宜", "country": "SG"},
    "ICN": {"city": "首尔", "name": "仁川", "country": "KR"},
    "HKG": {"city": "香港", "name": "赤鱲角", "country": "HK"},
    "SGN": {"city": "胡志明", "name": "新山一", "country": "VN"},
}

AIRLINES: dict[str, str] = {
    "QF": "澳航",
    "CZ": "南航",
    "CA": "国航",
    "MU": "东航",
    "SQ": "新航",
    "KE": "大韩",
    "CX": "国泰",
    "CI": "华航",
    "VJ": "越捷",
    "JQ": "捷星",
    "TR": "酷航",
}


def city_of(code: str) -> str:
    info = AIRPORTS.get(code.upper())
    return info["city"] if info else code


def label_of(code: str) -> str:
    info = AIRPORTS.get(code.upper())
    if not info:
        return code
    return f"{info['city']} {code}"


def airline_name(code: str) -> str:
    return AIRLINES.get(code.upper(), code)
