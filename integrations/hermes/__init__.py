"""home-flight-watcher Hermes plugin — registration."""

from __future__ import annotations

from . import schemas, tools


def register(ctx):
    """Register agent tools that call the local Django API."""

    def quick_search(args: dict, **kwargs):
        return tools.flight_quick_search(args, ctx=ctx, **kwargs)

    def scan_status(args: dict, **kwargs):
        return tools.flight_scan_status(args, ctx=ctx, **kwargs)

    ctx.register_tool(
        name="flight_quick_search",
        toolset="home_flight_watcher",
        schema=schemas.FLIGHT_QUICK_SEARCH,
        handler=quick_search,
    )
    ctx.register_tool(
        name="flight_scan_status",
        toolset="home_flight_watcher",
        schema=schemas.FLIGHT_SCAN_STATUS,
        handler=scan_status,
    )
