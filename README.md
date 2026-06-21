# AI Nexus Assistant

> AI增强个人科研助手 — 整合文献管理、试验管理、知识库、AI对话、音乐播放、电子书阅读的统一桌面平台

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Tauri 2](https://img.shields.io/badge/Tauri_2-v3.5.0-orange.svg)](https://tauri.app/)
[![React 19](https://img.shields.io/badge/React_19-TypeScript-cyan.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 项目简介

AI Nexus Assistant 面向航空航天/控制领域研究者，提供从日常事务管理、文献检索与综述、试验进度跟踪、AI知识库对话、到个人音乐/阅读的全链路支持。

### 双前端架构

| 版本 | 技术栈 | 包体积 | 状态 |
|------|--------|--------|------|
| **Tauri 2 版** | Rust + React 19 + TypeScript + Tailwind CSS v4 + FastAPI | **~83MB 单文件** | ✅ v3.5.0 |
| **PySide6 版** | Python + PySide6 + SQLAlchemy | ~235MB | ✅ 功能完整 |

## 功能模块

### 总览

| 模块 | 功能 |
|------|------|
| **仪表盘** | 数据总览、快捷入口、活动流 |
| **任务与日程** | 日历视图、主线任务、四级优先级(低/普通/高/紧急)、分类(日常/核心/文献/试验) |
| **今日工作** | 每日任务同步、进度看板、实时钟表、工作日志(localStorage持久化) |

### 科研助手

| 模块 | 功能 |
|------|------|
| **文献检索** | 7源学术搜索(OpenAlex/arXiv/Semantic Scholar/CrossRef/PubMed/Google Scholar/Scopus)、布尔检索(AND/OR/NOT)、列表/网格视图切换、综述池FAB浮动按钮、AI综述生成(自定义章节结构)、批量导入文献库 |
| **文献库** | PDF批量导入+AI元数据提取、引用格式(GB/T 7714/APA/IEEE/MLA/BibTeX)、AI摘要、批量操作、详情面板自适应 |
| **IDEA** | 知识卡片CRUD、随手记(快速记录想法)、AI对话关联、标签系统(支持层级标签)、JSON/MD/PDF导入、网页链接导入、知识图谱可视化、批量操作(导出/删除) |
| **试验管理** | 版本化结果记录、参数对比表、AI分析、Git集成(状态/快照)、结构化参数编辑、README自动生成、归档打包、实验并排对比 |
| **AI 对话** | 流式输出、工具调用(联网搜索+结构化卡片展示)、thinking折叠、分类管理、停止生成按钮、消息重新生成、会话搜索、Token统计、@引用文献 |
| **写作工作台** | 三栏布局(文档列表+关联文献 \| 编辑器+预览 \| AI助手)、Markdown编辑+实时预览、AI润色/翻译/扩写/精简/LaTeX转换、文献引用插入、自动保存 |
| **科研 Agent** | 5种Agent工作流：文献综述(多源检索+综合报告)、论文写作(分章节撰写)、实验设计(假设+方案+代码)、同行评审(5维评分)、多视角讨论(4视角辩论) |

### 个人助手

| 模块 | 功能 |
|------|------|
| **音乐** | 唱片旋转UI、频谱可视化(Web Audio API + Canvas)、jsmediatags元数据提取(标题/艺术家/封面/歌词)、文件夹加载、顺序/循环/随机播放、IndexedDB持久化(懒加载架构)、播放进度同步到时钟 |
| **书架** | 书脊风格网格、EPUB/TXT/MD阅读器、书籍详情(封面/作者/简介)、阅读进度持久化、IndexedDB懒加载、Markdown渲染+数学公式 |
| **素材库** | 即将推出 |

### 时钟窗口(辉光管时钟)

- CSS辉光管效果 + 透明模式
- **音乐播放器**: 文件夹加载、频谱可视化、顺序/随机播放
- **倒计时**: 自定义时长、结束提示音(可自定义)、手动停止按钮
- **游戏机模式**: 2048 / Tetris / 射击 / Word Hopper打字练习(复古像素风格、CRT扫描线、CET-6词汇)
- 右键原生菜单、双击返回主窗口、滚轮缩放(0.6x-2.5x)
- 窗口关闭时自动隐藏(不销毁)，保留播放状态

### 设置

- AI模型配置(OpenAI/Anthropic协议、多模型管理)
- 三套主题(浅色/暖色/深色) + 3种自定义配色方案(主色/强调色/背景渐变)
- 应用名称自定义
- 数据备份与恢复(.db + .db-wal + .db-shm 完整三文件)
- ZIP导出/导入
- 联网搜索服务状态

## 技术架构

```
┌─────────────────────────────────────────────┐
│          Tauri 2 桌面应用 (~71MB 单文件)      │
│  ┌───────────────────────────────────────┐  │
│  │  React 19 + TypeScript + Tailwind v4  │  │
│  │  10个页面 + 30+图标 + 三套主题+自定义   │  │
│  │  音乐播放器 + EPUB阅读器 + 游戏机       │  │
│  └──────────────┬────────────────────────┘  │
│                 │ HTTP REST API              │
│  ┌──────────────▼────────────────────────┐  │
│  │  Python FastAPI 后端 (嵌入式 sidecar)  │  │
│  │  40+ REST 路由 + SSE 流式              │  │
│  └──────────────┬────────────────────────┘  │
│                 │                            │
│  ┌──────────────▼────────────────────────┐  │
│  │  服务层                                │  │
│  │  搜索引擎(7源) | AI服务(工具调用)      │  │
│  │  数据库(SQLite WAL) | 备份服务         │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 快速开始

### 开发环境

```bash
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# Python 依赖
pip install -e .
pip install fastapi uvicorn openai anthropic

# 前端依赖
cd nexus-ui && npm install

# 联网搜索(可选, 需要 Node.js)
cd open-webSearch && npm install && npm run build

# 开发模式(两个终端)
python server.py                    # 后端 :8765
cd nexus-ui && npm run tauri dev    # Tauri 前端
```

### 构建

```bash
python build_server.py              # 构建 Python sidecar exe
python build_tauri.py               # 完整构建(Tauri + sidecar + 前端)
```

### 便携版

下载 `release/AI-Nexus-Assistant.exe` + `release/nexus_ui_lib.dll`，同目录运行。

## 项目结构

```
AI-Nexus-Assistant/
├── server.py                   # FastAPI 后端 (40+ 路由)
├── build_server.py             # sidecar 构建脚本
├── build_tauri.py              # 一键构建脚本
├── CLAUDE.md                   # 项目指南 + 开发体系
├── README.md                   # 本文件
│
├── app/                        # Python 核心层
│   ├── db.py                   # SQLAlchemy + SQLite(WAL)
│   ├── models/                 # 数据模型 (8个)
│   ├── services/               # 业务逻辑
│   │   ├── task_service.py     # 任务CRUD+日历+统计
│   │   ├── paper_service.py    # 文献CRUD+引用+AI摘要
│   │   ├── chat_service.py     # 对话管理+消息持久化
│   │   ├── backup_service.py   # 备份(3文件+WAL checkpoint)
│   │   └── ...
│   ├── ai/
│   │   ├── router.py           # AI服务(OpenAI/Anthropic+工具调用)
│   │   ├── web_search.py       # 联网搜索(代理绕过+多引擎)
│   │   └── tools/              # 工具注册系统
│   └── search/                 # 7源学术搜索引擎
│
├── nexus-ui/                   # Tauri 2 前端
│   ├── src/
│   │   ├── api/client.ts       # API客户端(40+接口)
│   │   ├── App.tsx             # 主应用(路由+窗口控制)
│   │   ├── components/
│   │   │   ├── Sidebar.tsx     # 分组导航(总览/科研/个人/设置)
│   │   │   └── Icons.tsx       # 30+ SVG图标
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx   # 仪表盘
│   │   │   ├── TaskPage.tsx    # 任务与日程
│   │   │   ├── TodayPage.tsx   # 今日工作
│   │   │   ├── LiteraturePage.tsx # 文献检索
│   │   │   ├── PaperLibraryPage.tsx # 文献库
│   │   │   ├── KnowledgePage.tsx # IDEA
│   │   │   ├── ExperimentPage.tsx # 试验管理
│   │   │   ├── ChatPage.tsx    # AI对话
│   │   │   ├── MusicPage.tsx   # 音乐播放器
│   │   │   ├── BookshelfPage.tsx # 书架+EPUB阅读器
│   │   │   └── SettingsPage.tsx # 设置
│   │   ├── hooks/useAppName.ts # 自定义应用名
│   │   ├── utils/toast.ts      # Toast通知
│   │   └── styles.css          # 全局样式(3主题+自定义配色)
│   ├── public/
│   │   ├── clock.html          # 辉光管时钟+音乐+游戏
│   │   ├── todo-calendar.html  # 待办日历
│   │   └── games.html          # 复古游戏(2048/Tetris/Shooter)
│   └── src-tauri/
│       ├── src/lib.rs          # Rust壳(窗口管理+IPC)
│       └── capabilities/       # Tauri 2 权限
│
├── release/                    # 便携版发布文件
│   ├── AI-Nexus-Assistant.exe  # 主程序
│   ├── nexus_ui_lib.dll        # WebView2 loader
│   └── data/                   # 运行时数据
│
└── data/                       # 开发环境数据 (gitignore)
```

## API 接口

FastAPI 后端提供 40+ REST 路由：

| 模块 | 路由 | 方法 | 说明 |
|------|------|------|------|
| 仪表盘 | `/api/dashboard` | GET | 聚合统计 |
| 任务 | `/api/tasks` | GET/POST | CRUD (日期筛选) |
| 任务 | `/api/tasks/main` | GET | 主线任务 |
| 任务 | `/api/tasks/incomplete` | GET | 未完成任务 |
| 任务 | `/api/tasks/{id}/toggle` | POST | 切换完成 |
| 搜索 | `/api/search` | POST | 7源文献搜索 |
| 文献 | `/api/papers` | GET/POST | 文献库CRUD |
| 文献 | `/api/papers/{id}/citation` | GET | 引用格式 |
| 文献 | `/api/papers/{id}/ai-summary` | POST | AI摘要 |
| 试验 | `/api/experiments` | GET/POST | CRUD |
| 试验 | `/api/experiments/{id}/ai-analysis` | POST | AI分析 |
| 知识库 | `/api/knowledge/cards` | GET/POST | 卡片CRUD |
| 知识库 | `/api/knowledge/import/json` | POST | JSON导入 |
| 知识库 | `/api/knowledge/import/pdf` | POST | PDF导入+AI提取 |
| 知识库 | `/api/knowledge/import/md` | POST | Markdown导入 |
| 对话 | `/api/chat/sessions` | GET/POST | 会话管理 |
| 对话 | `/api/chat/stream` | POST | 流式对话(SSE+工具调用) |
| 模型 | `/api/models` | GET/POST | 模型配置 |
| 备份 | `/api/backup` | POST | 手动备份(3文件) |
| 备份 | `/api/backups/export-db` | GET | ZIP导出 |
| 备份 | `/api/backups/import-db` | POST | 导入(.db/.zip) |
| 历史 | `/api/history` | GET/POST | 搜索历史 |
| 系统 | `/api/system/info` | GET | 系统信息 |

API 文档: `http://127.0.0.1:8765/docs`

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v3.5.0 | 2026-06-21 | 科研助手功能增强（PDF元数据提取、FTS5索引、语义搜索、引用图谱、主题聚类、工作区） |
| v3.1.0 | 2026-06-20 | 音乐播放器无缝切换、懒加载优化、Toast通知 |
| v3.2.0 | 2026-06-20 | 写作工作台、布尔检索、智能综述、研究讨论、Markdown渲染升级 |
| v3.3.0 | 2026-06-20 | Git集成、结构化参数、知识库增强搜索、网格视图 |
| v3.4.0 | 2026-06-20 | 对话导出、README生成、归档打包、写作模板 |
| v3.4.1 | 2026-06-21 | 播放同步修复、Word Hopper打字练习、CET-6词汇库 |
| v3.0.0 | 2026-06-19 | 个人助手(音乐/书架)、iOS UI、自定义配色 |
| v2.2.2 | 2026-06-19 | 倒计时音乐交互修复、开发体系文档 |
| v2.2.1 | 2026-06-19 | 音乐IndexedDB持久化修复 |
| v2.2.0 | 2026-06-18 | 时钟音乐播放器、备份修复、搜索修复 |
| v2.1.0 | 2026-06-18 | 今日工作、侧边栏重构、文献UI升级、IDEA随手记 |
| v2.0.0 | 2026-06-17 | 科研助手全面升级(文献库/试验/Chat/AI工具) |
| v1.4.0 | 2026-06-14 | 深色日历、无cmd启动、Web Search |
| v1.3.0 | 2026-06-14 | 待办日历UI重构、透明玻璃模式 |
| v1.2.0 | 2026-06-13 | 历史增强、Markdown渲染 |
| v1.1.0 | 2026-06-13 | 原生菜单、暖色主题 |

完整变更记录见 [CHANGELOG.md](nexus-ui/CHANGELOG.md)

## 致谢

- [ScholarAIO](https://github.com/ZimoLiao/scholaraio) — AI-Native Research Terminal，由 Zi-Mo Liao 开发（MIT 许可证）。ScholarAIO 的科研基础设施设计为本项目的文献管理、混合搜索、主题发现、引用图谱等功能改进提供了重要参考。详见 [docs/SCHOLARAIO_REFERENCE.md](docs/SCHOLARAIO_REFERENCE.md)。

## 许可

MIT License
