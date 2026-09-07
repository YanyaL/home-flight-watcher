# OpenClaw 插件脚手架

薄封装：工具 → HTTP → 本机 Django。工具名与 Hermes 一致：`flight_quick_search`、`flight_scan_status`。

## 启用（本地路径）

1. 启动后端：`cd backend && python manage.py runserver`
2. 安装插件依赖（需本机已装 OpenClaw / Node 22+）：

```powershell
cd D:\doc\home-flight-watcher\integrations\openclaw
npm install
```

3. 用路径安装到 OpenClaw（命令以你本机 OpenClaw 版本文档为准）：

```powershell
openclaw plugins install "D:\doc\home-flight-watcher\integrations\openclaw"
openclaw plugins inspect home-flight-watcher --runtime --json
```

4. 环境变量：

```
FLIGHT_WATCHER_API_BASE=http://127.0.0.1:8000
# FLIGHT_WATCHER_API_TOKEN=
```

也可在 OpenClaw 插件配置里设 `apiBase`。

契约见 [`docs/agent-api.md`](../../docs/agent-api.md)。本目录为开发脚手架，未走 ClawHub 发布流程。
