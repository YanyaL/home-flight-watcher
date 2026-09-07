# 回国机票雷达 · Home Flight Watcher

面向 **留学生、旅游出行者** 等需要订国际机票的人：用真实澳区报价（AUD）快速找出「最便宜直飞 + 最便宜转机」，并给出可点开的航司/代理购买链接；同一套 API 既能跑网页，也能挂到 Hermes / OpenClaw 当智能体工具。

> 示例航线：布里斯班（BNE）→ 上海浦东（PVG）；出发地、目的地、日期都可在配置或快捷查询里改成任意航线。

## 为什么做这个

订机票不是「打开 Google Flights 搜一下」那么简单：

1. **决策路径很固定** —— 大多数人只想知道：某天有没有便宜直飞？没有的话，一次转机里最便宜的两三班是哪几班、经哪、多少钱、去哪买。市面上的大搜索页信息过载，个人却总在重复同一套筛选。
2. **市场与货币要对齐** —— 人身在澳洲购票时，应用澳区市场、AUD 标价，否则汇率换算和低价幻觉很容易误导下单。
3. **要能持续盯，而不只是查一次** —— 寒暑假、节假日窗口、考试周前后或临时改签，价格天天变；需要日历式监测、降价提醒，而不是每次手工刷新。
4. **入口要适配真实使用习惯** —— 有人想打开网页点一点；也有人已经在用 Hermes / OpenClaw 这类个人助手，希望直接说「帮我查 12 月 18 号 BNE 到 PVG」。业务逻辑只应写一次，网页和插件都消费同一套后端。

所以本项目把「快捷查询」做成一等公民业务（直飞最便宜 1 班 + 转机 TOP3，可调中转次数），把「监测看板」做成可扫票存库打分的后台能力，并把 SerpAPI / Google Flights 细节关在服务端 —— **密钥不进插件、不进前端**。

它也适合作为全栈作品集项目：Django + DRF + Vue3 + 真实第三方 API + 智能体适配层，一条完整链路。

## 功能一览

| 能力 | 说明 |
|------|------|
| 快捷查询 | 出发地 / 到达地 / 日期 / 最多中转 → 直飞最便宜 1 + 转机最便宜前 3 |
| 监测看板 | 日期范围扫票、价格日历、性价比排序、告警 |
| 购买链接 | 优先航司渠道，也可看 OTA |
| 双入口 | Vue 网页 + Hermes / OpenClaw 插件（HTTP 调同一 API） |
| Agent 摘要 | `format=agent` 返回可直接念给用户的 `agent_summary` |

## 架构

```text
Vue 网页 ──┐
Hermes ────┼──► Django /api/* ──► SerpAPI (Google Flights)
OpenClaw ──┘
```

```text
backend/                 Django + DRF（业务内核）
frontend/                Vue 3 + TypeScript + Vite
integrations/hermes/     Hermes 插件脚手架
integrations/openclaw/   OpenClaw 插件脚手架
docs/agent-api.md        智能体工具契约
config.yaml              航线 / 预算 / 采样步长
.env.example             环境变量模板（不要提交真实 .env）
```

## 快速开始

### 1. 配置密钥

```powershell
cd D:\doc\home-flight-watcher
copy .env.example .env
# 编辑 .env：FLIGHT_PROVIDER=serpapi ，填入 SERPAPI_API_KEY
```

[SerpAPI](https://serpapi.com/) 免费额度有限（约 100 次/月），本地开发可先设 `FLIGHT_PROVIDER=mock`。

### 2. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 3. 前端

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 [http://127.0.0.1:5173](http://127.0.0.1:5173)。默认进入「快捷查询」；也可切到「监测看板」扫票。

### 4. 智能体插件（可选）

- Hermes：见 [`integrations/hermes/README.md`](integrations/hermes/README.md)
- OpenClaw：见 [`integrations/openclaw/README.md`](integrations/openclaw/README.md)
- 工具契约：[`docs/agent-api.md`](docs/agent-api.md)

插件环境变量：

```
FLIGHT_WATCHER_API_BASE=http://127.0.0.1:8000
# FLIGHT_WATCHER_API_TOKEN=   # 预留，对应将来后端 AGENT_API_TOKEN
```

| 工具 | API |
|------|-----|
| `flight_quick_search` | `POST /api/quick-search?format=agent` |
| `flight_scan_status` | `GET /api/dashboard?format=agent` |

`POST /api/scan` 不挂到插件（耗额度、偏运维），请在网页或 `python manage.py scan` 触发。

## API 摘要

- `GET /api/dashboard`（可选 `?format=agent`）
- `POST /api/scan`
- `GET /api/history?origin=BNE&dest=PVG`
- `POST /api/quick-search`

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

## 配置说明

根目录 `.env`：

```
FLIGHT_PROVIDER=serpapi
SERPAPI_API_KEY=你的key
```

`config.yaml`：出发地、目的地、日期窗、预算、`serpapi_date_step_days`、`booking_link_limit` 等。

默认澳洲市场（`gl=au`），货币 `AUD`。看板可勾选「只显示航司购买渠道」。

## 注意

- 标价仅供参考，下单以航司 / 代理结算页为准
- SerpAPI 的 `booking_token` 拉购买链接也会扣额度
- **不要把真实 `.env` 或 API Key 提交到 Git**；插件里也不要塞 SerpAPI key
- 本仓库为个人学习 / 自用项目，非商业比价产品

## License

MIT（若你 fork 后商用，请自行遵守上游数据源与 SerpAPI 条款）
