# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Nexus Assistant is a personal research assistant desktop application that integrates six independent tools (todo, literature search, experiment management, knowledge base, clock, AI chat) into a unified platform. It targets aerospace/control researchers.

## Dual Frontend Architecture

The project has **two independent frontends** sharing the same Python backend services:

1. **PySide6 version** (`main.py` + `app/ui/`) — Python desktop app, ~235MB packaged
2. **Tauri 2 version** (`nexus-ui/` + `server.py`) — Rust shell + React/TypeScript frontend + FastAPI API, ~11MB shell + ~347MB sidecar

Both share:
- `app/models/` — SQLAlchemy ORM models (8 tables in `data/nexus.db`)
- `app/services/` — Business logic layer
- `app/search/` — 8-source literature search engine
- `app/ai/router.py` — Unified AI service (OpenAI + Anthropic protocols)

## Common Commands

```bash
# PySide6 version
python main.py

# Tauri version — two terminals needed
python server.py                          # FastAPI backend on :8765
cd nexus-ui && npm run tauri dev          # Tauri dev mode

# Install dependencies
pip install -e .                          # Core Python deps
pip install fastapi uvicorn               # For Tauri backend
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
- `task_service.py` — CRUD + weekly plans + calendar marks + stats
- `experiment_service.py` — CRUD + version management + Markdown export
- `knowledge_service.py` — CRUD + tag management + card generation from paper
- `chat_service.py` — Session management + message persistence + AI message building
- `backup_service.py` — Auto backup (1 monthly + 1 weekly + 6 daily)

### Search Engine (`app/search/`)
- `engine.py` — `UnifiedSearchEngine` with parallel ThreadPoolExecutor search across 8 sources
- `sources/` — One file per data source: openalex, crossref, semantic_scholar, arxiv, pubmed, google_scholar, scopus
- `scorer.py` — Levenshtein + Chinese bigram tokenization + stop-word filtering
- `citation.py` — GB/T 7714-2015 formatting (Chinese/English detection)
- `enricher.py` — OpenAlex abstract enrichment via DOI lookup

### AI Service (`app/ai/router.py`)
- `AIRouter` class: loads models from DB, routes by purpose (summary/review/chat)
- Supports both OpenAI and Anthropic streaming protocols
- Handles DeepSeek `reasoning_content` (thinking) field
- Returns `{"type": "thinking"|"content", "data": str}` chunks

## Tauri Frontend: `nexus-ui/`

### Stack
- Tauri 2 (Rust shell) + React 19 + TypeScript + Tailwind CSS v4
- Open Sans font, glassmorphism UI style
- `src/api/client.ts` — Typed HTTP client connecting to FastAPI backend

### Key Files
- `src/App.tsx` — Main app with title bar (drag region), sidebar, page routing, loading state
- `src/pages/` — 7 page components (Dashboard, Task, Literature, Experiment, Knowledge, Chat, Settings)
- `src-tauri/src/lib.rs` — Rust setup: auto-starts Python backend (sidecar in release, `python server.py` in dev)
- `src-tauri/tauri.conf.json` — Window config (frameless, 1360×860)

### Build Notes
- `externalBin` was removed from tauri.conf.json to avoid build-time dependency on sidecar
- Rust `setup()` gracefully handles missing sidecar (dev mode)
- Frontend waits for backend via polling `/api/dashboard` with retry

## FastAPI Backend: `server.py`

- 36+ REST routes serving the Tauri frontend
- Auto-starts on port 8765, prints `NEXUS_SERVER_READY:8765`
- Lazy-initializes search engine and AI router
- Key endpoints: `/api/dashboard`, `/api/tasks`, `/api/search`, `/api/experiments`, `/api/knowledge/cards`, `/api/chat/stream` (SSE), `/api/models`, `/api/backup`
- Knowledge import: `/api/knowledge/import/json`, `/api/import/pdf`, `/api/import/md`

## Theme System (`app/ui/theme.py`)

- `ThemeManager` singleton with `theme_changed` signal
- Two themes: LIGHT (default, glassmorphism blue-green) and DARK (slate)
- QSS template functions: `BTN_PRIMARY_QSS()`, `INPUT_QSS()`, `TABLE_QSS()`, etc.
- Color tokens accessed via `get_theme().get('accent')`
- All pages must implement `reapply_theme()` for theme switching

## Windows Build Environment

Tauri build requires MSVC environment variables:
```
LIB=<MSVC>/lib/x64;<SDK>/um/x64;<SDK>/ucrt/x64
INCLUDE=<MSVC>/include;<SDK>/ucrt;<SDK>/um;<SDK>/shared
```
Paths depend on local VS Build Tools installation (typically `D:\VisualStudioBuild\VisualStudio`).

## Important Patterns

- **Session management**: Every UI action calls `get_session()`, does work in `try/finally`, closes session
- **Auto-save**: Task/experiment pages save on cell/text edit (no explicit save button)
- **Search source mapping**: UI display names map to engine keys via `engine_key` property on checkboxes (e.g., "OpenAlex" → "openalex")
- **Streaming AI**: Uses `QThread` (PySide6) or `ReadableStream` (Tauri) for real-time output
- **Backup**: Runs on startup, keeps 1 monthly + 1 weekly + 6 daily backups in `data/backups/`
