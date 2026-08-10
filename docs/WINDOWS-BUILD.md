# Windows PC 构建环境与发布流程

本文是 Windows 桌面版的规范构建入口。目标是让 Python sidecar、React 前端和 Rust/Tauri 壳使用可追踪、互不污染的依赖路径。

## 1. 构建产物与边界

完整发布由两层 EXE 组成：

1. `build_server.py` 使用 PyInstaller 构建 `nexus-server-x86_64-pc-windows-msvc.exe`。
2. Tauri 的 `build.rs` 将 sidecar 嵌入 Rust 主程序，最终生成 `release/AI-Nexus-Assistant.exe`。

React/Vite 前端不是独立 EXE，而是先生成静态资源，再由 Tauri 嵌入主程序。`open-webSearch` 是额外的 Node.js 服务；当前发布包包含其 JavaScript 和 `node_modules`，但不包含 Node.js 运行时，因此使用联网搜索的目标 PC 仍需安装 Node.js。

## 2. 工具链要求

| 工具 | 规范 | 用途 |
|---|---|---|
| Windows | Windows 10/11 x64 | 唯一受支持的正式发布平台 |
| Python | CPython 3.12 x64 推荐；支持 3.10–3.13 | FastAPI、PyInstaller |
| Node.js | 18+ x64，优先使用当前 LTS | React/Vite、open-webSearch |
| Rust | stable `x86_64-pc-windows-msvc` | Tauri 壳 |
| Visual Studio | VS 2022 Build Tools | MSVC linker 和 Windows 原生库 |
| Windows SDK | Windows 10/11 SDK | Win32/UCRT 头文件和库 |
| Git | Windows x64 正式版 | Submodule 和版本管理 |
| WebView2 | Evergreen Runtime | 应用运行时；Windows 11 通常已包含 |

Visual Studio Installer 至少选择：

- `Desktop development with C++` / `Microsoft.VisualStudio.Workload.VCTools`
- MSVC v143 x64/x86 build tools
- Windows 10 或 Windows 11 SDK
- C++ CMake tools（推荐，非当前构建硬依赖）

不要使用 MinGW Rust、MSYS2/Cygwin Python、Conda Python 或全局安装的 Tauri CLI 构建正式版本。

## 3. 干净路径约定

源码建议放在短、纯 ASCII、非同步盘路径，例如：

```text
C:\src\AI-Nexus-Assistant
```

当前 `C:\AiTools\Nexus` 也符合要求。避免 OneDrive、网络盘，以及包含 `& ; !` 等 shell 字符的目录。

系统工具链可以安装在各自的标准目录；项目依赖必须隔离在以下位置：

```text
.build-env/
├── python/             # 仓库专用 Python venv
├── npm-cache/          # 仓库专用 npm 下载缓存
├── cargo-target/       # 仓库专用 Rust 编译输出
├── environment.json    # 实际使用的工具路径和版本
└── python-packages.txt # 本次解析出的完整 Python 包版本

nexus-ui/node_modules/       # 由 package-lock.json + npm ci 生成
open-webSearch/node_modules/  # 由 package-lock.json + npm ci 生成
```

关键原则：

- Python 构建只能从 `.build-env/python` 运行。
- Node 依赖只用 `npm ci`，不使用 `npm install` 更新锁文件。
- Tauri CLI 使用 `nexus-ui/package.json` 的本地版本，不调用全局 `npx tauri`。
- Rust 依赖使用 `Cargo.lock` 和 `--locked`。
- MSVC 环境由 `vswhere.exe` 定位，再通过 `VsDevCmd.bat` 完整加载；不硬编码 `LIB/INCLUDE/PATH`。

## 4. 首次安装

先独立安装 Python、Node.js、Rustup、Git 和 Visual Studio Build Tools，然后关闭旧终端，打开新的 x64 PowerShell。

验证 Rust 工具链：

```powershell
rustup default stable-x86_64-pc-windows-msvc
rustup show active-toolchain
rustc -vV
```

`rustc -vV` 的 `host` 必须是：

```text
x86_64-pc-windows-msvc
```

初始化仓库专用依赖：

```powershell
cd C:\AiTools\Nexus
powershell -ExecutionPolicy Bypass -File scripts\windows\setup-build-env.ps1 -Reset
```

如果 Python 未注册到 `py.exe` 或 `PATH`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\setup-build-env.ps1 `
  -PythonExe C:\BuildTools\Python312\python.exe `
  -Reset
```

`-Reset` 只删除经过路径校验、位于仓库内的托管依赖目录，不会删除源码或 `data/`。

## 5. 构建

正式干净的便携 EXE 构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build-release.ps1 -CleanOutputs
```

生成 MSI 与 NSIS 安装包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build-release.ps1 `
  -CleanOutputs -PackageMode installers
```

安装器构建会从 `%USERPROFILE%\.tauri\nexus.key` 读取自动更新私钥，并验证
同目录的 `nexus.key.pub` 与 `tauri.conf.json` 中的公钥一致。私钥只注入当前构建
进程，不会复制到仓库或发布目录。成功构建必须同时生成：

- MSI 安装包
- NSIS setup EXE
- NSIS setup EXE（Tauri v2 直接复用安装器作为更新包）
- `*-setup.exe.sig` Ed25519 自动更新签名
- `*.msi.sig` MSI 签名
- 使用该签名生成的 `latest.json`

缺少签名密钥、密钥不匹配或任一更新文件缺失时，构建会直接失败。

首次安装器构建需要访问 GitHub，以下载并校验 WiX Toolset 3.14.1 与 NSIS 3.11；Tauri 会将它们缓存到 `%LOCALAPPDATA%\tauri\WixTools314` 和 `%LOCALAPPDATA%\tauri\NSIS`，后续相同版本构建可复用缓存。`-PackageMode portable` 是默认值，不依赖 WiX/NSIS。

日常增量构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\build-release.ps1
```

脚本执行顺序：

```text
project_check.py
  → build_server.py / PyInstaller
  → sidecar 复制到 src-tauri/binaries
  → npm run tauri:build:portable（默认）或 npm run tauri:build（installers 模式）
      → tsc --noEmit
      → vite build
      → cargo build --release --locked
      → sidecar + 前端资源嵌入 Tauri
  → release/AI-Nexus-Assistant.exe（installers 模式额外复制 MSI 与 setup.exe）
```

## 6. 分步验证

仅检查元数据和锁文件：

```powershell
.build-env\python\Scripts\python.exe tools\project_check.py
```

检查完整 Windows 工具链：

```powershell
.build-env\python\Scripts\python.exe tools\project_check.py --environment --strict-environment
```

前端类型检查：

```powershell
cd nexus-ui
npm.cmd run typecheck
```

Python 测试：

```powershell
.build-env\python\Scripts\python.exe -m pytest -q
```

测试使用 `NEXUS_DB_PATH=:memory:` 时会进入共享的 SQLite 内存数据库，不会访问 `data/nexus.db`。

## 7. 依赖更新规则

依赖更新必须作为独立变更处理：

1. 修改 `pyproject.toml`、`package.json` 或 `Cargo.toml`。
2. 更新相应锁文件。
3. 删除旧的托管依赖并重新安装。
4. 检查 `.build-env/environment.json` 和 `python-packages.txt`。
5. 运行类型检查、pytest 和一次 `-CleanOutputs` 完整构建。

Node 和 Rust 已提交传递依赖锁文件。Python 当前在 `pyproject.toml` 中约束直接依赖，实际完整解析结果记录在每台构建机的 `.build-env/python-packages.txt`；正式发版应保存该文件到发布工件，以便复现和审计。

## 8. 常见失败

### `link.exe not found`

VS Build Tools 缺少 C++ 工作负载，或 `vswhere.exe` 无法找到它。不要手动拼 `LIB`；修复 Visual Studio Installer 后重新打开终端。

### PowerShell 禁止执行 `npx.ps1`

规范流程不使用 `npx.ps1`，而是直接调用 `npm.cmd` 和本地 package script。

### sidecar 提示构建环境不受管理

先运行 `setup-build-env.ps1`。`NEXUS_ALLOW_UNMANAGED_BUILD=1` 仅供临时排查，不允许用于正式发布。

### npm 或 Cargo 下载到错误磁盘

确认当前终端没有预设冲突的 `NPM_CONFIG_CACHE`、`CARGO_TARGET_DIR`。规范脚本会覆盖为 `.build-env` 下的路径，并记录到 `environment.json`。

### 联网搜索在目标 PC 不可用

当前 open-webSearch 依赖目标机上的 Node.js。若要实现真正无外部依赖的单文件发布，需要后续将固定版本的 Node runtime 一并打包，或将搜索服务改写为 Rust/Python 内置实现。
