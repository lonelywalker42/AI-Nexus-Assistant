# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Nexus Assistant is a personal research assistant desktop application that integrates six independent tools (todo, literature search, experiment management, knowledge base, clock, AI chat) into a unified platform. It targets aerospace/control researchers. Current version: **v1.3.0**.

## Dual Frontend Architecture

The project has **two independent frontends** sharing the same Python backend services:

1. **PySide6 version** (`main.py` + `app/ui/`) — Python desktop app, ~235MB packaged
2. **Tauri 2 version** (`nexus-ui/` + `server.py`) — Rust shell + React/TypeScript frontend + FastAPI API, ~43MB single exe (sidecar embedded)

Both share:
- `app/models/` — SQLAlchemy ORM models (8 tables in `data/nexus.db`)
- `app/services/` — Business logic layer
- `app/search/` — 8-source literature search engine
- `app/ai/router.py` — Unified AI service (OpenAI + Anthropic protocols, with fallback)

## Common Commands

```bash
# PySide6 version
python main.py

# Tauri version — two terminals needed
python server.py                          # FastAPI backend on :8765
cd nexus-ui && npm run tauri dev          # Tauri dev mode

# Install dependencies
pip install -e .                          # Core Python deps
pip install fastapi uvicorn openai anthropic  # For Tauri backend + AI
cd nexus-ui && npm install                # Frontend deps

# Build
python build_server.py                    # Build Python sidecar exe
python build_tauri.py                     # Full Tauri build (sidecar + frontend + shell)
python build.py                           # PySide6 PyInstaller build

# Type check (Tauri frontend)
cd nexus-ui && npx tsc --noEmit
```

## Backend: `app/` Directory

### Database (`app/db.py`)
- SQLAlchemy 2.0 with `Mapped[]` / `mapped_column()` style
- SQLite with WAL mode, `check_same_thread=False`
- UUID primary keys (`String(36)`) on all tables
- JSON-in-Text columns for arrays/objects (e.g., `Task.sub_tasks`, `Paper.authors`)
- `init_db()` imports all models then calls `create_all()` — no Alembic migrations
- `get_session()` returns a new session; caller must close it (UI uses try/finally)

### Models (`app/models/`)
- `Task` / `WeeklyPlan` — Todo items with date, priority (low/normal/high/urgent), category (general/main/literature/experiment)
- `Paper` — Academic papers with GB/T 7714 citation, star rating, user notes
- `Experiment` / `ExperimentResult` — Versioned experiment records with code snippets and parameters
- `KnowledgeCard` / `Tag` / `CardTag` — Knowledge cards with tag system
- `ChatSession` / `ChatMessage` — AI conversation history with thinking_content
- `ModelConfig` — AI model configurations (OpenAI/Anthropic protocol)
- `SearchHistory` — Search/review/topic history

### Services (`app/services/`)
Pure functions accepting a `Session`, hardcoding `USER_ID = "default"`. Each service file handles one domain:
- `task_service.py` — CRUD + weekly plans + calendar marks + stats + main/incomplete task queries
- `experiment_service.py` — CRUD + version management + Markdown export
- `knowledge_service.py` — CRUD + tag management + card generation from paper
- `chat_service.py` — Session management + message persistence + AI message building
- `backup_service.py` — Auto backup (1 monthly + 1 weekly + 6 daily)

### AI Service (`app/ai/router.py`)
- `AIRouter` class: loads models from DB, routes by purpose (summary/review/chat)
- Supports both OpenAI and Anthropic streaming protocols
- **Protocol fallback**: if anthropic library not installed, automatically falls back to openai protocol
- Handles DeepSeek `reasoning_content` (thinking) field
- Returns `{"type": "thinking"|"content", "data": str}` chunks

## Tauri Frontend: `nexus-ui/`

### Stack
- Tauri 2 (Rust shell) + React 19 + TypeScript + Tailwind CSS v4
- Clean glassmorphism UI style, CSS-variable-driven themes
- Three themes: light (default), warm (#F5F0E1), dark (#0f172a)
- `src/api/client.ts` — Typed HTTP client connecting to FastAPI backend

### Key Files
- `src/App.tsx` — Main app with title bar, sidebar, page routing, loading state
- `src/pages/` — 7 page components (Dashboard, Task, Literature, Experiment, Knowledge, Chat, Settings)
- `src/components/Icons.tsx` — 20+ SVG icon components (replacing emoji icons)
- `src/components/Sidebar.tsx` — Navigation sidebar with About dialog (v1.0.0 clickable)
- `src-tauri/src/lib.rs` — Rust: sidecar spawn, clock window, native menus, IPC bridge
- `src-tauri/tauri.conf.json` — Window config (frameless, 1360×860)
- `src-tauri/capabilities/default.json` — Tauri 2 permissions for all windows (`"windows": ["*"]`)

### Clock Window (辉光管时钟)
- `public/clock.html` — Nixie tube clock with CSS glow effects, transparent mode
- `public/countdown-input.html` — Separate input window for custom countdown
- Triggered when main window is closed (minimized to tray)
- **Double-click** clock → returns to main window
- **Right-click** → native OS menu (countdown options, transparent toggle, back to main)
- **Mouse wheel** → zoom in/out (0.6x to 2.5x)
- Colors: `#ffe8aa` (core), `#ff8c00` (wire), `#cc5500` (glow), `#7a3a08` (halo), `#0e0e12` (glass)
- Window config: 360×140, frameless, always-on-top, transparent, resizable
- `public/todo-calendar.html` — Glass-style todo calendar with real-time clock, drag, task toggle
- Triggered alongside clock when main window closes; switchable via tray/clock context menu
- Window config: 380×500, frameless, always-on-top, transparent, resizable

### Build Notes
- `build_tauri.py` runs `npx tauri build` → Vite build + Rust compile + frontend embedding
- `build_server.py` uses `--exclude-module` but **keeps** `httpx`/`httpcore` (required by openai)
- Sidecar embedded via `include_bytes!()` — single-file distribution (~43MB)
- PyInstaller hidden imports: `openai`, `anthropic`, `app.*`, `uvicorn.*`, `sqlalchemy.*`

## FastAPI Backend: `server.py`

- 36+ REST routes serving the Tauri frontend
- Auto-starts on port 8765, prints `NEXUS_SERVER_READY:8765`
- Key endpoints:
  - Tasks: `/api/tasks`, `/api/tasks/main`, `/api/tasks/incomplete`, `/api/tasks/{id}/toggle`
  - Search: `/api/search` (saves history automatically, 50000 char limit)
  - History: `/api/history` (GET list, POST create), `/api/history/{id}` (DELETE)
  - Knowledge: `/api/knowledge/cards`, `/api/knowledge/cards/{id}`, `/api/knowledge/import/{json,pdf,md}`
  - Chat: `/api/chat/stream` (SSE), `/api/chat/sessions`, `/api/chat/sessions/{id}/messages`
  - Models: `/api/models`, `/api/models/{id}` (GET, POST, PUT, DELETE)
  - System: `/api/dashboard`, `/api/backup`

## Theme System

### Tauri (CSS variables)
- `[data-theme="light"]`, `[data-theme="warm"]`, `[data-theme="dark"]`
- Variables: `--bg-gradient`, `--glass-bg`, `--text-primary`, `--text-secondary`, `--text-muted`, `--accent-blue`, `--accent-green`, `--border-color`, `--hover-bg`, `--input-bg`

### PySide6 (`app/ui/theme.py`)
- `ThemeManager` singleton with `theme_changed` signal
- QSS template functions: `BTN_PRIMARY_QSS()`, `INPUT_QSS()`, `TABLE_QSS()`

## Important Patterns

- **Session management**: Every UI action calls `get_session()`, does work in `try/finally`, closes session
- **Auto-save**: Task/experiment pages save on cell/text edit (no explicit save button)
- **Streaming AI**: Uses `QThread` (PySide6) or `ReadableStream` (Tauri) for real-time output
- **Backup**: Runs on startup, keeps 1 monthly + 1 weekly + 6 daily backups in `data/backups/`

## Debugging Lessons Learned

### Tauri 2 子窗口 IPC 问题
- **问题**：子窗口（如时钟）的 `import('@tauri-apps/api/core')` 静默失败
- **根因**：Tauri 2 子窗口不自动注入 JS 模块系统
- **解决**：通过 `WebviewWindowBuilder::initialization_script()` 注入 `window.invoke`
- **关键**：`capabilities/default.json` 的 `windows` 必须包含子窗口标签或 `"*"`

### Tauri 2 参数名映射
- JS 的 camelCase 自动转为 Rust 的 snake_case
- JS: `{hasCd: true}` → Rust: `has_cd: bool`
- 错误示例：`has_cd` 在 JS 中不匹配 Rust 的 `has_cd`

### `-webkit-app-region: drag` 副作用
- 设置在 body 上会**吞掉所有鼠标事件**（右键、双击、点击）
- 解决：移除 body 的 drag，改用 JS `mousedown` + `getCurrentWindow().startDragging()`

### 系统托盘窗口死锁
- 在 `on_menu_event` 回调中调用 `close()`/`destroy()` 可能阻塞主线程
- 解决：用 `std::thread::spawn` 将窗口操作放到新线程

### PyInstaller 动态导入
- 函数内部的 `import openai` 不会被 PyInstaller 自动检测
- 必须添加 `--hidden-import openai` 和 `--hidden-import anthropic`
- `openai` 依赖 `httpx`，不能在 `--exclude-module` 中排除 `httpx`

### FastAPI 文件上传
- `UploadFile = File(...)` 在某些情况下解析 multipart 失败
- Tauri webview 中 `FormData + fetch` 有 CORS/协议限制
- `base64 + JSON` 方案受 Starlette body 大小限制
- **最终方案**：`Content-Type: application/octet-stream` + `X-Filename` 头部 + `request.body()` 接收原始字节

### Tauri 2 原生菜单
- HTML 菜单受窗口边界限制，无法超出窗口
- 使用 Rust `Menu` + `MenuItem` 创建原生菜单，通过 `popup_menu()` 弹出
- `on_menu_event` 注册全局事件处理器

### CSS 变量驱动主题
- 所有颜色使用 `var(--xxx)` 而非硬编码 Tailwind 类
- `[data-theme="warm"]` 选择器定义暖色主题变量
- `select.input-glass` 需要自定义下拉箭头 SVG（深色模式需切换颜色）
