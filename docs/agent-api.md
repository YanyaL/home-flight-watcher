# Agent API 契约（Hermes / OpenClaw）

业务内核是 Django REST。网页与智能体插件共用同一套接口；插件勿直接调 SerpAPI。

环境变量（插件侧）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `FLIGHT_WATCHER_API_BASE` | `http://127.0.0.1:8000` | Django 根地址 |
| `FLIGHT_WATCHER_API_TOKEN` | （空） | 预留：将来对应后端 `AGENT_API_TOKEN`，请求头 `X-Agent-Token` |

请求时建议带 `format=agent`（query 或 JSON body），响应会多一个 `agent_summary` 字符串，方便聊天直接念给用户。JSON 其它字段不变。

---

## `flight_quick_search`

- **HTTP**: `POST /api/quick-search?format=agent`
- **Body**:

```json
{
  "origin": "BNE",
  "dest": "PVG",
  "depart_date": "2026-12-18",
  "max_stops": 1,
  "connecting_limit": 3,
  "format": "agent"
}
```

- **用途**: 查某天最便宜直飞 1 班 + 转机最便宜前 N 班（默认 3）。
- **关键出参**: `agent_summary`、`cheapest_direct`、`cheapest_connecting[]`（含 `booking_options` / `booking_url`）。

---

## `flight_scan_status`

- **HTTP**: `GET /api/dashboard?format=agent`
- **用途**: 看监测看板当前快照、性价比首选、最便宜、最近告警。
- **关键出参**: `agent_summary`、`snapshot`、`best`、`cheapest`、`alerts`。

`POST /api/scan` 不挂到插件默认工具（耗额度）。网页会启动异步 job（按日期×航线拆分），用 `GET /api/scan/<id>` 查进度，失败可 `POST .../retry`，可 `.../cancel`。

---

## 汇率（显示换算）

数据源：[Frankfurter](https://www.frankfurter.app/)（欧洲央行 ECB 参考汇率），无需 API key。服务端缓存约 6 小时。

- `GET /api/fx-rates` — EUR 为基准的汇率表 + 支持货币列表  
- `POST /api/fx-convert` — 任意支持货币互转

```json
{ "amount": 1450, "from": "AUD", "to": "CNY" }
```

支持：`AUD CNY USD EUR GBP HKD SGD JPY NZD CAD`。网页「显示货币」切换只改展示，不改变报价源货币。

---

## 质量门禁 / Vibe check

返回前端 / agent 前会给每条报价打标，并落到四档 vibe：

| 级别 | 中文 | English | 触发大致 |
|------|------|---------|----------|
| top | 夯 | **GOATED** | 干净好价、有购买链接、直飞/高分 |
| solid | 人上人 | **BUILT DIFFERENT** | 稳、可冲，但不是封神 |
| meh | NPC | **NPC ENERGY** | warning（无链接、转机离谱等） |
| bad | 拉完了 | **COOKED** | error 或一堆 warning，先别付款 |

响应里有 `quality` 汇总（含 `vibes` 计数）；`error` / `COOKED` 报价不会进入「最合适/最便宜」首选（仍会出现在列表里并标警告）。
