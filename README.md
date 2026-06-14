# AI Nexus Assistant

> AI增强个人科研助手 — 整合文献检索、试验管理、知识库、AI对话的统一桌面平台

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Tauri 2](https://img.shields.io/badge/Tauri_2-v1.4.0-orange.svg)](https://tauri.app/)
[![React 19](https://img.shields.io/badge/React_19-TypeScript-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 项目简介

AI Nexus Assistant 将六个独立的科研工具整合为统一的桌面应用，面向航空航天/控制领域研究者，提供从日常事务管理、文献检索与综述、试验进度跟踪、到AI知识库对话的全链路支持。

### 双前端架构

| 版本 | 技术栈 | 包体积 | 状态 |
|------|--------|--------|------|
| **Tauri 2 版** | Rust + React + TypeScript + Tailwind CSS + FastAPI | **~51MB 单文件** | ✅ v1.4.0 |
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

- **全局仪表盘** — 统计聚合 + 近期活动 + 点击跳转对应模块
- **任务与日程** — 日历视图 + 主线任务置顶 + 四级优先级 + 自动换行
- **8源文献搜索** — OpenAlex/CrossRef/Semantic Scholar/arXiv/PubMed/Google Scholar/Scopus
- **AI综述与选题** — 三种数据源(搜索/知识库/自定义) + 自动保存到历史 + 响应式显示 + 历史回看
- **试验管理** — 版本化结果 + 参数快照 + Markdown导出
- **知识库** — 分类视图(文献/AI对话/手动) + 卡片详情 + JSON/MD/PDF导入
- **AI对话** — 流式输出 + Markdown渲染 + thinking折叠 + OpenAI/Anthropic双协议(自动降级)
- **辉光管时钟** — 关闭窗口后弹出 + 右键原生菜单倒计时 + 透明背景 + 滚轮缩放
- **待办日历** — 关闭窗口后弹出 + 无色透明玻璃UI + 3:2宽屏比例 + 深色字体 + Inter字体 + 拖拽移动 + 实时时钟 + 任务切换
- **三套主题** — 浅色/暖色(#F5F0E1)/深色，CSS变量驱动
- **系统托盘** — 关闭最小化到托盘 + 右键显示/退出
- **单文件分发** — 43MB exe，内嵌Python后端，无需额外文件
- **自动备份** — 1月 + 1周 + 6日策略

## 技术架构

```
┌─────────────────────────────────────────────┐
│          Tauri 2 桌面应用 (43MB 单文件)       │
│  ┌───────────────────────────────────────┐  │
│  │  React 19 + TypeScript + Tailwind     │  │
│  │  三套主题 + SVG图标 + 时钟 + 待办日历     │  │
│  └──────────────┬────────────────────────┘  │
│                 │ HTTP REST API              │
│  ┌──────────────▼────────────────────────┐  │
│  │  Python FastAPI 后端 (嵌入式 sidecar)  │  │
│  │  36+ REST 路由                         │  │
│  └──────────────┬────────────────────────┘  │
│                 │                            │
│  ┌──────────────▼────────────────────────┐  │
│  │  服务层                                │  │
│  │  搜索引擎(8源) | AI服务 | 数据库       │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 快速开始

### Tauri 2 版（推荐）

```bash
# 前置条件: Rust + Node.js + VS Build Tools (C++) + Windows SDK
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 安装 Python 依赖
pip install -e .
pip install fastapi uvicorn

# 启动 Python 后端
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

### 便携版（无需开发环境）

下载 `release/AI-Nexus-Assistant.exe` (43MB)，双击即可运行。单文件，无需额外依赖。

详细说明见 [usage.md](usage.md)

## 项目结构

```
AI-Nexus-Assistant/
├── main.py                     # PySide6 入口
├── server.py                   # FastAPI 后端 (36+ 路由)
├── pyproject.toml              # Python 项目配置
├── build_server.py             # 后端 sidecar 构建脚本
├── build_tauri.py              # 一键构建脚本
│
├── app/                        # Python 核心层
│   ├── db.py                   # 数据库 (SQLAlchemy + SQLite)
│   ├── models/                 # 数据模型 (8个)
│   ├── services/               # 业务逻辑 (7个)
│   ├── ai/                     # AI服务 (OpenAI + Anthropic)
│   ├── search/                 # 搜索引擎 (8源)
│   └── ui/                     # PySide6 前端
│
├── nexus-ui/                   # Tauri 2 前端
│   ├── src/
│   │   ├── api/client.ts       # API 客户端
│   │   ├── App.tsx             # 主应用 (无边框窗口+拖拽)
│   │   ├── components/         # 组件
│   │   └── pages/              # 7 个页面
│   ├── public/
│   │   ├── clock.html          # 辉光管时钟
│   │   ├── countdown-input.html# 倒计时输入
│   │   └── todo-calendar.html  # 待办日历
│   └── src-tauri/              # Rust 壳
│       └── capabilities/       # Tauri 2 权限声明 (窗口控制)
│
├── release/                    # 便携版发布文件
│   └── AI-Nexus-Assistant.exe  # 单文件 (43MB，内嵌Python后端)
│
└── data/                       # 运行时数据 (gitignore)
```

## API 接口

FastAPI 后端提供 36+ REST 路由：

| 模块 | 路由 | 方法 | 说明 |
|------|------|------|------|
| 仪表盘 | `/api/dashboard` | GET | 聚合统计 |
| 任务 | `/api/tasks` | GET/POST | CRUD (支持日期筛选) |
| 任务 | `/api/tasks/main` | GET | 所有主线任务 |
| 任务 | `/api/tasks/incomplete` | GET | 所有未完成任务 |
| 任务 | `/api/tasks/{id}/toggle` | POST | 切换完成 |
| 搜索 | `/api/search` | POST | 8源文献搜索 |
| 试验 | `/api/experiments` | GET/POST | CRUD |
| 试验 | `/api/experiments/{id}/results` | POST | 添加结果 |
| 知识库 | `/api/knowledge/cards` | GET/POST | CRUD |
| 知识库 | `/api/knowledge/import/json` | POST | JSON导入 |
| 知识库 | `/api/knowledge/import/pdf` | POST | PDF导入+AI提取 |
| 知识库 | `/api/knowledge/import/md` | POST | Markdown导入 |
| 知识库 | `/api/knowledge/generate` | POST | AI生成卡片 |
| 对话 | `/api/chat/sessions` | GET/POST | 会话管理 |
| 对话 | `/api/chat/stream` | POST | 流式对话(SSE) |
| 模型 | `/api/models` | GET/POST | 模型配置 |
| 模型 | `/api/models/{id}` | PUT/DELETE | 更新/删除模型 |
| 备份 | `/api/backup` | POST | 手动备份 |
| 历史 | `/api/history` | GET/POST | 搜索历史列表/创建 |
| 历史 | `/api/history/{id}` | DELETE | 删除历史记录 |
| 系统 | `/api/system/info` | GET | 数据库大小等系统信息 |

API 文档: `http://127.0.0.1:8765/docs`

## 开发进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 项目骨架 + 任务 + 文献 + 设置 | ✅ 完成 |
| Phase 2 | 试验管理 + 知识库 + AI对话 | ✅ 完成 |
| Phase 3 | 仪表盘 + 时钟 + 命令面板 + 打包备份 | ✅ 完成 |
| Phase 4 | Bug修复 + UI优化 + 无边框窗口 | ✅ 完成 |
| Phase 5 | Tauri 2 前端 + FastAPI 后端 | ✅ 完成 |
| Phase 6 | Issue修复 + 知识库增强 + 窗口控制 | ✅ 完成 |
| Phase 7 | Sidecar优化 + 前端嵌入 + 端口冲突检测 | ✅ 完成 |
| Phase 8 | v1.1.0: 原生菜单 + 暖色主题 + AI修复 + 单文件分发 | ✅ 完成 |
| Phase 9 | v1.2.0: 历史增强 + Markdown渲染 + 数据库信息 | ✅ 完成 |
| Phase 10 | v1.3.0: 待办日历UI重构 + 窗口重复创建修复 + 无色透明玻璃 | ✅ 完成 |
| Phase 11 | v1.4.0: 深色日历 + 无cmd + 滚动隔离 + Web Search | ✅ 完成 |

详细进展见 [development.md](development.md)

## 相关文档

| 文档 | 说明 |
|------|------|
| [development.md](development.md) | 开发进展与计划 |
| [usage.md](usage.md) | 使用说明 |
| original_design/ | 整合设计方案（本地参考，未上传） |
