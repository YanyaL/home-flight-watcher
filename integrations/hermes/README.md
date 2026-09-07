# Hermes 插件脚手架

薄封装：工具 → HTTP → 本机 Django（`/api/quick-search`、`/api/dashboard`）。不内置 SerpAPI key。

## 启用

1. 先启动后端：`cd backend && python manage.py runserver`
2. 把本目录链到 Hermes 插件目录（或复制）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.hermes\plugins\home-flight-watcher" -Target "D:\doc\home-flight-watcher\integrations\hermes"
```

3. 可选环境变量：

```
FLIGHT_WATCHER_API_BASE=http://127.0.0.1:8000
# FLIGHT_WATCHER_API_TOKEN=  # 预留，对应后端将来 AGENT_API_TOKEN
```

4. 在 Hermes 里启用插件 `home-flight-watcher`，确认工具 `flight_quick_search` / `flight_scan_status` 可见。

契约见仓库 [`docs/agent-api.md`](../../docs/agent-api.md)。
