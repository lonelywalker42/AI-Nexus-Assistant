# AI Nexus Assistant

面向航空航天/控制领域科研人员的个人研究助手桌面应用。

## 功能模块

- **仪表盘** — 数据总览、快捷入口
- **任务与日程** — 待办管理、日历视图、优先级分类
- **今日工作** — 每日任务同步、进度看板、工作日志
- **文献检索** — 7 源学术搜索（OpenAlex / arXiv / Semantic Scholar / CrossRef / PubMed / Google Scholar / Scopus）
- **文献库** — PDF 导入、AI 元数据提取、引用格式、综述生成
- **IDEA** — 知识卡片、随手记、AI 对话关联
- **试验管理** — 版本化试验记录、参数对比表、AI 分析
- **AI 对话** — 多模型支持、工具调用（联网搜索）、流式输出、分类管理
- **时钟窗口** — 辉光管时钟 + 音乐播放器 + 频谱可视化 + 倒计时提示音
- **设置** — 模型配置、主题切换、数据备份与恢复、应用重命名

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Tauri 2 + React 19 + TypeScript + Tailwind CSS v4 |
| 后端 | FastAPI + SQLAlchemy + SQLite (WAL) |
| AI | OpenAI / Anthropic 协议，DeepSeek / GPT / Claude |
| 搜索 | open-webSearch 聚合引擎（Bing + DuckDuckGo） |

## 快速开始

```bash
# 安装 Python 依赖
pip install -e .

# 安装前端依赖
cd nexus-ui && npm install

# 开发模式
python server.py                    # 后端 :8765
cd nexus-ui && npm run tauri dev    # Tauri 前端

# 构建
python build_server.py              # 构建 sidecar
python build_tauri.py               # 构建完整 Tauri 应用
```

## 项目结构

```
├── app/                    # Python 后端
│   ├── ai/                 # AI 路由 + 工具调用 + 搜索
│   ├── models/             # SQLAlchemy 模型
│   ├── services/           # 业务逻辑
│   └── search/             # 学术搜索引擎
├── nexus-ui/               # Tauri 前端
│   ├── src/                # React 组件 + 页面
│   ├── src-tauri/          # Rust 壳 + 系统托盘
│   └── public/             # 时钟窗口 + 待办日历
├── server.py               # FastAPI 入口
└── data/                   # 数据目录（SQLite + 备份）
```

## 安装运行

**Windows x64：**
- 下载 `AI Nexus Assistant_x.x.x_x64-setup.exe` 安装
- 或下载 `AI-Nexus-Assistant.exe` + `nexus_ui_lib.dll` 便携运行

**系统要求：**
- Windows 10/11 (x64)
- WebView2 运行时（Windows 10 1803+ 自带）
- Node.js（可选，联网搜索功能需要）

## 许可

MIT License
