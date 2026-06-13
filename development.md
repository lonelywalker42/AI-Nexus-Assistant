# 开发进展

## 总体进度

```
Phase 1: 基础框架 + 任务 + 文献 + 设置     [████████████████████] 100%  ✅ 完成
Phase 2: 试验管理 + 知识库 + AI对话         [████████████████████] 100%  ✅ 完成
Phase 3: 仪表盘 + 时钟 + 命令面板 + 打包    [████████████████████] 100%  ✅ 完成
Phase 4: Bug修复 + UI优化 + 无边框窗口      [████████████████████] 100%  ✅ 完成
Phase 5: Tauri 2 前端 + FastAPI 后端        [████████████████████] 100%  ✅ 完成
Phase 6: Issue修复 + 知识库增强             [████████████████████] 100%  ✅ 完成
Phase 7: Sidecar修复 + Tauri2窗口权限       [████████████████████] 100%  ✅ 完成
Phase 8: v1.1.0 原生菜单 + 暖色 + AI修复   [████████████████████] 100%  ✅ 完成
```

---

## Phase 1: 基础框架 ✅ (2026-06-11)

- 项目骨架 (pyproject.toml, main.py, db.py)
- 数据模型 (Task, WeeklyPlan, Paper, ModelConfig, SearchHistory)
- 统一主题系统 (暗色/亮色)
- 主窗口框架 (侧边栏 + QStackedWidget + 系统托盘)
- 任务与日程模块 (日历 + 待办 + 周计划 + 统计)
- 文献搜索引擎 (8源并行 + 摘要补全 + 评分 + 引用)
- AI服务层 (OpenAI + Anthropic 双协议)
- 文献管理页面 (5 Tab)
- 设置页面 (AI模型 + 主题 + 搜索)

## Phase 2: 核心功能 ✅ (2026-06-12)

- 试验管理 (Experiment + ExperimentResult, 版本化+代码片段)
- 知识库 (KnowledgeCard + Tag + CardTag)
- AI对话 (ChatSession + ChatMessage, 流式+thinking)
- 写作辅助 (润色/翻译/LaTeX/摘要)
- 跨模块联动

## Phase 3: 完善 ✅ (2026-06-12)

- 仪表盘 (统计卡片 + 近期活动)
- 时钟组件 (辉光管/机械表 + 浮动窗口)
- 命令面板 (Ctrl+K)
- 自动备份 (1月+1周+6日)

## Phase 4: Bug修复 + UI优化 ✅ (2026-06-12)

- 文献搜索名称映射修复
- 主题切换修复
- 全页面UI优化 (圆角/共享QSS)
- Markdown渲染
- 文献管理渲染修复
- 无边框窗口 + 浮动时钟

## Phase 5: Tauri 2 + FastAPI ✅ (2026-06-12~13)

- Rust 1.96.0 + VS Build Tools + Windows SDK
- Tauri 2 项目 (React + TypeScript + Tailwind + Open Sans)
- FastAPI 后端 (36+ REST 路由)
- API 客户端 (TypeScript 类型定义)
- 7 个页面连接 API
- Sidecar 自动启动后端
- 便携版构建 (AI-Nexus-Assistant.exe 11MB + nexus-server 347MB)

## Phase 6: Issue修复 + 知识库增强 ✅ (2026-06-13)

### 10个Issue全部修复

| Issue | 修复内容 |
|-------|----------|
| 1. 托盘图标 | 多层渲染（柔光+阴影+渐变+高光+文字阴影） |
| 2. 模型编辑 | 设置页添加模型表单 + 编辑功能 |
| 3. 前后端链接 | 主题切换/数据管理/添加模型连接API |
| 4. Markdown渲染 | renderMarkdown() 函数 |
| 5. 知识库导入 | PDF(含AI提取) + Markdown + DeepSeek JSON + AI生成卡片 |
| 6. 仪表盘跳转 | 统计卡片可点击跳转 |
| 7. 窗口控制 | data-tauri-drag-region + 最小化/最大化/关闭 |
| 8. 主线任务 | category=main 紫色高亮 + 自动置顶 |
| 9. Tauri启动 | Rust setup() graceful处理sidecar |
| 10. Release EXE | 移除externalBin，自动查找server.py |

### 新增API端点

| 端点 | 说明 |
|------|------|
| POST /api/backup | 手动备份 |
| POST /api/knowledge/import/json | JSON导入 |
| POST /api/knowledge/import/pdf | PDF导入+AI提取 |
| POST /api/knowledge/import/md | Markdown分割导入 |
| POST /api/knowledge/generate | AI生成知识卡片 |

## Phase 7: Sidecar修复 + Tauri2窗口权限 ✅ (2026-06-13)

### Sidecar启动无响应修复

| 修复 | 说明 |
|------|------|
| server.py 日志重定向 | 冻结模式下 stdout/stderr 重定向到 `data/server.log` |
| server.py 错误捕获 | try/except 包裹所有导入和初始化，致命错误写入日志 |
| build_server.py hidden imports | 补充 `search.scorer/citation/enricher/sources.base` + `httptools/h11` |
| build_server.py 排除模块 | 排除 40+ 不需要的模块（torch/scipy/numpy/pandas/PySide6 等） |
| build_server.py 体积优化 | sidecar 从 2.6GB 降至 31MB |
| build_tauri.py 路径修复 | sidecar 查找路径从 `binaries/` 修正为 `release/`，自动复制 |

### Tauri 2 窗口控制修复

| 修复 | 说明 |
|------|------|
| 新建 `capabilities/default.json` | 声明窗口权限：minimize/maximize/close/drag/isMaximized 等 |

**根因**: Tauri 2 采用 capability-based 权限模型，缺少 capabilities 文件导致所有窗口操作被默认拒绝。

### Tauri 2 启动等待修复

| 修复 | 说明 |
|------|------|
| lib.rs wait_for_backend() | Rust 侧 TCP 探测端口 8765，最多等 30 秒后才打开 webview |
| lib.rs 端口冲突检测 | 启动前先检查端口是否已被占用，避免重复绑定 Errno 10048 |

**根因**: `--onefile` exe 解压需 5-8 秒，Rust 未等待后端就绪就打开 webview，导致首次连接失败。

### Tauri 2 前端嵌入修复

| 修复 | 说明 |
|------|------|
| build_tauri.py | `cargo build --release` 改为 `npx tauri build`，正确嵌入 dist/ 到 exe |
| lib.rs 端口检测 | 启动前 TCP 探测，后端已运行则跳过 sidecar 启动 |

**根因**: `cargo build --release` 不会嵌入前端资源到 exe，webview 加载空白页显示 "localhost 拒绝连接"。必须用 `npx tauri build` 触发完整的构建流程（Vite 构建前端 → 编译 Rust → 嵌入 dist/ → 打包）。

---

## Phase 8: v1.1.0 ✅ (2026-06-13)

### 功能更新
- 时钟右键菜单改为 Rust 原生菜单（不受窗口边界限制）
- 自定义倒计时使用独立输入窗口 + START/CANCEL 按钮
- 暖色配色方案（#F5F0E1 背景, #E07A5F 主题色）
- 文献历史记录删除功能
- 知识库 PDF 导入改用 base64 + JSON 传输
- 模型编辑保存改为 PUT 更新（不新建）
- 滚轮缩放时钟窗口（0.6x-2.5x）

### Bug 修复
- openai/anthropic 库打包：移除 httpx 排除 + 添加 hidden-import
- AI 协议降级：anthropic 未安装时自动 fallback 到 openai
- API Key 保存：模型 CRUD 后 AIRouter.reload() 刷新缓存
- 时钟窗口死锁：异步线程创建避免阻塞菜单事件
- PDF 导入：FormData → base64 JSON 传输
- 子窗口 IPC：capabilities windows: ["*"] 授权所有窗口

### 调试经验
- Tauri 2 子窗口不自动注入 JS 模块，需 initialization_script 注入
- -webkit-app-region: drag 会吞掉所有鼠标事件
- on_menu_event 中调用 close()/destroy() 会死锁主线程
- PyInstaller 不检测函数内动态 import，需 hidden-import
- openai 依赖 httpx，不能在 exclude-module 中排除

---

## Git 历史

```
53b4ccb fix: 用npx tauri build替代cargo build，正确嵌入前端资源
7870603 fix: 先检查端口占用再启动sidecar，避免重复绑定冲突
5219629 fix: 移除reqwest依赖，改用TCP探测后端端口
3a4a2d7 fix: sidecar 2.6GB→31MB + Rust等待后端就绪再打开webview
df928e0 refactor: build_server改用专用最小venv构建
60d7caf fix: 排除40+个不需要的模块，sidecar从2.6GB预期降至~50MB
78f41d4 fix: sidecar启动日志+补全hidden imports+Tauri2窗口权限
34600b7 fix: 剩余issue修复 — 托盘图标/窗口控制/知识库导入
979b1f2 fix: 多项修复 — 设置/对话/仪表盘/任务/后端API
1b85db7 feat: Tauri便携版构建 — sidecar自动启动后端
8104de6 docs: 更新文档 + Tauri 2 前端项目初始化
e7b25b4 fix: 文献管理渲染修复 - Markdown/JSON/历史重载
2c30c74 fix: 5项重大修复 — 搜索/主题/UI/Markdown/无边框
2ab9795 fix: 侧边栏导航修复 + AI对话页面UI优化
741bae5 feat: 5项修复 + 玻璃质感UI重构
4ddfd26 fix: 5项修复 — UI配色/任务跳转/文献搜索/托盘图标/时钟番茄钟
1cfadf8 style: UI美化 — 精致主题系统 + 组件样式优化
0021d53 feat: Phase 2 — 试验管理 + 知识库 + AI对话
225101a fix: pyproject.toml build-backend and package discovery
96f5eff fix: QSizePolicy import and task_service query
fef9c46 feat: Phase 1 — 项目骨架 + 任务 + 文献 + 搜索引擎 + AI服务 + 设置
```

---

## 测试状态

| 测试项 | 状态 |
|--------|------|
| Python 模块导入 | ✅ |
| 数据库 CRUD | ✅ |
| PySide6 主窗口 | ✅ |
| 文献搜索 | ✅ |
| 主题切换 | ✅ |
| AI 对话 Markdown | ✅ |
| 历史记录重载 | ✅ |
| 自动备份 | ✅ |
| FastAPI 后端 | ✅ |
| Tauri 构建 | ✅ |
| 前后端连接 | ✅ |
| 窗口拖拽/关闭 | ✅ |
| 知识库导入(JSON/MD) | ✅ |
| 主线任务置顶 | ✅ |
