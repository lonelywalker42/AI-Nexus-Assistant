# 开发环境配置指南

> 面向希望参与开发或进行自定义改造的开发者。普通用户请参考 `usage.md`。

> Windows 正式构建以 [`WINDOWS-BUILD.md`](WINDOWS-BUILD.md) 为准。本文保留跨平台开发说明；不要再通过手工拼接 MSVC 路径或全局 `npx tauri` 制作发布包。

---

## 目录

- [1. 架构概览](#1-架构概览)
- [2. 系统要求](#2-系统要求)
- [3. 克隆仓库与 Submodule](#3-克隆仓库与-submodule)
- [4. Python 后端环境](#4-python-后端环境)
- [5. Node.js 前端环境](#5-nodejs-前端环境)
- [6. Rust / Tauri 环境](#6-rust--tauri-环境)
- [7. open-webSearch 子模块](#7-open-websearch-子模块)
- [8. 开发模式启动](#8-开发模式启动)
- [9. 构建流程](#9-构建流程)
- [10. 版本号同步清单](#10-版本号同步清单)
- [11. 常见问题排查](#11-常见问题排查)
- [12. 各平台额外说明](#12-各平台额外说明)

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    Tauri 2 Shell (Rust)              │
│  ┌───────────────────────────────────────────────┐  │
│  │          React 19 + TypeScript + Tailwind     │  │
│  │              (nexus-ui/src/)                   │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │ HTTP (localhost:8765)         │
│  ┌───────────────────▼───────────────────────────┐  │
│  │       FastAPI Backend (server.py)              │  │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────────┐  │  │
│  │  │ models/ │ │ services/│ │ search/ + ai/ │  │  │
│  │  └─────────┘ └──────────┘ └───────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│                      │                               │
│  ┌───────────────────▼───────────────────────────┐  │
│  │  SQLite (data/nexus.db) + PDFs (data/pdfs/)   │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         ▲
         │ HTTP (localhost:3210)
┌────────▼────────┐
│ open-webSearch  │  ← git submodule, Node.js 独立进程
│ (Bing/DDG/...)  │
└─────────────────┘
```

**两种运行模式:**

| 模式 | 前端 | 后端 | 启动方式 |
|------|------|------|----------|
| **Tauri 开发** | Vite dev server (:1420) | `python server.py` (:8765) | 两个终端 |
| **PySide6** | Qt 窗口 | 同进程 | `python main.py` |

---

## 2. 系统要求

### 必需

| 依赖 | 最低版本 | 用途 | 安装方式 |
|------|---------|------|----------|
| **Python** | 3.10 | 后端运行时 | `winget install Python.Python.3.12` |
| **Node.js** | 18 LTS | 前端构建 + open-webSearch | `winget install OpenJS.NodeJS.LTS` |
| **Rust** | 1.70 (stable) | Tauri Shell 编译 | `winget install Rustlang.Rustup` |
| **Git** | 2.30 | 版本控制 + submodule | `winget install Git.Git` |

### Windows 专属

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| **Visual Studio Build Tools** | C++ 编译器 + Windows SDK | [下载页面](https://aka.ms/vs/17/release/vs_BuildTools.exe)，勾选「C++ 桌面开发」工作负载 |
| **Windows 10/11 SDK** | 系统库链接 | 随 VS Build Tools 一起安装，或 `winget install Microsoft.WindowsSDK.10.0.26100` |
| **WebView2** | Tauri 运行时渲染 | Windows 10/11 自带，若缺失可从 [Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) 安装 |

### 可选

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| **MinerU** (`magic-pdf`) | PDF 转 Markdown | `pip install magic-pdf` |
| **CUDA Toolkit** | sentence-transformers GPU 加速 | [NVIDIA CUDA](https://developer.nvidia.com/cuda-toolkit) |

---

## 3. 克隆仓库与 Submodule

```bash
# 克隆（含 submodule 递归）
git clone --recursive https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 如果已克隆但 submodule 为空：
git submodule update --init --recursive
```

**验证 submodule:**
```bash
ls open-webSearch/package.json   # 应存在
git submodule status              # 应显示 commit hash，无 '-' 前缀
```

**后续更新 submodule:**
```bash
cd open-webSearch
git pull origin main
cd ..
git add open-webSearch
git commit -m "chore: update open-webSearch submodule"
```

---

## 4. Python 后端环境

### 4.1 创建虚拟环境（推荐）

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 4.2 安装依赖

```bash
# PySide6 桌面开发
pip install -e ".[desktop]"

# Tauri/FastAPI 后端开发
pip install -e ".[tauri]"

# 测试与构建工具
pip install -e ".[tauri,build,test]"

# 可选：PDF 转 Markdown
pip install magic-pdf

# 可选：向量数据库 + 语义搜索（需要 C++ 编译器）
pip install -e ".[full]"
```

### 4.3 依赖说明

| 包 | 说明 | 注意事项 |
|----|------|----------|
| `PySide6` | Qt6 框架（仅 PySide6 版需要） | 体积 ~100MB，Tauri 开发模式可跳过 |
| `PyMuPDF` (fitz) | PDF 解析 + 元数据提取 | 自带预编译 wheel，无需额外系统库 |
| `python-docx` | DOCX 导出 | `pip install python-docx`（未在 pyproject.toml 中，需单独安装） |
| `fastapi` + `uvicorn` | Tauri 后端 HTTP 服务 | 不在 pyproject.toml 中，需手动安装 |
| `openai` + `anthropic` | AI 模型调用 | 支持 OpenAI 协议 + Anthropic 协议 |
| `httpx` | HTTP 客户端 | openai 库的依赖，`proxy=None` 绕过本地代理 |
| `SQLAlchemy` | ORM | 2.0+ 使用 `Mapped[]` 风格 |
| `scholarly` | Google Scholar 爬取 | 可能被限流，建议配合代理 |

### 4.4 验证安装

```bash
python -c "import fastapi, uvicorn, openai, anthropic, httpx, fitz, docx; print('All OK')"
```

---

## 5. Node.js 前端环境

### 5.1 安装依赖

```bash
cd nexus-ui
npm ci

# 如果网络慢，使用镜像源
npm ci --registry https://registry.npmmirror.com
```

### 5.2 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 3.4 | 样式系统 |
| Vite | 6.x | 构建工具 + HMR |
| @tauri-apps/api | 2.x | Tauri IPC 调用 |
| react-markdown | 9.x | Markdown 渲染 |
| rehype-katex / remark-math | — | 数学公式 |
| pdfjs-dist | 6.x | PDF 预览 |

### 5.3 类型检查

```bash
cd nexus-ui
npx tsc --noEmit    # 零错误才算通过
```

---

## 6. Rust / Tauri 环境

### 6.1 安装 Rust

```bash
# 安装 rustup（Rust 版本管理器）
winget install Rustlang.Rustup

# 或手动下载: https://rustup.rs

# 验证
rustc --version    # >= 1.70
cargo --version
```

### 6.2 确认 MSVC 工具链

```bash
rustup show
# 应显示: stable-x86_64-pc-windows-msvc (default)
```

如果没有 MSVC 工具链：
```bash
rustup default stable-x86_64-pc-windows-msvc
```

### 6.3 Tauri CLI

```bash
# 使用项目锁定的本地版本；正式构建禁止依赖全局 Tauri CLI
cd nexus-ui
npm run tauri -- --version   # 应为 2.x
```

### 6.4 Cargo 依赖一览

| Crate | 用途 |
|-------|------|
| `tauri` 2 (feature: tray-icon) | 应用壳 + 系统托盘 |
| `tauri-plugin-shell` | 打开外部链接 |
| `tauri-plugin-updater` | 自动更新（Ed25519 签名） |
| `tauri-plugin-process` | 进程重启 |
| `tauri-plugin-os` | 系统信息 |
| `tauri-plugin-dialog` | 文件对话框 |
| `serde` + `serde_json` | JSON 序列化 |
| `time` =0.3.36 | 时间处理（精确版本锁定） |
| `base64` | 文件 Base64 编码 |

### 6.5 架构说明

```
nexus-ui/src-tauri/
├── Cargo.toml          # Rust 依赖配置
├── Cargo.lock          # 锁定版本（已提交）
├── tauri.conf.json     # Tauri 应用配置
├── build.rs            # 构建脚本（嵌入 sidecar）
├── capabilities/       # 权限声明
│   ├── default.json    # 桌面端权限
│   └── mobile.json     # 移动端权限
├── binaries/           # sidecar 二进制（.gitignore）
├── icons/              # 应用图标
└── src/
    ├── main.rs         # 入口（调用 lib.rs::run()）
    └── lib.rs          # 核心逻辑（~700 行）
        - 后端 sidecar 生命周期管理
        - 系统托盘 + 菜单
        - 子窗口管理（时钟、日历、游戏机）
        - IPC 命令（文件读取、音频列表）
```

---

## 7. open-webSearch 子模块

### 7.1 概述

`open-webSearch/` 是一个独立的 Node.js 项目，聚合多个搜索引擎（Bing、DuckDuckGo、Brave、Wikipedia、Arxiv）。作为 git submodule 引入。

### 7.2 构建

```bash
cd open-webSearch
npm ci
npm run build          # TypeScript 编译 → build/
cd ..
```

### 7.3 验证

```bash
# 启动测试（默认端口 3210）
cd open-webSearch
npm start
# 另一个终端:
curl http://127.0.0.1:3210/health
```

### 7.4 与后端的关系

- `server.py` 启动时自动通过 `search_service.py` 启动 open-webSearch 守护进程
- 端口 3210，健康检查 `GET /health`
- 如果 Node.js 不可用，自动降级为 DuckDuckGo 直连搜索

---

## 8. 开发模式启动

### 8.1 Tauri 开发模式（推荐）

需要 **两个终端**：

```bash
# 终端 1: 启动 FastAPI 后端
cd AI-Nexus-Assistant
python server.py
# 等待输出: NEXUS_SERVER_READY:8765

# 终端 2: 启动 Tauri 开发模式（Vite HMR + Rust 热编译）
cd AI-Nexus-Assistant/nexus-ui
npm run tauri dev
```

**开发模式行为:**
- 前端: Vite dev server 在 `localhost:1420`，修改 React 代码自动热更新
- 后端: `python server.py` 在 `localhost:8765`，修改 Python 代码需手动重启
- Rust: 修改 `lib.rs` 后 Tauri 自动重新编译（首次较慢，后续增量编译）

### 8.2 PySide6 开发模式

```bash
cd AI-Nexus-Assistant
python main.py
```

### 8.3 仅前端开发（不编译 Rust）

```bash
cd nexus-ui
npm run dev           # Vite dev server on :1420
# 浏览器访问 http://localhost:1420
# 需要后端运行在 :8765
```

---

## 9. 构建流程

### 9.1 开发期间快速验证

```bash
# 仅类型检查（不构建）
cd nexus-ui && npx tsc --noEmit

# 仅构建前端（不编译 Rust）
cd nexus-ui && npm run build
```

### 9.2 完整 Tauri 构建

```bash
# Windows 一键构建（推荐，使用隔离环境）
powershell -ExecutionPolicy Bypass -File scripts/windows/setup-build-env.ps1
powershell -ExecutionPolicy Bypass -File scripts/windows/build-release.ps1 -CleanOutputs
```

**`build_tauri.py` 执行 3 个步骤:**

```
Step 1: build_server.py
  └─ PyInstaller 打包 server.py → release/nexus-server-*.exe (~31MB)
  └─ 复制到 nexus-ui/src-tauri/binaries/

Step 2: npm run tauri:build
  └─ beforeBuildCommand: npm run build (Vite → dist/)
  └─ cargo build --release (Rust 编译)
  └─ build.rs: 复制 sidecar 到 OUT_DIR
  └─ lib.rs: include_bytes!() 嵌入 sidecar + 前端资源
  └─ 生成 MSI/NSIS 安装包

Step 3: 整理到 release/
  └─ AI-Nexus-Assistant.exe (主程序)
  └─ nexus_ui_lib.dll (WebView2 loader)
  └─ open-webSearch/ (搜索引擎)
```

### 9.3 分步构建

```bash
# Step 1: 构建 sidecar
python build_server.py

# Step 2: 构建 Tauri（前端 + Rust + 打包）
cd nexus-ui && npm run tauri:build

# Step 3: 手动整理（或运行 build_tauri.py 的 step3）
```

### 9.4 仅构建 PySide6 版

```bash
python build.py
# 输出: dist/AI-Nexus-Assistant/
```

### 9.5 构建产物

```
release/
├── AI-Nexus-Assistant.exe    # 便携版主程序 (~51MB)
├── nexus_ui_lib.dll          # WebView2 loader
├── open-webSearch/           # 搜索引擎 (Node.js)
│   ├── build/
│   ├── node_modules/
│   └── package.json
├── latest.json               # 自动更新元数据
└── *.exe / *.msi             # 安装包（可选）
```

---

## 10. 版本号同步清单

`VERSION` 是发布版本的规范值。发版时同步更新 `pyproject.toml`、npm package/lock、Tauri config、Cargo package/lock、前端 `APP_VERSION` 和 FastAPI 版本，然后运行：

```powershell
.build-env\python\Scripts\python.exe tools\project_check.py
```

任意发布元数据不一致都会返回非零退出码并阻止正式构建。界面上的登录页和 PySide6 版本标签也由检查脚本覆盖。

---

## 11. 常见问题排查

### Python 相关

| 问题 | 解决方案 |
|------|----------|
| `pip install -e .` 失败 | 使用 Python 3.10–3.13 x64；正式构建推荐 3.12 |
| `ModuleNotFoundError: No module named 'fastapi'` | 运行 `pip install -e ".[tauri]"` |
| `ModuleNotFoundError: No module named 'fitz'` | `pip install PyMuPDF` |
| `ModuleNotFoundError: No module named 'docx'` | `python-docx` 已在核心依赖中；重新安装项目依赖 |
| PySide6 安装太慢/太大 | Tauri 开发模式不需要 PySide6，可跳过 |
| `chromadb` 安装失败 | 需要 C++ 编译器（VS Build Tools），或跳过 `pip install -e ".[full]"` |

### Node.js 相关

| 问题 | 解决方案 |
|------|----------|
| `npm ci` 网络超时 | `npm ci --registry https://registry.npmmirror.com` |
| `npm run dev` 端口 1420 被占用 | 关闭占用进程，或修改 `vite.config.ts` 中的 `strictPort` |
| TypeScript 类型错误 | `npx tsc --noEmit` 查看详情 |

### Rust / Tauri 相关

| 问题 | 解决方案 |
|------|----------|
| `cargo build` 报错 "linker not found" | 安装 VS Build Tools C++ 工作负载 |
| `tauri build` 报错 "Windows SDK not found" | 安装 Windows 10/11 SDK |
| `time` crate 编译错误 | 确认 `time = "=0.3.36"` 精确版本（已锁定） |
| 首次编译极慢（10+ 分钟） | 正常现象，Tauri + 依赖首次编译较慢，后续增量编译很快 |
| `include_bytes!` 报错 "file not found" | 需先运行 `build_server.py` 生成 sidecar 到 `binaries/` |
| 修改 Rust 代码后不生效 | `npm run tauri dev` 会自动检测变更并重新编译 |

### 运行时相关

| 问题 | 解决方案 |
|------|----------|
| 端口 8765 被占用 | `netstat -ano \| findstr 8765` 找到进程并终止 |
| 端口 3210 被占用 | open-webSearch 端口冲突，重启应用 |
| open-webSearch 不工作 | `cd open-webSearch && npm ci && npm run build` |
| "localhost 拒绝连接" | 确认 `python server.py` 已启动并输出 `NEXUS_SERVER_READY:8765` |
| PDF 拉取失败 | 检查网络/代理，部分出版社需要校园网或 VPN |
| AI 功能不工作 | 在设置页配置 AI 模型（API Key + Base URL） |

---

## 12. 各平台额外说明

### Windows（主要开发平台）

- 项目主要在 Windows 上开发和测试
- `build_tauri.py` 通过 `vswhere.exe` + `VsDevCmd.bat` 自动加载完整 MSVC/SDK 环境，不允许硬编码工具链路径
- 正式构建流程、干净依赖目录和故障排查见 [`WINDOWS-BUILD.md`](WINDOWS-BUILD.md)
- Rust 进程管理使用 `taskkill /F /T` 和 `CREATE_NO_WINDOW` 标志

### macOS

- 需要安装 Xcode Command Line Tools: `xcode-select --install`
- Tauri 编译目标: `aarch64-apple-darwin` (Apple Silicon) 或 `x86_64-apple-darwin` (Intel)
- 系统托盘使用 macOS 原生 API

### Linux

- 需要安装系统依赖:
  ```bash
  # Debian/Ubuntu
  sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

  # Fedora
  sudo dnf install webkit2gtk4.1-devel gtk3-devel libappindicator-gtk3-devel librsvg2-devel
  ```
- `pystray` 需要 `libappindicator` 或 GTK

### Android / iOS

- 参考 `.github/workflows/build-android.yml` 和 `build-ios.yml`
- 需要额外安装 Android NDK / Xcode
- 移动端使用 `capabilities/mobile.json` 权限配置
