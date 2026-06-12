# AI Nexus Assistant

> AI增强个人科研助手 — 整合文献检索、试验管理、知识库、AI对话的统一桌面平台

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-green.svg)](https://doc.qt.io/qtforpython-6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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

- **📊 仪表盘** — 全局统计聚合 + 近期活动流 + 月度完成率
- **📋 任务与日程** — 日历视图 + 待办管理 + 周计划 + 四级优先级
- **📚 8源文献搜索** — OpenAlex, CrossRef, Semantic Scholar, arXiv, PubMed, Google Scholar, Scopus + OpenAlex摘要补全
- **📚 AI综述与选题** — 基于检索结果的结构化综述生成 + 选题讨论
- **🧪 试验管理** — 版本化结果 + 参数快照 + 代码片段存档 + Markdown导出
- **🧠 知识库** — 知识卡片 + 标签分类 + 星级评分 + 从文献/对话生成
- **💬 AI对话** — 流式输出 + thinking折叠 + 写作辅助（润色/翻译/LaTeX/摘要）
- **🔍 命令面板** — Ctrl+K 全局搜索 + 跨模块结果分组 + 页面快速跳转
- **⏰ 桌面时钟** — 辉光管/机械表双模式 + 状态栏嵌入/浮动窗口切换
- **🤖 统一AI服务** — OpenAI + Anthropic 双协议，DeepSeek thinking 内容折叠
- **🎨 暗/亮主题** — Catppuccin 色板，一键切换
- **📦 自动备份** — 1月 + 1周 + 6日备份策略，启动时自动执行

## 技术栈

| 层级 | 技术 |
|------|------|
| GUI | PySide6 (Qt 6) |
| 数据库 | SQLAlchemy 2.0 + SQLite (WAL模式) |
| AI | OpenAI / Anthropic 兼容 API |
| 搜索 | requests + scholarly + arxiv |
| 文件处理 | PyMuPDF + openpyxl + matplotlib + scipy |
| 打包 | PyInstaller |

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 安装依赖
pip install -e .

# 启动应用
python main.py
```

详细使用说明见 [usage.md](usage.md)

## 项目结构

```
AI-Nexus-Assistant/
├── pyproject.toml              # 项目配置
├── main.py                     # 入口点
├── build.py                    # PyInstaller 构建脚本
├── app/
│   ├── db.py                   # 数据库层
│   ├── models/                 # 7 个数据模型
│   ├── services/               # 7 个服务层
│   ├── ai/                     # AI服务层（双协议）
│   ├── search/                 # 搜索引擎（8源）
│   ├── ui/
│   │   ├── main_window.py      # 主窗口（7页导航+状态栏时钟）
│   │   ├── theme.py            # 主题系统
│   │   ├── pages/              # 7 个页面
│   │   ├── widgets/            # 自定义组件
│   │   └── dialogs/            # 对话框（命令面板）
│   └── utils/                  # 工具函数
├── config/                     # 配置文件
└── data/                       # 运行时数据（已gitignore）
```

## 开发进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 项目骨架 + 任务 + 文献 + 设置 | ✅ 完成 |
| Phase 2 | 试验管理 + 知识库 + AI对话 | ✅ 完成 |
| Phase 3 | 仪表盘 + 时钟 + 命令面板 + 打包备份 | ✅ 完成 |

详细进展见 [development.md](development.md)

## 相关文档

| 文档 | 说明 |
|------|------|
| [development.md](development.md) | 开发进展与计划 |
| [usage.md](usage.md) | 使用说明 |
| original_design/ | 整合设计方案（本地参考，未上传） |
