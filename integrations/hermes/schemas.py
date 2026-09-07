"""Tool schemas for Hermes LLM tool calling."""

FLIGHT_QUICK_SEARCH = {
    "name": "flight_quick_search",
    "description": (
        "Search one-way flights for a single date via the local home-flight-watcher API. "
        "Returns the cheapest nonstop (if any) plus the top cheapest connecting flights. "
        "Use when the user asks to check ticket prices for a specific origin, destination, and date."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "IATA origin airport code, e.g. BNE",
            },
            "dest": {
                "type": "string",
                "description": "IATA destination airport code, e.g. PVG",
            },
            "depart_date": {
                "type": "string",
                "description": "Departure date YYYY-MM-DD",
            },
            "max_stops": {
                "type": "integer",
                "description": "Max stops: 0=nonstop only, 1=one stop, 2=two stops. Default 1.",
            },
            "connecting_limit": {
                "type": "integer",
                "description": "How many cheapest connecting options to return (default 3).",
            },
        },
        "required": ["origin", "dest", "depart_date"],
    },
}

FLIGHT_SCAN_STATUS = {
    "name": "flight_scan_status",
    "description": (
        "Read the home-flight-watcher monitor dashboard: last scan, best/cheapest offers, "
        "and recent price alerts. Use when the user asks how monitoring looks right now."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}
