# AI Nexus Assistant

> AI增强个人科研助手 — 整合文献检索、试验管理、知识库、AI对话的统一桌面平台

## 项目简介

AI Nexus Assistant 将六个独立的科研工具整合为一个统一的 PySide6 桌面应用，面向航空航天/控制领域研究者，提供从日常事务管理、文献检索与综述、试验进度跟踪、到AI知识库对话的全链路支持。

### 整合的源项目

| 源项目 | 原功能 | 整合后的角色 |
|--------|--------|-------------|
| ai-todo | 待办日历 | 📋 任务与日程模块 |
| ai-literature | 文献检索与综述 | 📚 文献管理模块 |
| ai-researchers | 多源文献搜索 | 🔍 搜索引擎后端 |
| ai-research-manager | 试验与进度管理 | 🧪 试验管理模块 |
| clock-1999 | 桌面时钟 | ⏰ 时钟组件 |
| DeepseekManager | 知识库与AI对话 | 🧠 知识库 + 💬 AI对话 |

### 核心特性

- **8源文献搜索** — OpenAlex, CrossRef, Semantic Scholar, arXiv, PubMed, Google Scholar, Scopus + OpenAlex摘要补全
- **统一AI服务** — 支持 OpenAI 和 Anthropic 双协议，thinking 内容折叠显示
- **任务与日程** — 日历视图 + 待办管理 + 周计划 + 优先级
- **试验管理** — 版本化结果 + 参数对比 + 代码片段存档 + CSV/mat 导出
- **知识库** — PDF导入 + 知识卡片 + 语义搜索（可选ChromaDB）
- **AI对话** — 写作辅助 + 通用问答 + 跨模块联动
- **暗/亮主题** — Catppuccin 色板，一键切换
- **系统托盘** — 关闭最小化到托盘，快速操作

## 技术栈

| 层级 | 技术 |
|------|------|
| GUI | PySide6 (Qt 6) |
| 数据库 | SQLAlchemy 2.0 + SQLite (WAL模式) |
| AI | OpenAI / Anthropic 兼容 API |
| 搜索 | requests + scholarly + arxiv |
| 文件处理 | PyMuPDF + openpyxl + matplotlib + scipy |
| 打包 | PyInstaller |

## 项目结构

```
ai_coding_research/
├── pyproject.toml              # 项目配置
├── main.py                     # 入口点
├── app/
│   ├── db.py                   # 数据库层
│   ├── models/                 # 数据模型
│   ├── services/               # 业务逻辑
│   ├── ai/                     # AI服务层
│   ├── search/                 # 搜索引擎（8源）
│   │   ├── engine.py           # 统一搜索引擎
│   │   ├── scorer.py           # 相似度评分
│   │   ├── citation.py         # GB/T 7714引用
│   │   └── sources/            # 8个数据源适配器
│   ├── ui/                     # PySide6界面
│   │   ├── main_window.py      # 主窗口
│   │   ├── theme.py            # 主题系统
│   │   ├── pages/              # 页面
│   │   └── widgets/            # 组件
│   └── utils/                  # 工具函数
├── config/                     # 配置文件
└── data/                       # 运行时数据
```

## 快速开始

详见 [usage.md](usage.md)

## 开发进度

详见 [development.md](development.md)

## 相关文档

| 文档 | 说明 |
|------|------|
| [design_framework.md](AI增强个人助手-整合设计方案.md) | 整合设计方案（60KB） |
| [source_analysis.md](源项目分析报告.md) | 源项目技术分析 |
| [requirements.md](需求确认书.md) | 需求确认书（29项决策） |
| [development.md](development.md) | 开发进展与计划 |
| [usage.md](usage.md) | 使用说明 |
