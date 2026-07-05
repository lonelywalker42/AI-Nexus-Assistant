# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Nexus Assistant is a personal research assistant desktop application that integrates six independent tools (todo, literature search, experiment management, knowledge base, clock, AI chat) into a unified platform. It targets aerospace/control researchers. Current version: **v4.6.2**.

## v4.0.0 Features (Multi-platform + Auto-update)

**Auto-update** (`tauri-plugin-updater`):
- Desktop app checks GitHub Release on startup
- Ed25519 signature verification for update packages
- Frontend UI in SettingsPage: "检查更新" button + update dialog
- Config: `tauri.conf.json` → `plugins.updater.endpoints`
- Signing key: `~/.tauri/nexus.key` (generate with `npx tauri signer generate`)
- **⚠️ `latest.json` 必须随每个版本发布** — updater 端点指向 `releases/latest/download/latest.json`，若缺失则自动更新完全失效
- **签名命令**: `npx tauri signer sign -f ~/.tauri/nexus.key -p "" <file>` — 必须使用 `-f` 读取密钥文件 + `-p ""` 指定空密码，否则会挂起等待交互输入

**JWT Authentication** (`app/auth.py`):
- Endpoints: `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`
- Default user: admin / nexus2024
- Access token: 15min, Refresh token: 7 days
- Frontend: `client.ts` auto-adds Bearer token, auto-refreshes on 401
- Local mode (localhost): auth skipped; Remote mode: login required

**Mobile Support** (Android/iOS):
- Platform detection: `usePlatform()` hook (`src/hooks/usePlatform.ts`)
- Mobile layout: `MobileLayout.tsx` with bottom tab navigation
- Mobile CSS: `src/styles/mobile.css` (safe areas, touch optimization)
- Conditional features: `#[cfg(desktop)]` / `#[cfg(mobile)]` in lib.rs
- Capabilities: `capabilities/mobile.json` for mobile permissions

## Dual Frontend Architecture

The project has **two independent frontends** sharing the same Python backend services:

1. **PySide6 version** (`main.py` + `app/ui/`) — Python desktop app, ~235MB packaged
2. **Tauri 2 version** (`nexus-ui/` + `server.py`) — Rust shell + React/TypeScript frontend + FastAPI API, ~51MB single exe (sidecar embedded)

Both share:
- `app/models/` — SQLAlchemy ORM models (8 tables in `data/nexus.db`)
- `app/services/` — Business logic layer
- `app/search/` — 8-source literature search engine
- `app/ai/router.py` — Unified AI service (OpenAI + Anthropic protocols, with fallback)
- `app/ai/web_search.py` — Web search tool (open-webSearch aggregator + DuckDuckGo fallback)
- `app/ai/search_service.py` — open-webSearch daemon lifecycle manager

## Common Commands

```bash
# PySide6 version
python main.py

# Tauri version — two terminals needed
python server.py                          # FastAPI backend on :8765
cd nexus-ui && npm run tauri dev          # Tauri dev mode

# Install dependencies
pip install -e .                          # Core Python deps
pip install fastapi uvicorn openai anthropic httpx  # For Tauri backend + AI
pip install python-docx                   # DOCX export support
cd nexus-ui && npm install                # Frontend deps
cd open-webSearch && npm install && npm run build  # Web search aggregator (Node.js)

# Build
python build_server.py                    # Build Python sidecar exe
python build_tauri.py                     # Full Tauri build (sidecar + frontend + shell)
python build.py                           # PySide6 PyInstaller build

# Type check (Tauri frontend)
cd nexus-ui && npx tsc --noEmit
```

## Environment Setup for Claude Code

This section guides Claude Code through setting up the development environment from a fresh clone.
**完整开发者指南**: 参见 `docs/DEV-SETUP.md`（含架构图、各平台说明、构建流程、常见问题排查）。

### Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ LTS | Frontend build + open-webSearch |
| Rust | 1.70+ | Tauri shell compilation |
| Git | 2.30+ | Version control + submodules |

### Step 1: Clone with Submodules

```bash
git clone --recursive https://github.com/anthropics/ai-nexus-assistant.git
cd ai-nexus-assistant

# If already cloned without --recursive:
git submodule update --init --recursive
```

### Step 2: Python Environment

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install core dependencies
pip install -e .

# Install Tauri backend dependencies
pip install fastapi uvicorn openai anthropic httpx

# DOCX export support
pip install python-docx

# Optional: MinerU for PDF conversion
pip install magic-pdf
```

### Step 3: Frontend Dependencies

```bash
# Tauri frontend
cd nexus-ui
npm install

# open-webSearch (web search aggregator)
cd ../open-webSearch
npm install
npm run build
cd ..
```

### Step 4: Tauri Build Tools (for desktop app)

```bash
# Install Tauri CLI
cargo install tauri-cli

# Or via npm
npm install -g @tauri-apps/cli
```

### Step 5: Verify Setup

```bash
# Start backend
python server.py  # Should print NEXUS_SERVER_READY:8765

# In another terminal, start frontend
cd nexus-ui && npm run tauri dev

# Type check
cd nexus-ui && npx tsc --noEmit
```

### Submodule: open-webSearch

The `open-webSearch/` directory is a git submodule containing the web search aggregator. It aggregates DuckDuckGo, Bing, Brave, Wikipedia, and Arxiv search engines.

```bash
# Update submodule to latest
cd open-webSearch
git pull origin main
cd ..
git add open-webSearch
git commit -m "chore: update open-webSearch submodule"
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `pip install -e .` fails | Ensure Python 3.10+ and pip are up to date |
| `npm install` network errors | Use `npm install --registry https://registry.npmmirror.com` |
| Tauri build fails | Ensure Rust toolchain is installed via rustup |
| `open-webSearch` not working | Run `cd open-webSearch && npm install && npm run build` |
| Port 8765 in use | Kill existing process or change port in server.py |
| Port 3210 in use | open-webSearch default port; restart app to clear |
| DOCX export fails | `pip install python-docx` — not in pyproject.toml, must install separately |
| VS Build Tools not found | Install "C++ 桌面开发" workload from [VS Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe) |

## Backend: `app/` Directory

### Database (`app/db.py`)
- SQLAlchemy 2.0 with `Mapped[]` / `mapped_column()` style
- SQLite with WAL mode, `check_same_thread=False`
- UUID primary keys (`String(36)`) on all tables
- JSON-in-Text columns for arrays/objects (e.g., `Task.sub_tasks`, `Paper.authors`)
- `init_db()` imports all models then calls `create_all()` — no Alembic migrations
- **Incremental migration**: `_migrate_columns()` in `init_db()` adds missing columns via `ALTER TABLE`
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
- `backup_service.py` — Auto backup (1 monthly + 1 weekly + 6 daily), backup/restore handles .db + .db-wal + .db-shm

### AI Service (`app/ai/router.py`)
- `AIRouter` class: loads models from DB, routes by purpose (summary/review/chat)
- Supports both OpenAI and Anthropic streaming protocols
- **Protocol fallback**: if anthropic library not installed, automatically falls back to openai protocol
- **JSON mode**: `response_format={"type": "json_object"}` 支持，含自动 fallback（模型不支持时重试）
- Handles DeepSeek `reasoning_content` (thinking) field
- Returns `{"type": "thinking"|"content", "data": str}` chunks
- **Tool calling**: OpenAI function calling + Anthropic tool use with agentic loop (max 3 rounds)
- **Forced final response**: when max tool rounds reached, forces a final text response without tools

### Web Search (`open-webSearch` + `app/ai/`)
- **open-webSearch** (`open-webSearch/`): TypeScript git submodule, aggregates DuckDuckGo + Bing + Brave + Wikipedia + Arxiv
- `app/ai/search_service.py` — daemon lifecycle manager, auto-starts on server.py startup (port 3210)
- `app/ai/web_search.py` — calls daemon API `POST /search`, fallback to DuckDuckGo HTML scraping
- **Proxy bypass**: httpx client uses `proxy=None` to bypass local proxy (e.g. Clash) avoiding 502 errors
- **Timeout**: 60 seconds (Chinese search queries take longer)
- Health check: `GET http://127.0.0.1:3210/health`
- Requires Node.js; auto-degrades to DuckDuckGo direct search when unavailable

## Tauri Frontend: `nexus-ui/`

### Stack
- Tauri 2 (Rust shell) + React 19 + TypeScript + Tailwind CSS v4
- Clean glassmorphism UI style, CSS-variable-driven themes
- Three themes: light (default), warm (#F5F0E1), dark (#0f172a)
- `src/api/client.ts` — Typed HTTP client connecting to FastAPI backend

### Pages
- `src/pages/Dashboard.tsx` — Dashboard (data overview)
- `src/pages/TaskPage.tsx` — Tasks & Schedule
- `src/pages/TodayPage.tsx` — Today (task sync, progress, work log)
- `src/pages/LiteraturePage.tsx` — Literature Search (7-source search, review generation, review pool FAB)
- `src/pages/PaperLibraryPage.tsx` — Paper Library (PDF import, citation, AI summary)
- `src/pages/KnowledgePage.tsx` — IDEA (knowledge cards, quick notes, AI chat association)
- `src/pages/ExperimentPage.tsx` — Experiment Management
- `src/pages/ChatPage.tsx` — AI Chat (tool calling, category management, auto title)
- `src/pages/SettingsPage.tsx` — Settings (model config, theme, backup, app rename)

### Key Components
- `src/components/Icons.tsx` — 30+ SVG icon components
- `src/components/Sidebar.tsx` — Grouped navigation (Overview/Research/Personal Assistant/Settings) + AI Chat floating button + About dialog
- `src/hooks/useAppName.ts` — Custom app name hook (localStorage + Event)

### Clock Window (Nixie Tube Clock)
- `public/clock.html` — Nixie tube clock with CSS glow effects, transparent mode
- **Music player**: folder loading, sequential/shuffle play, spectrum visualization (Web Audio API + Canvas)
- **IndexedDB persistence**: playlist and alert sound stored as ArrayBuffer, auto-restore on restart
- **Countdown alert**: countdown ends pauses music, plays alert, manual stop button restores music and clock
- Triggered when main window is closed (minimized to tray)
- **Double-click** clock -> returns to main window
- **Right-click** -> native OS menu (countdown options, transparent toggle, back to main)
- **Mouse wheel** -> zoom in/out (0.6x to 2.5x)
- Window config: 360x180, frameless, always-on-top, transparent, resizable
- `public/todo-calendar.html` — Glass-style todo calendar with real-time clock, drag, task toggle

### Game Console Mode (游戏机模式)
- `public/games.html` — Self-contained retro arcade with 18 pixel games on a single Canvas
- **Games**: 2048, Tetris, Shooter (fighter jet), Word Hopper (CET-6 typing), Snake, Breakout, Minesweeper, Flappy Bird, Pac-Man, Pong, Frogger, Bomberman, Space Invaders, Hextris, Tower Stacking, Pseudo-3D Racer, Gomoku, Maze
- **Gomoku AI Engine**: 7-level difficulty with Minimax+Alpha-Beta, Iterative Deepening, Zobrist TT, History Heuristic, VCF/VCT threat-space search
- **Win Rate Stats**: Per-difficulty win/loss/draw tracking in localStorage (`nexus-gomoku-stats`)
- **UI**: CRT scanline overlay, neon green (#00ff41) retro aesthetic, 2-column grid menu, pixel font support (Press Start 2P / VT323)
- **GameConsolePage**: CRT monitor frame with scanlines, LED indicator, glow effects
- **Persistence**: `localStorage` for high scores (`nexus-game-scores`) and save/resume progress (`nexus-game-progress`)
- **Navigation**: Keyboard (arrow keys + Enter) and mouse click support
- **Integration**: `GameConsolePage.tsx` embeds via iframe, fullscreen toggle, integrated in sidebar under "个人助手"
- All games are pure Canvas/JS, zero dependencies, single HTML file

### Build Notes
- `build_tauri.py` runs `npx tauri build` -> Vite build + Rust compile + frontend embedding
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
  - DeepSeek Import: `/api/knowledge/import/deepseek`, `/api/knowledge/import-groups/{id}/progress`
  - Chat: `/api/chat/stream` (SSE), `/api/chat/sessions`, `/api/chat/sessions/{id}/messages`
  - Models: `/api/models`, `/api/models/{id}` (GET, POST, PUT, DELETE)
  - System: `/api/dashboard`, `/api/backup`, `/api/backups/export-db`
  - Rust IPC: `list_audio_files`, `read_file_base64`

## Theme System

### Tauri (CSS variables)
- `[data-theme="light"]`, `[data-theme="warm"]`, `[data-theme="dark"]`
- Variables: `--bg-gradient`, `--glass-bg`, `--text-primary`, `--text-secondary`, `--text-muted`, `--accent-blue`, `--accent-green`, `--border-color`, `--hover-bg`, `--input-bg`

## Important Patterns

- **Session management**: Every UI action calls `get_session()`, does work in `try/finally`, closes session
- **Auto-save**: Task/experiment pages save on cell/text edit (no explicit save button)
- **Streaming AI**: Uses `ReadableStream` (Tauri) for real-time output
- **AI Tool Calling**: `router.py` supports OpenAI function calling + Anthropic tool use with agentic loop (max 3 rounds). SSE chunk types: `thinking`, `content`, `tool_call`, `tool_result`. Intermediate tool-calling rounds suppress content from frontend.
- **AI JSON Mode**: `response_format={"type": "json_object"}` 支持，含自动 fallback（模型不支持时重试）
- **Web Search**: `app/ai/web_search.py` — proxy=None bypasses local proxy, 60s timeout, multi-engine aggregation
- **DeepSeek Import**: Two-phase pipeline: (1) parse JSON + preprocess + save sessions (no LLM), (2) batch LLM summarization → knowledge cards. ChatSession has `import_group_id` for grouping.
- **Backup**: backup/restore handles .db + .db-wal + .db-shm, WAL checkpoint before backup
- **Export**: ZIP export includes all three db files; import supports .db and .zip
- **Incremental Migration**: `_migrate_columns()` in `init_db()` adds missing columns via `ALTER TABLE` (no Alembic)

---

## Development Lifecycle

### Version Numbering

| Change Type | Format | Example | Description |
|-------------|--------|---------|-------------|
| Major release | `vX.0.0` | v3.0.0 | Large feature set, architecture changes |
| Minor update | `v*.x.0` | v2.3.0 | Feature enhancements, UI improvements |
| Bug fix | `v*.*.x` | v2.2.2 | Bug fixes, debugging, performance |

### ⚠️ 版本号同步清单

**发版时必须同步更新以下 5 处版本号**，遗漏任何一处都会导致前端显示、自动更新、构建产物版本不一致：

| # | 文件 | 字段 | 说明 |
|---|------|------|------|
| 1 | `nexus-ui/src-tauri/tauri.conf.json` | `"version"` | Tauri 安装包文件名、Windows 安装信息中的版本号 |
| 2 | `nexus-ui/src-tauri/Cargo.toml` | `version` | Rust 编译产物版本元数据（影响 `Cargo.lock`） |
| 3 | `nexus-ui/src/api/client.ts` | `APP_VERSION` | 前端显示版本号（侧边栏、设置页、更新检查） |
| 4 | `server.py` | `FastAPI(version=...)` | API 文档中的版本号 |
| 5 | `CLAUDE.md` | `Current version: **vX.Y.Z**` | 项目文档版本记录 |

**自动化脚本**（推荐在发版前执行）：
```bash
# 一键检查版本号一致性（替换 X.Y.Z 为目标版本）
grep -rn '"version"' nexus-ui/src-tauri/tauri.conf.json | grep -q 'X.Y.Z' && echo "✅ tauri.conf.json" || echo "❌ tauri.conf.json"
grep -rn 'version' nexus-ui/src-tauri/Cargo.toml | head -1 | grep -q 'X.Y.Z' && echo "✅ Cargo.toml" || echo "❌ Cargo.toml"
grep -rn 'APP_VERSION' nexus-ui/src/api/client.ts | grep -q 'X.Y.Z' && echo "✅ client.ts" || echo "❌ client.ts"
grep -rn 'FastAPI.*version' server.py | grep -q 'X.Y.Z' && echo "✅ server.py" || echo "❌ server.py"
grep -rn 'Current version' CLAUDE.md | grep -q 'X.Y.Z' && echo "✅ CLAUDE.md" || echo "❌ CLAUDE.md"
```

**⚠️ Cargo.lock 会自动同步**：修改 `Cargo.toml` 后，`npx tauri build` 会自动更新 `Cargo.lock` 中的版本号，无需手动编辑。

### Workflow

```
Requirements -> Development -> Release -> Iteration
```

#### 1. Requirements (Major vX.0.0)
- User provides requirements
- Claude Code writes PRD document (`docs/PRD-vX.md`)
- Review and confirm before development

#### 2. Development (Minor v*.x.0)
- Feature development complete
- User confirms, update release directory exe/dll version suffix
- `git commit` + `git tag` + `git push`
- `gh release create` to publish GitHub release

#### 3. Release
```bash
# Build
python build_server.py              # Build sidecar
cd nexus-ui && npx tauri build      # Build Tauri app

# Update release directory
cp nexus-ui/src-tauri/target/release/nexus-ui.exe release/AI-Nexus-Assistant.exe
cp nexus-ui/src-tauri/target/release/nexus_ui_lib.dll release/nexus_ui_lib.dll

# Sign installers (必须！updater 需要 Ed25519 签名验证)
cd nexus-ui
npx tauri signer sign -f ~/.tauri/nexus.key -p "" "src-tauri/target/release/bundle/nsis/AI Nexus Assistant_X.Y.Z_x64-setup.exe"
npx tauri signer sign -f ~/.tauri/nexus.key -p "" "src-tauri/target/release/bundle/msi/AI Nexus Assistant_X.Y.Z_x64_en-US.msi"
cd ..

# Generate latest.json (用 Python 生成，确保中文正确编码)
python -c "
import json, datetime
nsis_sig = open('nexus-ui/src-tauri/target/release/bundle/nsis/...setup.exe.sig').read().strip()
data = {
    'version': 'X.Y.Z',
    'notes': '更新说明',
    'pub_date': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'platforms': {
        'windows-x86_64': {
            'signature': nsis_sig,
            'url': 'https://github.com/lonelywalker42/AI-Nexus-Assistant/releases/download/vX.Y.Z/AI.Nexus.Assistant_X.Y.Z_x64-setup.exe'
        }
    }
}
with open('release/latest.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
"

# Publish (⚠️ 必须包含 latest.json！)
git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z - Title" --notes "..." \
  release/AI-Nexus-Assistant.exe \
  release/nexus_ui_lib.dll \
  release/latest.json \
  "nexus-ui/src-tauri/target/release/bundle/nsis/...setup.exe" \
  "nexus-ui/src-tauri/target/release/bundle/msi/...msi"
```

> **调试教训**: v4.3.1 及之前所有版本均未上传 `latest.json`，导致 Tauri 自动更新端点 `releases/latest/download/latest.json` 始终 404，自动更新功能完全失效。签名工具必须使用 `-f <keyfile> -p ""` 参数，否则 `tauri signer sign` 会挂起等待交互式密码输入。

#### 4. Iteration (Bug fix v*.*.x)
- Based on user feedback / bug reports
- Problem testing and localization -> debugging and fixing
- Document development testing best practices (`docs/DEV-PRACTICES.md`)
- Repeat Release phase

### Project Structure

```
CLAUDE.md                   # This file (project guide + lifecycle)
README.md                   # Project introduction
CHANGELOG.md                # Version change log
docs/PRD-v3.md              # Major version PRD document
docs/DEV-PRACTICES.md       # Development testing best practices
docs/SCHOLARAIO_REFERENCE.md # ScholarAIO 参考分析与改进方案
docs/LITKB_REFERENCE.md     # LitKB 参考分析与改进方案
app/                        # Python backend
nexus-ui/                   # Tauri frontend
reference/                  # 参考项目 (gitignore)
  scholaraio/               # ScholarAIO 克隆
release/                    # Build artifacts
  AI-Nexus-Assistant.exe    # Portable main program
  nexus_ui_lib.dll          # WebView2 loader
  data/                     # Data directory
data/                       # Development environment data
```

## Debugging Lessons Learned

### Tauri 2 Sub-window IPC
- **Problem**: Sub-window JS imports silently fail
- **Fix**: Inject `window.invoke` via `initialization_script()`

### System Tray Backend Process Leak
- **Problem**: `child.kill()` only kills direct child, not process tree
- **Fix**: Use `taskkill /F /T /PID` to kill entire process tree

### SQLite WAL Backup Data Loss
- **Problem**: Backup copies only `.db` file, WAL data lost
- **Fix**: `PRAGMA wal_checkpoint(FULL)` before backup, copy all three files

### httpx Proxy Causing 502
- **Problem**: System proxy (Clash) intercepts localhost requests
- **Fix**: `httpx.Client(proxy=None)` bypasses proxy

### AI Tool Calling Infinite Loop
- **Problem**: Model retries search on failure, exhausts all rounds
- **Fix**: At `MAX_TOOL_ROUNDS`, append "answer directly" prompt without tools

### Tauri WebView2 showDirectoryPicker Unavailable
- **Problem**: File System Access API not supported in Tauri WebView2
- **Fix**: Use `<input webkitdirectory>` + IndexedDB for ArrayBuffer storage

### Clock Window State Loss
- **Problem**: Clock window destroyed on return to main, playlist lost
- **Fix**: `cw.hide()` instead of `cw.close()`, IndexedDB persistence
