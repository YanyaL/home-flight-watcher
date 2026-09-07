/**
 * OpenClaw plugin — thin HTTP wrappers around home-flight-watcher Django API.
 * Same tool names/params as the Hermes integration.
 */
import { Type } from "typebox";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

type Json = Record<string, unknown>;

function apiBase(pluginConfig?: { apiBase?: string }): string {
  const fromEnv = (process.env.FLIGHT_WATCHER_API_BASE || "").trim().replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  const fromCfg = (pluginConfig?.apiBase || "").trim().replace(/\/$/, "");
  if (fromCfg) return fromCfg;
  return "http://127.0.0.1:8000";
}

function apiHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  // Future: when Django enforces AGENT_API_TOKEN, send it here.
  const token = (process.env.FLIGHT_WATCHER_API_TOKEN || "").trim();
  if (token) headers["X-Agent-Token"] = token;
  return headers;
}

async function httpJson(method: string, url: string, body?: Json): Promise<Json> {
  const res = await fetch(url, {
    method,
    headers: apiHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let parsed: Json = {};
  if (text) {
    try {
      parsed = JSON.parse(text) as Json;
    } catch {
      parsed = { detail: text };
    }
  }
  if (!res.ok) {
    throw new Error(String(parsed.detail || `HTTP ${res.status}`));
  }
  return parsed;
}

function textResult(summary: unknown, details: Json) {
  const text =
    typeof summary === "string" && summary.trim()
      ? summary
      : JSON.stringify(details, null, 2);
  return {
    content: [{ type: "text" as const, text }],
    details,
  };
}

export default definePluginEntry({
  id: "home-flight-watcher",
  name: "Home Flight Watcher",
  description: "Quick flight search and monitor status via local Django API",
  register(api) {
    const cfg = (api.pluginConfig || {}) as { apiBase?: string };

    api.registerTool({
      name: "flight_quick_search",
      description:
        "Search one-way flights for a single date via local home-flight-watcher. " +
        "Returns cheapest nonstop (if any) plus top cheapest connecting flights.",
      parameters: Type.Object({
        origin: Type.String({ description: "IATA origin, e.g. BNE" }),
        dest: Type.String({ description: "IATA destination, e.g. PVG" }),
        depart_date: Type.String({ description: "YYYY-MM-DD" }),
        max_stops: Type.Optional(Type.Integer({ minimum: 0, maximum: 2 })),
        connecting_limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 10 })),
      }),
      async execute(_id, params) {
        const base = apiBase(cfg);
        const body = {
          origin: String(params.origin || "").trim().toUpperCase(),
          dest: String(params.dest || "").trim().toUpperCase(),
          depart_date: String(params.depart_date || "").trim(),
          max_stops: params.max_stops ?? 1,
          connecting_limit: params.connecting_limit ?? 3,
          format: "agent",
        };
        const payload = await httpJson("POST", `${base}/api/quick-search?format=agent`, body);
        const details = {
          agent_summary: payload.agent_summary,
          query: payload.query,
          summary: payload.summary,
          cheapest_direct: payload.cheapest_direct,
          cheapest_connecting: payload.cheapest_connecting,
        };
        return textResult(payload.agent_summary, details);
      },
    });

    api.registerTool({
      name: "flight_scan_status",
      description:
        "Read home-flight-watcher monitor dashboard: last scan, best/cheapest offers, alerts.",
      parameters: Type.Object({}),
      async execute() {
        const base = apiBase(cfg);
        const payload = await httpJson("GET", `${base}/api/dashboard?format=agent`);
        const config = (payload.config || {}) as Json;
        const details = {
          agent_summary: payload.agent_summary,
          snapshot: payload.snapshot,
          config: {
            origins: config.origins,
            destinations: config.destinations,
            date_from: config.date_from,
            date_to: config.date_to,
            budget: config.budget,
            currency: config.currency,
            provider: config.provider,
          },
          best: payload.best,
          cheapest: payload.cheapest,
          alerts: Array.isArray(payload.alerts) ? payload.alerts.slice(0, 5) : [],
        };
        return textResult(payload.agent_summary, details);
      },
    });
  },
});
