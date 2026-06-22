# PRD v4.0 — 多端适配 & 自动更新

> **版本**: v4.0.0 规划
> **日期**: 2026-06-21
> **状态**: 调研完成，待评审
> **基于**: AI Nexus Assistant v3.5.0 (Tauri 2 + React + FastAPI)

---

## 一、背景与目标

### 1.1 当前痛点

| 问题 | 描述 |
|------|------|
| **平台单一** | 仅 Windows 桌面端，无法满足移动场景（平板/手机查阅文献、管理待办） |
| **更新困难** | 便携版 exe 需手动下载替换，用户常停留在旧版本，错过 Bug 修复和新功能 |
| **分发局限** | 无安装包自动升级机制，NSIS/MSI 安装包也需用户手动运行 |

### 1.2 目标

| 目标 | 具体指标 |
|------|---------|
| 多端覆盖 | 在 Windows 基础上，新增 Android APK / AAB 和 iOS IPA 支持 |
| 自动更新 | Tauri 桌面端启动时静默检查 GitHub Release，一键完成更新 |
| 代码复用 | 前端 React/TypeScript 代码 80%+ 跨端共享 |
| 架构兼容 | 不破坏现有 Windows 桌面端功能和 PySide6 版本 |

---

## 二、调研结论总览

### 2.1 Tauri 2 移动端支持状态

| 维度 | 结论 |
|------|------|
| 官方状态 | Tauri 2.0 于 2024 年 10 月 2 日正式发布，**Android/iOS 为正式稳定特性** |
| Android 最低版本 | API 24 (Android 7.0 Nougat) |
| iOS 最低版本 | iOS 13.0 |
| WebView 引擎 | Android: Chromium WebView; iOS: WKWebView (WebKit) |
| APK 体积 | 基础约 5-10MB（远小于 Electron 50-100MB） |

**验证状态**: ✅ 已通过多源交叉验证

### 2.2 自动更新方案对比

| 方案 | 适用框架 | 更新体积 | 签名验证 | 增量更新 | 复杂度 |
|------|---------|---------|---------|---------|--------|
| **tauri-plugin-updater** ⭐ | Tauri 2 | ~5MB | Ed25519 | 否 | 低 |
| Velopack | 任意 (.NET 优先) | 中等 | 代码签名 | 是 | 中 |
| WinSparkle | C/C++ Windows | 全量 | 可选 | 否 | 中 |
| 纯自定义 DIY | 任意 | 全量 | 手动 SHA | 否 | 中高 |

**推荐**: Tauri 版本使用 `tauri-plugin-updater`（官方原生，Ed25519 签名，配置简单）

### 2.3 关键架构约束

> ⚠️ **最大阻塞点**: 当前项目依赖 Python FastAPI 后端 (`server.py`) 作为 sidecar。
> 在移动端**无法嵌入 Python 进程**。需要决策后端部署策略。

**六种后端方案对比**:

| # | 方案 | 可行性 | 工时 | 需要服务器？ | iOS 支持 | 安全风险 |
|---|------|--------|------|-------------|---------|---------|
| A | 远程 API (FastAPI 部署) | ✅ 高 | 2-3 周 | ✅ 是 | ✅ | 🔴 高（需加固） |
| B | Rust 原生重写 | ✅ 高 | 4-8 周 | ❌ 否 | ✅ | 🟢 低 |
| C | 混合方案（本地缓存+远程） | ✅ 高 | 3-5 周 | ✅ 是 | ✅ | 🟡 中 |
| D | WASM/Pyodide | ❌ 低 | 2-4 周 | ❌ 否 | ❌ 不可行 | 🟡 中 |
| E | Chaquopy 嵌入 Python | ❌ 低 | 4-8 周 | ❌ 否 | ❌ 不可行 | 🔴 高 |
| F | Edge Serverless | ✅ 高 | 2-4 周 | 托管式 | ✅ | 🟡 中 |

**排除方案**:
- **D. WASM/Pyodide** — iOS WKWebView 禁用 JIT 编译，WASM 性能下降 10-30 倍，生产不可用
- **E. Chaquopy** — Apple App Store 禁止嵌入可执行任意代码的解释器，iOS 审核必定被拒

**详细分析见**: 第九章《后端方案深度分析》

---

## 三、技术方案详述

### 3.1 多端适配方案

#### 3.1.1 环境准备

**Android 构建环境**:

| 工具 | 版本 | 用途 |
|------|------|------|
| Android Studio | 最新稳定版 | IDE + SDK Manager |
| Android SDK | API 34+ | 核心平台 |
| Android NDK | 26.x / 27.x | 原生代码编译 |
| JDK | 17 (严格要求) | Gradle 构建系统 |
| Rust targets | `aarch64-linux-android`, `armv7-linux-androideabi`, `i686-linux-android`, `x86_64-linux-android` | 交叉编译 |

**iOS 构建环境** (需 macOS):

| 工具 | 版本 | 用途 |
|------|------|------|
| Xcode | 15+ | IDE + 构建工具 |
| CocoaPods | 最新 | iOS 依赖管理 |
| Rust targets | `aarch64-apple-ios`, `x86_64-apple-ios` | 交叉编译 |

#### 3.1.2 项目改造点

**已具备的条件** (无需改动):
- ✅ `Cargo.toml` 已配置 `crate-type = ["lib", "cdylib", "staticlib"]` — `staticlib` 是 Android NDK 链接必需
- ✅ `tauri.conf.json` 已设置 `identifier: "com.nexus.assistant"` — 移动端需要反向域名标识
- ✅ `lib.rs` 已有 `#[cfg_attr(mobile, tauri::mobile_entry_point)]` — 移动端入口点已就绪

**需要新增/修改的文件**:

```
nexus-ui/src-tauri/
├── Cargo.toml              # 添加移动端插件依赖
├── tauri.conf.json          # 添加移动端窗口配置
├── capabilities/
│   ├── default.json         # 现有桌面端权限
│   └── mobile.json          # 新增：移动端权限集
├── src/
│   └── lib.rs               # 添加平台条件编译，移动端禁用桌面特性
└── gen/                     # 自动生成（gitignore）
    ├── android/             # cargo tauri android init 生成
    └── ios/                 # cargo tauri ios init 生成
```

**前端改造**:

```
nexus-ui/src/
├── hooks/
│   └── usePlatform.ts       # 新增：平台检测 hook
├── layouts/
│   ├── DesktopLayout.tsx    # 现有侧边栏布局
│   └── MobileLayout.tsx     # 新增：底部标签栏布局
├── components/
│   ├── mobile/              # 新增：移动端专用组件
│   │   ├── BottomNav.tsx    # 底部导航
│   │   └── SafeAreaView.tsx # 安全区域适配
│   └── shared/              # 可跨端共享的组件
└── api/
    └── client.ts            # 修改：API 地址根据平台切换（localhost vs 远程）
```

#### 3.1.3 移动端不可用功能

| 功能 | 桌面端 | 移动端 | 替代方案 |
|------|--------|--------|---------|
| 系统托盘 | ✅ | ❌ | 通知栏常驻通知 |
| 多窗口（时钟/日历/游戏） | ✅ | ❌ | 应用内路由切换 |
| 菜单栏 | ✅ | ❌ | 底部导航 + 更多菜单 |
| 全局快捷键 | ✅ | ❌ | 不适用 |
| Shell 命令执行 | ✅ | ❌ | 移除或替换为 Tauri 插件 |
| 文件对话框 | 完整 | 受限 | `@tauri-apps/plugin-dialog` |
| Python sidecar | ✅ | ❌ | 远程 API 或 Rust 重写 |

#### 3.1.4 前端代码复用策略

```
共享层（~80%）                    平台特定层（~20%）
├── API 客户端 (client.ts)       ├── 桌面：侧边栏导航 (Sidebar.tsx)
├── 状态管理 (hooks)             ├── 移动：底部标签栏 (BottomNav.tsx)
├── 页面组件 (pages/*.tsx)       ├── 桌面：多窗口管理
├── UI 组件 (cards, forms)       ├── 移动：手势交互、安全区域
├── 类型定义 (types)             ├── 桌面：系统托盘
└── 工具函数 (utils)             └── 移动：返回按钮处理
```

**平台检测方式**:

```typescript
// hooks/usePlatform.ts
import { platform } from '@tauri-apps/plugin-os';

export function usePlatform() {
  const os = platform();
  return {
    isMobile: os === 'android' || os === 'ios',
    isDesktop: os === 'windows' || os === 'macos' || os === 'linux',
    os,
  };
}
```

#### 3.1.5 CI/CD 多端构建

```yaml
# GitHub Actions 多端构建矩阵
jobs:
  build-windows:    # windows-latest, tauri-action
  build-android:    # ubuntu-latest, JDK 17 + Android SDK + NDK
  build-ios:        # macos-latest, Xcode 15+
```

Android 构建关键步骤:
1. `actions/setup-java@v4` (JDK 17)
2. `android-actions/setup-android@v3` (SDK + NDK)
3. `rustup target add aarch64-linux-android ...`
4. `cargo tauri android build`

iOS 构建关键步骤:
1. `runs-on: macos-latest` (必须 macOS)
2. `rustup target add aarch64-apple-ios`
3. `cargo tauri ios build`

### 3.2 自动更新方案

#### 3.2.1 Tauri 桌面端：tauri-plugin-updater

**更新流程**:

```
应用启动
  ↓
检查 latest.json 端点
  ↓
比较版本号 (semver)
  ↓
┌─ 无更新 → 正常启动
└─ 有更新 → 显示更新对话框（版本号 + 更新日志）
               ↓
           用户确认下载
               ↓
           下载 .nsis.zip + 验证 Ed25519 签名
               ↓
           安装并重启
```

**需要修改的文件** (4 个):

| 文件 | 修改内容 |
|------|---------|
| `Cargo.toml` | 添加 `tauri-plugin-updater = "2"` 依赖 |
| `tauri.conf.json` | 添加 `plugins.updater` 配置 (pubkey + endpoint) |
| `capabilities/default.json` | 添加 `"updater:default"` 权限 |
| `src/lib.rs` | 注册 `tauri_plugin_updater::Builder::new().build()` 插件 |

**签名密钥管理**:

```bash
# 一次性生成密钥对
npx tauri signer generate -w ~/.tauri/nexus.key

# 构建时设置环境变量
export TAURI_SIGNING_PRIVATE_KEY="<私钥内容>"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""
```

**发布清单** (每个版本):

```
GitHub Release v3.6.0
├── AI-Nexus-Assistant_3.6.0_x64-setup.nsis.zip      # NSIS 更新包
├── AI-Nexus-Assistant_3.6.0_x64-setup.nsis.zip.sig  # Ed25519 签名
├── AI-Nexus-Assistant_3.6.0_x64-setup.exe           # 完整安装包
├── AI-Nexus-Assistant.exe                            # 便携版
├── nexus_ui_lib.dll                                  # WebView2 loader
└── latest.json                                       # 更新清单
```

**latest.json 格式**:

```json
{
  "version": "3.6.0",
  "notes": "v3.6.0 更新说明...",
  "pub_date": "2026-07-01T12:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "<.sig 文件内容>",
      "url": "https://github.com/chenjingwei/AI-Nexus-Assistant/releases/download/v3.6.0/AI-Nexus-Assistant_3.6.0_x64-setup.nsis.zip"
    }
  }
}
```

**前端更新 UI** (在 Settings 页面):

```typescript
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

async function checkUpdate() {
  const update = await check();
  if (update) {
    // 显示更新对话框: update.version, update.body
    setUpdateInfo({ version: update.version, notes: update.body });
    setShowUpdateDialog(true);
  }
}

async function doUpdate() {
  await update!.downloadAndInstall();
  await relaunch();
}
```

#### 3.2.2 移动端更新策略

移动端**不使用** `tauri-plugin-updater`（该插件仅支持桌面端）。移动端更新通过应用商店原生机制:

| 平台 | 更新方式 | 说明 |
|------|---------|------|
| Android | Google Play 自动更新 | 上传 AAB 到 Play Console |
| Android (侧载) | 应用内提示 + 跳转下载页 | 检查版本号，提示用户下载新 APK |
| iOS | App Store 自动更新 | 上传 IPA 到 App Store Connect |

对于不通过应用商店分发的 Android 侧载场景，可在应用内实现版本检查:

```typescript
// 移动端版本检查（不使用 updater 插件）
async function checkMobileUpdate() {
  const resp = await fetch('https://api.github.com/repos/chenjingwei/AI-Nexus-Assistant/releases/latest');
  const data = await resp.json();
  const latestVer = data.tag_name.replace('v', '');
  if (compareVersions(latestVer, CURRENT_VERSION) > 0) {
    // 提示用户下载新版本
    const apkAsset = data.assets.find((a: any) => a.name.endsWith('.apk'));
    if (apkAsset) showUpdatePrompt(apkAsset.browser_download_url, data.body);
  }
}
```

#### 3.2.3 GitHub Release API 速查

| 项目 | 值 |
|------|-----|
| 端点 | `GET /repos/{owner}/{repo}/releases/latest` |
| 无认证限额 | 60 次/小时/IP |
| 条件请求 | `If-None-Match: "<etag>"` → 304 不计入限额 |
| 响应关键字段 | `tag_name`, `body`, `assets[].browser_download_url`, `assets[].size` |

---

## 四、开源参考项目

### 4.1 跨端 Tauri 应用

| 项目 | Stars | 平台 | 技术栈 | 参考价值 |
|------|-------|------|--------|---------|
| [HuLa](https://github.com/HuLaSpark/HuLa) | 7,400+ | Win/Mac/Linux/Android/iOS | Rust + Vue3 | 最大 5 端 Tauri 应用，IM 场景 |
| [PakePlus](https://github.com/Sjj1024/PakePlus-Android) | 8,500+ | 全平台 | Tauri 2 | 网页打包工具，<5MB 体积 |
| [QuickClipboard](https://github.com/mosheng1/QuickClipboard) | 1,700+ | Win + Android | Tauri 2 + React | **最接近本项目架构** |
| [Voltius](https://github.com/VoltiusApp/voltius) | 377 | Win/Linux/Mac/Android | Rust/Tauri | SSH 客户端，桌面+移动 |

### 4.2 自动更新参考

| 项目 | 方案 | 适用性 |
|------|------|--------|
| Tauri 官方 updater 插件 | Ed25519 签名 + JSON 清单 | ⭐ 直接采用 |
| [Velopack](https://github.com/velopack/velopack) | 跨平台安装+更新框架 | .NET 生态参考 |
| [AutoUpdater.NET](https://github.com/ravibpatel/AutoUpdater.NET) | XML 清单 + 简单下载 | 简单方案参考 |

---

## 五、v4.0.0 开发计划

### 5.1 版本规划总览

```
v4.0.0  — 多端适配 + 自动更新 + 安全加固（大版本）
  ├── Step 1: 自动更新 (桌面端)           预计 1-2 天
  ├── Step 2: 安全加固 (API 认证层)        预计 3-5 天
  ├── Step 3: Android 适配               预计 1-2 周
  ├── Step 4: Android 真机测试 + 修复      预计 3-5 天
  └── Step 5: 发布 + CI/CD               预计 2-3 天
                                     总计: 约 3-4 周

后续版本:
  v4.1.0 — iOS 适配（需 macOS 环境）
  v4.2.0 — 本地缓存层（离线支持）
  v5.0.0 — Rust 原生后端（淘汰 Python sidecar）
```

### 5.2 Step 1: 自动更新（桌面端）

**预计工时**: 1-2 天
**前置条件**: 无
**影响范围**: 仅桌面端，不影响现有功能

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | 生成签名密钥对 | `~/.tauri/nexus.key` | `npx tauri signer generate`，公钥记入配置 |
| 1.2 | 添加 updater 依赖 | `nexus-ui/src-tauri/Cargo.toml` | `tauri-plugin-updater = "2"` |
| 1.3 | 注册 updater 插件 | `nexus-ui/src-tauri/src/lib.rs` | `.plugin(tauri_plugin_updater::Builder::new().build())` |
| 1.4 | 配置 updater 端点 | `nexus-ui/src-tauri/tauri.conf.json` | `plugins.updater.pubkey` + `endpoints` |
| 1.5 | 添加权限 | `nexus-ui/src-tauri/capabilities/default.json` | 添加 `"updater:default"` |
| 1.6 | 前端更新 UI | `nexus-ui/src/pages/SettingsPage.tsx` | "检查更新" 按钮 + 更新对话框（版本号 + 更新日志 + 进度条） |
| 1.7 | 构建脚本适配 | `build_tauri.py` | 构建后自动生成 `latest.json`，读取 `.sig` 文件内容 |
| 1.8 | 发布脚本 | `scripts/release.sh` (新增) | 封装 `gh release create` 流程，自动上传 nsis.zip + .sig + latest.json |

**验收标准**:
- [ ] 应用启动时静默检查更新（<1s 延迟，不阻塞主界面）
- [ ] 发现新版本时显示更新对话框（含版本号、更新日志）
- [ ] 点击更新后自动下载、验证 Ed25519 签名、安装并重启
- [ ] 无网络时优雅降级（静默跳过，不弹错误）
- [ ] 便携版 exe 和 NSIS 安装包均支持更新

### 5.3 Step 2: 安全加固（API 认证层）

**预计工时**: 3-5 天
**前置条件**: 无（可与 Step 1 并行）
**影响范围**: 桌面端 + 移动端共用

> ⚠️ 当前 `server.py` 无任何认证，任何人访问 :8765 即可操作全部数据。
> 远程部署前**必须**完成此步骤。

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 2.1 | JWT 认证中间件 | `app/auth.py` (新增) | FastAPI dependency，验证 Bearer token |
| 2.2 | 登录/注册接口 | `server.py` | `POST /api/auth/login` 返回 access_token + refresh_token |
| 2.3 | Token 刷新机制 | `server.py` | `POST /api/auth/refresh`，access_token 15min 过期 |
| 2.4 | 密码哈希存储 | `app/models/user.py` (新增) | User 表，bcrypt 哈希，不存明文 |
| 2.5 | 速率限制 | `server.py` | `slowapi` 中间件，每 IP 60 次/分钟 |
| 2.6 | HTTPS 部署文档 | `docs/DEPLOY.md` (新增) | Nginx 反代 + Let's Encrypt 配置指南 |
| 2.7 | 前端登录页 | `nexus-ui/src/pages/LoginPage.tsx` (新增) | 移动端登录界面 |
| 2.8 | Token 存储 | `nexus-ui/src/api/client.ts` | 桌面端: localStorage; 移动端: `tauri-plugin-stronghold` |
| 2.9 | API 拦截器 | `nexus-ui/src/api/client.ts` | 401 时自动刷新 token，刷新失败跳转登录 |

**安全架构层次**:

```
┌──────────────────────────────────────────────────┐
│  第 1 层: 传输安全                                │
│  ├── TLS 1.2+ (Nginx + Let's Encrypt)            │
│  ├── HSTS (防 SSL 降级)                           │
│  └── 移动端: Certificate Pinning (Android/iOS)    │
├──────────────────────────────────────────────────┤
│  第 2 层: 身份认证                                │
│  ├── JWT (Access Token 15min + Refresh Token 7d) │
│  ├── Token 存 OS 安全存储 (移动端)                 │
│  └── 设备指纹绑定 (防 Token 窃取重用)              │
├──────────────────────────────────────────────────┤
│  第 3 层: 数据保护                                │
│  ├── API 密钥仅存服务端 (移动端不存第三方 key)     │
│  ├── SQLite 加密 (sqlcipher, 可选)                │
│  └── 日志脱敏 (Release 构建不输出敏感信息)         │
└──────────────────────────────────────────────────┘
```

**验收标准**:
- [ ] 未认证请求返回 401，不泄露任何数据
- [ ] access_token 15 分钟过期，refresh_token 7 天过期
- [ ] 速率限制生效（超限返回 429）
- [ ] 登录失败不泄露"用户不存在"vs"密码错误"信息（统一返回 401）
- [ ] 前端 token 存储在安全位置（移动端不在 localStorage）

### 5.4 Step 3: Android 适配

**预计工时**: 1-2 周
**前置条件**: Step 2 完成（需要认证层）

| # | 任务 | 文件/命令 | 说明 |
|---|------|----------|------|
| 3.1 | Android 环境搭建 | 系统级 | Android Studio + SDK (API 34+) + NDK 27.x + JDK 17 |
| 3.2 | Rust targets | `rustup target add` | `aarch64-linux-android`, `armv7-linux-androideabi`, `i686-linux-android`, `x86_64-linux-android` |
| 3.3 | 初始化 Android | `cargo tauri android init` | 生成 `src-tauri/gen/android/` Gradle 项目 |
| 3.4 | API 地址适配 | `nexus-ui/src/api/client.ts` | 桌面端 `http://localhost:8765`，移动端 `https://api.nexus.local` (可配置) |
| 3.5 | 平台检测 hook | `nexus-ui/src/hooks/usePlatform.ts` (新增) | `isMobile` / `isDesktop` / `os` |
| 3.6 | 移动端布局 | `nexus-ui/src/layouts/MobileLayout.tsx` (新增) | 底部标签栏导航 (5 tab) |
| 3.7 | 移动端导航 | `nexus-ui/src/components/mobile/BottomNav.tsx` (新增) | 任务 / 文献 / 知识库 / AI / 设置 |
| 3.8 | 安全区域适配 | `nexus-ui/src/styles/mobile.css` (新增) | `env(safe-area-inset-*)`、`100dvh` |
| 3.9 | 响应式改造 | `nexus-ui/src/pages/*.tsx` | 各页面移动端布局适配 |
| 3.10 | 功能裁剪 | `nexus-ui/src/lib.rs` | `#[cfg(not(target_os = "android"))]` 条件编译桌面特性 |
| 3.11 | 触摸优化 | 各页面组件 | 避免 hover 依赖、增大点击区域、底部弹窗替代 modal |
| 3.12 | 移动端权限 | `nexus-ui/src-tauri/capabilities/mobile.json` (新增) | 移动端专用权限集 |

**前端代码复用策略**:

```
nexus-ui/src/
├── hooks/
│   ├── usePlatform.ts       # 新增: 平台检测
│   └── useAuth.ts           # 新增: 认证状态管理
├── layouts/
│   ├── DesktopLayout.tsx    # 现有: 侧边栏布局
│   └── MobileLayout.tsx     # 新增: 底部标签栏
├── components/
│   ├── mobile/              # 新增: 移动端组件
│   │   ├── BottomNav.tsx    #   底部导航
│   │   └── SafeAreaView.tsx #   安全区域
│   └── shared/              # 现有: 跨端共享
├── pages/
│   ├── LoginPage.tsx        # 新增: 登录页
│   └── *.tsx                # 修改: 响应式适配
└── api/
    └── client.ts            # 修改: 平台切换 + JWT 拦截器
```

**验收标准**:
- [ ] `cargo tauri android dev` 在模拟器/真机正常运行
- [ ] 核心功能可用：任务管理、文献搜索、知识库、AI 对话
- [ ] 登录/认证流程完整
- [ ] 底部导航 5 个 tab 正常切换
- [ ] 无桌面端功能残留（无空白区域、无无效按钮、无报错）
- [ ] 触摸交互流畅（无 hover 卡死、无点击区域过小）

### 5.5 Step 4: Android 真机测试 + 修复

**预计工时**: 3-5 天
**前置条件**: Step 3 完成

| # | 任务 | 说明 |
|---|------|------|
| 4.1 | 多设备测试 | 至少 3 款不同 Android 版本/厂商的设备 |
| 4.2 | WebView 兼容性 | Android 7 (WebView 60+) 到 Android 14 (WebView 120+) |
| 4.3 | 内存/性能 profiling | 低内存设备测试，避免 OOM |
| 4.4 | 网络切换测试 | WiFi ↔ 移动数据，断网重连，弱网环境 |
| 4.5 | Bug 修复 | 根据测试结果修复适配问题 |

### 5.6 Step 5: 发布 + CI/CD

**预计工时**: 2-3 天
**前置条件**: Step 4 完成

| # | 任务 | 说明 |
|---|------|------|
| 5.1 | GitHub Actions Android 构建 | ubuntu-latest + JDK 17 + Android SDK + NDK |
| 5.2 | Android 签名配置 | Keystore 生成，CI 中配置签名环境变量 |
| 5.3 | APK/AAB 生成 | Release 构建输出签名 APK + AAB |
| 5.4 | GitHub Release 发布 | v4.0.0-rc1 → 测试 → v4.0.0 正式发布 |
| 5.5 | 版本号同步 | 前端 `package.json` + Rust `Cargo.toml` + Python `__init__.py` 统一 |
| 5.6 | 更新日志 | `CHANGELOG.md` 补充 v4.0.0 变更记录 |

**v4.0.0 发布清单**:

```
GitHub Release v4.0.0
├── Windows
│   ├── AI-Nexus-Assistant_4.0.0_x64-setup.nsis.zip      # 更新包
│   ├── AI-Nexus-Assistant_4.0.0_x64-setup.nsis.zip.sig  # 签名
│   ├── AI-Nexus-Assistant_4.0.0_x64-setup.exe           # 安装包
│   ├── AI-Nexus-Assistant.exe                            # 便携版
│   └── nexus_ui_lib.dll
├── Android
│   ├── nexus-ui-universal.apk                            # 通用 APK (侧载)
│   └── nexus-ui.aab                                      # Play Store 格式
├── latest.json                                            # 桌面端更新清单
└── checksums.txt                                          # SHA-256 校验
```

---

## 六、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Python sidecar 无法在移动端运行 | 阻塞移动端 | 确定 | v4.0.0 使用远程 API；v5.0.0 渐进 Rust 重写 |
| 远程 API 被攻击 | 数据泄露 | 高 | Step 2 安全加固：JWT + HTTPS + 速率限制 |
| API 密钥泄露 (APK 反编译) | 第三方冒用额度 | 高 | 密钥仅存服务端，移动端通过 JWT 代理调用 |
| 中间人攻击 (MITM) | 数据窃听/篡改 | 中 | TLS 强制 + Certificate Pinning |
| iOS 构建需要 macOS | 增加开发成本 | 确定 | v4.1.0 再处理 iOS；使用 GitHub Actions macOS runner |
| WKWebView 性能限制 (无 JIT) | iOS 体验下降 | 中 | 减少复杂 JS 运算，优化首屏加载 |
| 移动端 WebView 版本碎片化 | 兼容性问题 | 低 | 设置最低 API level 24 (Android 7.0+) |
| tauri-plugin-updater 仅支持桌面 | 移动端需额外方案 | 确定 | 移动端走应用商店更新机制或应用内版本检查 |
| App Store 审核拒绝 (WebView 壳) | iOS 发布受阻 | 低 | 确保提供原生功能价值（通知、文件系统、离线存储） |

---

## 七、架构决策记录 (ADR)

### ADR-1: 移动端后端策略

**决策**: 分阶段演进 — **短期远程 API → 长期 Rust 原生**

| 阶段 | 方案 | 版本 | 说明 |
|------|------|------|------|
| 短期 | 远程 API (方案 A) | v4.0.0 | FastAPI 部署为远程服务，移动端通过 HTTPS + JWT 连接 |
| 中期 | 本地缓存 + 远程 (方案 C) | v4.2.0 | 本地 SQLite 缓存，离线可读，AI/搜索走远程 |
| 长期 | Rust 原生 (方案 B) | v5.0.0 | 核心逻辑用 Rust 重写，淘汰 Python sidecar |

**理由**:
1. 短期远程 API 改动最小，可快速上线 Android 端
2. 移动端核心功能（AI 对话、文献搜索）本身依赖网络，远程 API 不增加额外网络依赖
3. 长期 Rust 原生可彻底消除服务器依赖，体积极小，安全性最高
4. 分阶段演进避免一次性大重写的风险

**排除方案**:
- WASM/Pyodide — iOS 禁用 JIT，性能不可接受
- Chaquopy — App Store 审核政策不允许嵌入式解释器

### ADR-2: 自动更新方案选择

**决策**: Tauri 桌面端使用 `tauri-plugin-updater`，移动端走应用商店

**理由**:
1. 官方原生方案，与 Tauri 2 深度集成
2. Ed25519 签名验证保障安全性
3. 移动端应用商店更新是平台规范，自定义更新可能违反商店政策
4. 配置简单，仅需 4 个文件修改

### ADR-3: 移动端优先级

**决策**: 先 Android，后 iOS

**理由**:
1. Android 可在 Windows 环境开发（Android Studio + 模拟器）
2. iOS 必须 macOS 环境，增加开发成本
3. Android 用户基数更大（特别是中国市场的研究者）
4. Android 侧载分发更灵活（不强制应用商店）

### ADR-4: 安全认证方案

**决策**: JWT (Access Token + Refresh Token) + HTTPS + 服务端代理

**理由**:
1. JWT 是移动端 API 认证的事实标准（RFC 7519）
2. 短期 access_token (15min) 限制泄露窗口
3. API 密钥仅存服务端，移动端通过 JWT 代理调用第三方 API，密钥不暴露在客户端
4. HTTPS (TLS 1.2+) 保障传输安全，移动端额外做 Certificate Pinning

**存储策略**:
| 平台 | Token 存储 | API 密钥 |
|------|-----------|---------|
| 桌面端 | localStorage | 本地 ModelConfig 表 |
| Android | Android Keystore (EncryptedSharedPreferences) | 不存储，服务端代理 |
| iOS | iOS Keychain Services | 不存储，服务端代理 |

---

## 八、参考资料

| 资源 | URL |
|------|-----|
| Tauri v2 官方文档 | https://v2.tauri.app |
| Tauri 移动端指南 | https://v2.tauri.app/mobile/ |
| Tauri Updater 插件 | https://v2.tauri.app/plugin/updater/ |
| Tauri 签名文档 | https://tauri.app/distribute/signing/ |
| Tauri 分发指南 | https://tauri.app/distribute/updating/ |
| GitHub Release API | https://docs.github.com/en/rest/releases |
| Tauri 官方插件仓库 | https://github.com/tauri-apps/plugins-workspace |
| HuLa (5 端参考) | https://github.com/HuLaSpark/HuLa |
| QuickClipboard (React 参考) | https://github.com/mosheng1/QuickClipboard |
| PakePlus (体积参考) | https://github.com/Sjj1024/PakePlus-Android |
| OWASP Mobile Top 10 | https://owasp.org/www-project-mobile-top-10/ |
| OWASP API Security Top 10 | https://owasp.org/API-Security/ |
| RFC 8252 OAuth 2.0 Native Apps | https://tools.ietf.org/html/rfc8252 |

---

## 九、后端方案深度分析

> 本章对六种后端方案进行技术细节分析，为 ADR-1 提供决策依据。

### 9.1 方案 A: 远程 API (v4.0.0 采用)

**架构**:
```
移动端 ──HTTPS+JWT──→ Nginx ──→ FastAPI (server.py) ──→ SQLite / AI APIs
```

**实现要点**:
- `server.py` 部署到云服务器（推荐 2C4G 轻量云，~30 元/月）
- Nginx 反代配置 SSL 证书（Let's Encrypt 免费）
- FastAPI 添加 JWT 认证中间件
- 前端 `client.ts` 按平台切换 API base URL

**优点**: 改动最小，复用全部现有 Python 代码
**缺点**: 需要服务器运维，数据经过网络，需要安全加固
**适用**: v4.0.0 短期方案

### 9.2 方案 B: Rust 原生重写 (v5.0.0 目标)

**组件映射**:

| Python 模块 | Rust 替代 | Crate | 工时 |
|-------------|----------|-------|------|
| SQLAlchemy + SQLite (8 表) | rusqlite | `rusqlite = { features = ["bundled", "serde_json"] }` | 1 周 |
| CRUD 服务 (task/knowledge/experiment/chat) | `#[tauri::command]` | 内置 | 1.5 周 |
| AI Router (OpenAI + Anthropic 流式) | async-openai + reqwest | `async-openai`, `eventsource-stream` | 1 周 |
| 文献搜索 (8 源) | reqwest + scraper | `scraper`, `reqwest` | 1 周 |
| 备份/恢复 | fs::copy + zip | `zip`, `walkdir` | 3 天 |
| Dashboard 统计 | rusqlite 聚合查询 | 同上 | 3 天 |

**优点**:
- 无服务器依赖，无网络攻击面
- 单二进制 ~5-10MB (vs 当前 51MB)
- 原生性能，Rust 内存安全
- Tauri v2 移动端原生支持

**缺点**:
- 4-8 周重写工作量
- 需要 Rust 开发能力
- AI 工具调用协议需重新实现

**适用**: v5.0.0 长期方案

### 9.3 方案 C: 混合本地+远程 (v4.2.0 计划)

**架构**:
```
┌─────────────────────┐         ┌──────────────┐
│ 移动端               │         │ 远程 API      │
│ ┌─────────────────┐ │  同步    │              │
│ │ SQLite (本地缓存) │←┼────────→│ server.py    │
│ │ - 任务/知识库/实验 │ │         │ - AI 对话    │
│ │ - 离线可读        │ │         │ - 文献搜索   │
│ └─────────────────┘ │         │ - 数据同步   │
└─────────────────────┘         └──────────────┘
```

**同步策略**: Last-Write-Wins (LWW)
- 每条记录带 `updated_at` 时间戳和 `dirty` 标记
- 联网时 push 脏数据，pull 远程变更
- 冲突时时间戳最新的胜出

**优点**: 离线可用 + 渐进式迁移
**缺点**: 同步逻辑有边界情况，需维护双 schema
**适用**: v4.2.0 中期方案

### 9.4 方案 D: WASM/Pyodide — ❌ 不可行

**致命问题**: iOS WKWebView 禁用 JIT 编译，WASM 性能下降 10-30 倍。
Pyodide 加载 CPython 解释器 ~15MB，启动 5-15 秒，内存 50-100MB+。
Apple 可能拒绝加载大型 WASM 模块的应用。

### 9.5 方案 E: Chaquopy/PyObjC — ❌ 不可行

**致命问题**: Apple App Store 审核指南 2.5.2 禁止嵌入可执行非 Apple 批准代码的解释器。
iOS 上嵌入 CPython 几乎必定审核被拒。Android 可行但 iOS 不可行，无法跨端统一。

### 9.6 方案 F: Edge Serverless

**架构**:
```
移动端 ──HTTPS──→ Cloudflare Workers ──→ D1 (SQLite)
                                    ──→ OpenAI API (代理)
                                    ──→ 搜索引擎 (代理)
```

**优点**: 零运维，全球边缘节点，免费额度 (10 万请求/天)，TLS 默认
**缺点**: CPU 时限 (免费 10ms)，厂商锁定，长连接 AI 流式需 Durable Objects
**适用**: 可作为远程 API 的替代部署方案

### 9.7 方案对比总结

| 维度 | 远程 API | Rust 原生 | 混合方案 | WASM | Chaquopy | Serverless |
|------|---------|----------|---------|------|----------|-----------|
| 可行性 | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| 工时 | 2-3 周 | 4-8 周 | 3-5 周 | — | — | 2-4 周 |
| 体积极小 | +1MB | +5MB | +3MB | +15MB | +50MB | +1MB |
| 离线支持 | ❌ | ✅ | 部分 | 部分 | ✅ | 部分 |
| 安全风险 | 高 | 低 | 中 | 中 | 高 | 中 |
| 服务器成本 | ¥30/月 | ¥0 | ¥30/月 | ¥0 | ¥0 | ¥0-5/月 |
| iOS 支持 | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |

---

## 十、安全风险详细分析

> 本章详述移动端连接远程 API 的安全威胁模型和防护措施。

### 10.1 威胁模型

```
┌─────────────┐                    ┌─────────────┐
│   攻击者     │                    │   攻击者     │
│  (网络层)    │                    │  (客户端)    │
│  - MITM      │                    │  - 反编译    │
│  - DNS 劫持   │                    │  - Frida hook│
│  - 重放攻击   │                    │  - Root 提权 │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       ▼                                  ▼
┌──────────────────────────────────────────────┐
│              移动端 Tauri App                 │
│  ┌────────────┐  ┌─────────────────────────┐ │
│  │ WebView    │  │ Rust Backend            │ │
│  │ (React UI) │→ │ - HTTP client (reqwest) │ │
│  │            │  │ - Token 管理            │ │
│  └────────────┘  └─────────────────────────┘ │
└──────────────────┬───────────────────────────┘
                   │ HTTPS
                   ▼
┌──────────────────────────────────────────────┐
│              远程 API 服务                     │
│  ┌──────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Nginx│→ │ FastAPI   │→ │ SQLite         │ │
│  │ TLS  │  │ JWT 验证   │  │ + AI API Keys  │ │
│  └──────┘  └──────────┘  └────────────────┘ │
└──────────────────────────────────────────────┘
```

### 10.2 攻击向量与防护

#### 攻击 1: 中间人攻击 (MITM)

| 维度 | 说明 |
|------|------|
| **场景** | 公共 WiFi（咖啡厅、机场、酒店），攻击者 ARP 欺骗/DNS 劫持 |
| **后果** | 窃取 JWT token、AI 对话内容、研究数据、文献搜索记录 |
| **防护** | TLS 1.2+ 强制；HSTS 头；移动端 Certificate Pinning |

Certificate Pinning 实现 (Android):
```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <domain-config>
        <domain includeSubdomains="true">api.nexus.local</domain>
        <pin-set expiration="2027-06-21">
            <pin digest="SHA-256">base64-of-cert-public-key=</pin>
            <pin digest="SHA-256">backup-pin=</pin>
        </pin-set>
    </domain-config>
</network-security-config>
```

#### 攻击 2: API 密钥泄露

| 维度 | 说明 |
|------|------|
| **场景** | APK 用 `jadx` 反编译，提取硬编码的 OpenAI/Anthropic API key |
| **后果** | 第三方冒用你的 API 额度，产生高额费用 |
| **防护** | 密钥**仅存服务端**，移动端通过 JWT 认证后由服务端代理调用 |

```
# 当前（不安全）:
移动端 → 直接调用 OpenAI API (key 在客户端)

# 改为（安全）:
移动端 → JWT 认证 → 你的 API 服务 → 代理调用 OpenAI (key 在服务端)
```

#### 攻击 3: Token 窃取与重放

| 维度 | 说明 |
|------|------|
| **场景** | 内存 dump、日志泄露、WebView localStorage 被读取 |
| **后果** | 攻击者冒充用户身份操作数据 |
| **防护** | 短期 token (15min)；存储在 OS 安全存储；设备指纹绑定 |

Token 存储安全等级:
```
最安全 → 最不安全:
iOS Keychain > Android Keystore > 加密文件 > localStorage > 明文
                                    ↑ 推荐          ↑ 禁止
```

#### 攻击 4: 证书固定绕过

| 维度 | 说明 |
|------|------|
| **场景** | 攻击者使用 Frida/Xposed 框架 hook SSL 验证函数 |
| **后果** | 绕过 Certificate Pinning，恢复 MITM 能力 |
| **防护** | 多层 pinning（网络配置 + 代码级）；混淆 pinning 逻辑；Root/越狱检测 |

#### 攻击 5: 数据泄露

| 维度 | 说明 |
|------|------|
| **场景** | 日志输出 token、WebView 缓存敏感数据、截屏泄露 |
| **后果** | 研究数据、AI 对话、API 凭证泄露 |
| **防护** | Release 构建日志脱敏；WebView 缓存登出时清理；敏感页面防截屏 |

### 10.3 安全实施清单

**传输层**:
- [ ] TLS 1.2+ 强制，禁用 HTTP 明文
- [ ] HSTS 头 (`max-age=31536000; includeSubDomains`)
- [ ] Android Certificate Pinning (network_security_config.xml)
- [ ] iOS Certificate Pinning (WKNavigationDelegate)

**认证层**:
- [ ] JWT Access Token (15min) + Refresh Token (7d)
- [ ] 登录接口速率限制 (5 次/分钟/IP)
- [ ] Token 存 OS 安全存储 (移动端)，localStorage (桌面端)
- [ ] 401 自动刷新 token，刷新失败跳登录

**密钥管理**:
- [ ] OpenAI/Anthropic API key 仅存服务端环境变量
- [ ] 移动端不存储任何第三方 API key
- [ ] 服务端 key 通过 `.env` 文件管理，不入 git

**数据保护**:
- [ ] Release 构建日志不输出 token/密码/API key
- [ ] WebView localStorage 登出时清理
- [ ] SQLite 敏感字段加密 (可选 sqlcipher)

**代码保护** (Android):
- [ ] ProGuard/R8 混淆 (Tauri 构建默认启用)
- [ ] 不在代码中硬编码任何密钥
- [ ] API base URL 可配置（不硬编码服务器地址）

### 10.4 当前 server.py 安全问题清单

> 以下问题在远程部署前**必须修复**:

| # | 问题 | 严重性 | 修复方案 |
|---|------|--------|---------|
| 1 | 无认证 — 任何人可访问所有 API | 🔴 严重 | 添加 JWT 认证中间件 |
| 2 | 无 HTTPS — 明文传输 | 🔴 严重 | Nginx + TLS 反代 |
| 3 | API 密钥存数据库 — 可被读取 | 🔴 严重 | 迁移到环境变量，移动端不返回 |
| 4 | 无速率限制 — 可暴力攻击 | 🟡 高 | slowapi 中间件 |
| 5 | CORS 全开放 — 任意来源访问 | 🟡 高 | 限制为允许的域名 |
| 6 | 错误信息泄露堆栈 | 🟡 中 | 生产环境隐藏详细错误 |

---

## 十一、v4.0.0 构建状态

### 11.1 Windows 构建 ✅ 完成

| 产出物 | 大小 | 路径 |
|--------|------|------|
| 便携版 exe | 87 MB | `release/AI-Nexus-Assistant.exe` |
| NSIS 安装包 | 75 MB | `release/AI Nexus Assistant_4.0.0_x64-setup.exe` |
| MSI 安装包 | 77 MB | `release/AI Nexus Assistant_4.0.0_x64_en-US.msi` |
| WebView2 loader | 134 KB | `release/nexus_ui_lib.dll` |
| 更新清单 | - | `release/latest.json` |

### 11.2 Android 构建 — 通过 GitHub Actions

本地构建受 Windows 中文用户名路径编码问题影响（Kotlin 编译器无法处理非 ASCII 路径）。
已配置 GitHub Actions 工作流 `.github/workflows/build-android.yml`，在干净的 Linux 环境中构建。

**触发方式**:
```bash
# 推送 tag 触发自动构建
git tag v4.0.0
git push origin v4.0.0

# 或手动触发
gh workflow run build-android.yml
```

**产出物**: APK 文件（通过 GitHub Actions Artifacts 下载）

### 11.3 iOS 构建 — 通过 GitHub Actions

iOS 构建必须在 macOS 环境中进行。已配置 GitHub Actions 工作流 `.github/workflows/build-ios.yml`。

**触发方式**:
```bash
# 同样通过 tag 或手动触发
gh workflow run build-ios.yml
```

**产出物**: IPA 文件（通过 GitHub Actions Artifacts 下载）

### 11.4 已知限制

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Android 本地构建失败 | Windows 中文用户名导致 Kotlin 路径编码错误 | 使用 GitHub Actions 构建 |
| iOS 无法本地构建 | 必须 macOS 环境 | 使用 GitHub Actions 构建 |
| updater 插件仅桌面端 | Tauri 官方限制 | 移动端走应用商店更新 |

---

## 十二、后续版本路线图

| 版本 | 主题 | 关键特性 | 预计时间 |
|------|------|---------|---------|
| **v4.0.0** | 多端 + 安全 | Android 适配 + 自动更新 + JWT 认证 | 2026 Q3 |
| v4.1.0 | iOS 适配 | iOS 构建 + App Store 发布 | 2026 Q3-Q4 |
| v4.2.0 | 离线支持 | 本地 SQLite 缓存 + LWW 同步 | 2026 Q4 |
| v5.0.0 | Rust 原生 | 核心逻辑 Rust 重写，淘汰 Python sidecar | 2027 Q1 |

---

*本文档由深度调研生成，覆盖 5 个研究方向、20+ 信息源，经过多源交叉验证。*
