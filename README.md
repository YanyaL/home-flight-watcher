# 回国机票雷达 · Home Flight Watcher

面向 **留学生、旅游出行者** 等需要订国际机票的人。核心能力一句话概括：

- **快捷查询**：最便宜直飞 1 班 + 转机 TOP3（可调中转次数）+ 购买链接  
- **监测看板**：按「日期×航线」异步扫票，进度条 / 取消 / 失败重试  
- **多币种显示**：ECB 参考汇率（Frankfurter），AUD↔CNY/USD/EUR…  
- **Vibe 质量门禁**：夯 GOATED · 人上人 BUILT DIFFERENT · NPC · 拉完了 COOKED  
- **双入口**：Vue 网页 + Hermes / OpenClaw 插件，共用同一 Django API  

> 示例航线：布里斯班（BNE）→ 上海浦东（PVG）；出发地、目的地、日期都可在配置或快捷查询里改成任意航线。

### English

A return-flight radar for **students and travelers**. Feature pack:

- **Quick search**: cheapest nonstop + top connecting fares, with airline/OTA links  
- **Monitor board**: progressive day×route scans with progress / cancel / retry-failed  
- **Multi-currency UI**: ECB reference rates via Frankfurter  
- **Vibe quality gate**: **GOATED / BUILT DIFFERENT / NPC ENERGY / COOKED**  
- **Dual entry**: Vue web + Hermes / OpenClaw plugins on one Django API  

## 为什么做这个

订机票不是「打开 Google Flights 搜一下」那么简单：

1. **决策路径很固定** —— 大多数人只想知道：某天有没有便宜直飞？没有的话，一次转机里最便宜的两三班是哪几班、经哪、多少钱、去哪买。市面上的大搜索页信息过载，个人却总在重复同一套筛选。
2. **市场与货币要对齐** —— 人身在澳洲购票时，用澳区市场拿真实 AUD 标价更靠谱；同时很多人习惯用人民币/美元心里换算，所以支持一键切换显示货币（ECB 参考汇率，保留原价对照）。
3. **要能持续盯，而不只是查一次** —— 寒暑假、节假日窗口、考试周前后或临时改签，价格天天变；需要日历式监测、降价提醒。长扫票不能黑盒干等，所以按天拆任务，失败可单独重试，避免整轮重跑烧额度。
4. **入口要适配真实使用习惯** —— 有人想打开网页点一点；也有人已经在用 Hermes / OpenClaw 这类个人助手，希望直接说「帮我查 12 月 18 号 BNE 到 PVG」。业务逻辑只应写一次，网页和插件都消费同一套后端。
5. **结果要敢说话** —— 别用干巴巴的 “warning/error”。四档 vibe：夯（GOATED）、人上人（BUILT DIFFERENT）、NPC、拉完了（COOKED），该冲的冲，该停的停。

所以本项目把「快捷查询」做成一等公民业务（直飞最便宜 1 班 + 转机 TOP3，可调中转次数），把「监测看板」做成可扫票存库打分、带进度反馈的后台能力，并把 SerpAPI / Google Flights 细节关在服务端 —— **密钥不进插件、不进前端**。

它也适合作为全栈作品集项目：Django + DRF + Vue3 + 异步任务进度 + 真实第三方 API + 智能体适配层，一条完整链路。

### Why this exists (EN)

Booking flights isn’t “just open Google Flights”:

1. People ask the same narrow question every time — cheapest nonstop, else top 1-stop deals with links.
2. If you’re buying in Australia, AU-market AUD quotes beat fuzzy FX hallucinations; still, folks think in CNY/USD, so display conversion matters.
3. Prices move through exam weeks and holiday windows — monitoring needs progress, not a black-box wait, and failed days should retry without burning the whole quota.
4. Same business core for web and agent plugins.
5. Soft corporate labels are mid. We ship slang tiers so the product actually tells you when a fare is goated vs cooked.

## 功能一览

| 能力 | 说明 |
|------|------|
| 快捷查询 | 出发地 / 到达地 / 日期 / 最多中转 → 直飞最便宜 1 + 转机最便宜前 3 |
| 监测看板 | 日期范围扫票、价格日历、性价比排序、告警；扫票按「日期×航线」拆任务，可看进度/取消/重试失败 |
| 购买链接 | 优先航司渠道，也可看 OTA |
| 双入口 | Vue 网页 + Hermes / OpenClaw 插件（HTTP 调同一 API） |
| Agent 摘要 | `format=agent` 返回可直接念给用户的 `agent_summary` |
| 货币切换 | 前端可切换显示货币；汇率来自 Frankfurter / 欧洲央行参考价 |
| Vibe 质量门禁 | 夯 GOATED · 人上人 BUILT DIFFERENT · NPC · 拉完了 COOKED；价格/链接/转机异常会拖档 |

### Vibe tiers

| 中文 | English slang | 大致含义 |
|------|---------------|----------|
| 夯 | **GOATED** | 干净好价、可冲 |
| 人上人 | **BUILT DIFFERENT** | 稳、体面、不丢人 |
| NPC | **NPC ENERGY** | 能飞，但毫无主场光环 |
| 拉完了 | **COOKED** | 数据不对劲或体验崩了，先别付款 |

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

`POST /api/scan` 不挂到插件默认工具（耗额度、偏运维），请在网页或 `python manage.py scan` 触发。

## API 摘要

- `GET /api/dashboard`（可选 `?format=agent`；含 `latest_job`）
- `POST /api/scan` — 启动异步扫票（按日期×航线拆任务，返回 job）
- `GET /api/scan/<id>` — 查询进度
- `POST /api/scan/<id>/cancel` — 取消剩余任务
- `POST /api/scan/<id>/retry` — 只重试失败任务
- `GET /api/history?origin=BNE&dest=PVG`
- `POST /api/quick-search`
- `GET /api/fx-rates` — ECB 参考汇率（Frankfurter）
- `POST /api/fx-convert` — 指定金额从一种货币转到另一种

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
