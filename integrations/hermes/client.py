"""HTTP client helpers shared by Hermes tool handlers."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def api_base(ctx=None) -> str:
    env = (os.environ.get("FLIGHT_WATCHER_API_BASE") or "").strip().rstrip("/")
    if env:
        return env
    if ctx is not None and hasattr(ctx, "get_config"):
        configured = str(ctx.get_config("api_base", default="") or "").strip().rstrip("/")
        if configured:
            return configured
    return "http://127.0.0.1:8000"


def api_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # Future: when Django enforces AGENT_API_TOKEN, send it here.
    token = (os.environ.get("FLIGHT_WATCHER_API_TOKEN") or "").strip()
    if token:
        headers["X-Agent-Token"] = token
    return headers


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 120.0) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=api_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("detail") or detail
        except json.JSONDecodeError:
            message = detail or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach flight API: {exc.reason}") from exc
