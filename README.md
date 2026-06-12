# AI Nexus Assistant

> AI增强个人科研助手 — 整合文献检索、试验管理、知识库、AI对话的统一桌面平台

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Tauri 2](https://img.shields.io/badge/Tauri_2-Rust-orange.svg)](https://tauri.app/)
[![React 19](https://img.shields.io/badge/React_19-TypeScript-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 项目简介

AI Nexus Assistant 将六个独立的科研工具整合为统一的桌面应用，面向航空航天/控制领域研究者，提供从日常事务管理、文献检索与综述、试验进度跟踪、到AI知识库对话的全链路支持。

### 双前端架构

| 版本 | 技术栈 | 包体积 | 状态 |
|------|--------|--------|------|
| **Tauri 2 版** | Rust + React + TypeScript + Tailwind CSS + FastAPI | **11MB** | ✅ 可用 |
| **PySide6 版** | Python + PySide6 + SQLAlchemy | ~235MB | ✅ 功能完整 |

### 整合的源项目

| 源项目 | 原功能 | 整合后的角色 |
|--------|--------|-------------|
| ai-todo | 待办日历 | 任务与日程模块 |
| ai-literature | 文献检索与综述 | 文献管理模块 |
| ai-researchers | 多源文献搜索 | 搜索引擎后端 |
| ai-research-manager | 试验与进度管理 | 试验管理模块 |
| clock-1999 | 桌面时钟 | 时钟组件 |
| DeepseekManager | 知识库与AI对话 | 知识库 + AI对话 |

### 核心特性

- **全局仪表盘** — 统计聚合 + 近期活动流 + 月度完成率
- **任务与日程** — 日历视图 + 待办管理 + 周计划 + 四级优先级
- **8源文献搜索** — OpenAlex, CrossRef, Semantic Scholar, arXiv, PubMed, Google Scholar, Scopus + OpenAlex摘要补全
- **AI综述与选题** — 流式Markdown渲染 + JSON结构化选题 + 历史重载
- **试验管理** — 版本化结果 + 参数快照 + 代码片段存档 + Markdown导出
- **知识库** — 知识卡片 + 标签分类 + 星级评分 + 多格式导入
- **AI对话** — 流式输出 + Markdown渲染 + thinking折叠 + 写作辅助
- **统一AI服务** — OpenAI + Anthropic 双协议，DeepSeek thinking 内容折叠
- **桌面时钟** — 辉光管/机械表/番茄钟三模式 + 浮动窗口
- **玻璃质感UI** — 清新蓝绿配色 + 高圆角 + Open Sans字体

## 技术架构

```
┌─────────────────────────────────────────────┐
│          Tauri 2 桌面应用 (11MB)             │
│  ┌───────────────────────────────────────┐  │
│  │  React 19 + TypeScript + Tailwind     │  │
│  │  Open Sans + 玻璃质感 UI              │  │
│  └──────────────┬────────────────────────┘  │
│                 │ HTTP REST API              │
│  ┌──────────────▼────────────────────────┐  │
│  │  Python FastAPI 后端 (server.py)       │  │
│  │  31 个 REST 路由                       │  │
│  └──────────────┬────────────────────────┘  │
│                 │                            │
│  ┌──────────────▼────────────────────────┐  │
│  │  服务层 (复用现有 Python 代码)          │  │
│  │  搜索引擎(8源) | AI服务 | 数据库       │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 快速开始

### Tauri 2 版（推荐）

```bash
# 前置条件: Rust + Node.js + VS Build Tools (C++)
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 启动 Python 后端
pip install -e .
pip install fastapi uvicorn
python server.py &

# 启动 Tauri 前端
cd nexus-ui
npm install
npm run tauri dev
```

### PySide6 版

```bash
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant
pip install -e .
python main.py
```

详细说明见 [usage.md](usage.md)

## 项目结构

```
AI-Nexus-Assistant/
├── main.py                     # PySide6 入口
├── server.py                   # FastAPI 后端 API (31 路由)
├── pyproject.toml              # Python 项目配置
│
├── app/                        # Python 核心层
│   ├── db.py                   # 数据库 (SQLAlchemy + SQLite)
│   ├── models/                 # 数据模型 (7个)
│   ├── services/               # 业务逻辑 (7个)
│   ├── ai/                     # AI服务 (OpenAI + Anthropic)
│   ├── search/                 # 搜索引擎 (8源)
│   └── ui/                     # PySide6 前端
│
├── nexus-ui/                   # Tauri 2 前端
│   ├── src/
│   │   ├── api/client.ts       # API 客户端 (连接 FastAPI)
│   │   ├── App.tsx             # 主应用
│   │   ├── components/         # 组件
│   │   └── pages/              # 7 个页面
│   └── src-tauri/              # Rust 壳
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       └── target/release/nexus-ui.exe (11MB)
│
└── data/                       # 运行时数据 (gitignore)
```

## 开发进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 项目骨架 + 任务 + 文献 + 设置 | ✅ 完成 |
| Phase 2 | 试验管理 + 知识库 + AI对话 | ✅ 完成 |
| Phase 3 | 仪表盘 + 时钟 + 命令面板 + 打包备份 | ✅ 完成 |
| Phase 4 | Bug修复 + UI优化 + 无边框窗口 | ✅ 完成 |
| Phase 5 | Tauri 2 前端 + FastAPI 后端 | ✅ 完成 |

详细进展见 [development.md](development.md)

## API 接口

FastAPI 后端提供 31 个 REST 路由：

| 模块 | 路由 | 方法 |
|------|------|------|
| 仪表盘 | `/api/dashboard` | GET |
| 任务 | `/api/tasks` | GET/POST |
| 任务 | `/api/tasks/{id}` | PATCH/DELETE |
| 任务 | `/api/tasks/{id}/toggle` | POST |
| 搜索 | `/api/search` | POST |
| 试验 | `/api/experiments` | GET/POST |
| 试验 | `/api/experiments/{id}/results` | POST |
| 知识库 | `/api/knowledge/cards` | GET/POST |
| 知识库 | `/api/knowledge/cards/{id}` | PATCH/DELETE |
| 知识库 | `/api/knowledge/tags` | GET |
| 对话 | `/api/chat/sessions` | GET/POST |
| 对话 | `/api/chat/sessions/{id}/messages` | GET/POST |
| 对话 | `/api/chat/stream` | POST (SSE) |
| 模型 | `/api/models` | GET/POST/DELETE |
| 历史 | `/api/history` | GET |

API 文档：启动后端后访问 `http://127.0.0.1:8765/docs`

## 相关文档

| 文档 | 说明 |
|------|------|
| [development.md](development.md) | 开发进展与计划 |
| [usage.md](usage.md) | 使用说明 |
| original_design/ | 整合设计方案（本地参考，未上传） |
