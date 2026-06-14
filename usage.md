# 使用说明

## 环境要求

### Tauri 2 版（推荐）
- Rust 1.70+ (通过 rustup 安装)
- Node.js 18+
- Python 3.10+
- Visual Studio Build Tools (C++ 工作负载) + Windows SDK
- 约 500MB 磁盘空间

### PySide6 版
- Python 3.10+
- Windows 10/11
- 约 250MB 磁盘空间

---

## 安装

### Tauri 2 版

```bash
# 1. 安装 Rust
winget install Rustlang.Rustup

# 2. 安装 VS Build Tools (C++ 工作负载)
# 下载: https://aka.ms/vs/17/release/vs_BuildTools.exe

# 3. 安装 Windows SDK
winget install Microsoft.WindowsSDK.10.0.26100

# 4. 克隆项目
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 5. 安装 Python 依赖
pip install -e .
pip install fastapi uvicorn openai anthropic

# 6. 安装前端依赖
cd nexus-ui
npm install
```

### PySide6 版

```bash
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant
pip install -e .
```

### 便携版

下载 `AI-Nexus-Assistant-v1.3.0.exe`，双击即可运行。单文件 (43MB)，无需额外依赖。

---

## 启动

### Tauri 2 版

```bash
# 终端 1: 启动后端
python server.py

# 终端 2: 启动前端
cd nexus-ui
npm run tauri dev
```

### PySide6 版

```bash
python main.py
```

### 便携版

双击 `AI-Nexus-Assistant.exe`，后端自动启动。

---

## 功能说明

### 全局仪表盘

- 6 个统计卡片（今日任务/月度完成率/试验/知识卡片）
- 点击卡片跳转对应页面
- 近期活动流

### 任务与日程

**日历视图**
- 月历，有待办日期显示圆点（橙色=待办，绿色=完成）
- 点击日期切换，"跳转今日"按钮

**添加待办**
- 输入内容 + 选择优先级（普通/低/高/紧急）+ 类别（普通/主线/文献/试验）
- 主线任务紫色边框 + "主线"标签 + 自动置顶

**操作**
- 点击圆圈切换完成，点击 ✕ 删除

### 文献管理

**关键词检索**
1. 输入关键词（多个用 OR 连接）
2. 勾选数据源
3. 点击"搜索"

**AI 综述 / 选题讨论 / 历史记录**
- 切换 Tab 使用
- 综述 Markdown 渲染
- 历史支持重载

### 试验管理

- 左侧列表 + 右侧详情
- 版本化结果（版本号/描述/参数/代码片段/结论）
- Markdown 导出

### 知识库

**创建卡片**
- 点击"新建卡片"

**导入**
- **JSON 文件**：支持 ai-literature 格式和 DeepSeek 对话格式
- **Markdown 文件**：按 `##` 标题自动分割
- **PDF 文献**：AI 自动提取摘要、关键点、标签

**浏览**
- 卡片网格，搜索 + 来源过滤
- 星级评分（1-5 星）

### AI 对话

**模型选择**: 左上角下拉框

**发送消息**: Enter 发送，支持 Markdown 渲染

**流式输出**: 实时显示，thinking 内容可折叠

**写作辅助**: 润色/翻译/LaTeX/摘要

**会话管理**: 新建/删除对话

### 设置

**AI 模型配置**: 添加/编辑/删除模型，支持 OpenAI 和 Anthropic 协议

**主题**: 浅色/深色切换

**数据管理**: JSON 导入 / 手动备份

---

## 窗口控制（Tauri 版）

- **拖拽**: 标题栏区域可拖拽移动窗口
- **最小化**: 点击标题栏 — 按钮
- **最大化**: 点击标题栏 □ 按钮
- **关闭**: 点击标题栏 × 按钮

> 权限由 `src-tauri/capabilities/default.json` 声明，Tauri 2 必须有此文件才能使用窗口控制。

---

## 系统托盘（PySide6 版）

- 关闭窗口 → 最小化到托盘
- 双击托盘 → 恢复窗口
- 右键 → 打开/显示时钟/退出

## Tauri 特色功能

### 关闭窗口后
- 主窗口最小化到系统托盘（任务栏不显示）
- 自动弹出**辉光管时钟** + **待办日历**

### 辉光管时钟
- 双击 → 返回主窗口
- 右键 → 倒计时（15/30/45/60/90分钟/自定义）/ 透明背景 / 显示待办日历 / 返回主窗口
- 滚轮 → 缩放（0.6x-2.5x）
- 拖拽 → 移动窗口

### 待办日历
- 实时时钟 + 日期星期
- 主线任务置顶 + 未完成待办
- 点击任务 → 切换完成状态
- 拖拽顶部 → 移动窗口

### 系统托盘
- 右键 → 显示主窗口 / 显示时钟 / 显示待办日历 / 退出
- 双击 → 恢复主窗口

---

## 构建

### Tauri 便携版

```bash
python build_tauri.py    # 一键构建 (sidecar + 前端 + 嵌入 + 打包)
```

或分步：
```bash
python build_server.py   # 构建后端 sidecar (~31MB)
cd nexus-ui && npx tauri build  # 构建前端 + 嵌入 + 打包
```

### PySide6 版

```bash
python build.py
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+K | 命令面板（PySide6 版） |
| Enter | 发送消息 / 添加任务 |
| Shift+Enter | 换行 |

---

## 数据存储

```
data/
├── nexus.db          # SQLite 主数据库
├── backups/          # 自动备份
├── exports/          # 导出文件
└── uploads/          # 上传的文件
```

---

## 常见问题

**Q: Tauri 编译失败？**
A: 确保安装了 VS Build Tools C++ 工作负载和 Windows SDK。

**Q: 后端启动失败？**
A: `pip install fastapi uvicorn`，然后 `python server.py`。便携版可查看 `data/server.log` 排查启动错误。

**Q: 搜索没有结果？**
A: 检查网络连接。搜索使用空格连接关键词。

**Q: AI 功能不工作？**
A: 在设置中添加 AI 模型配置。

**Q: 两个版本数据互通吗？**
A: 是的，共用 `data/nexus.db`。

**Q: 便携版如何使用？**
A: 两个 exe 放同一目录，双击 `AI-Nexus-Assistant.exe`，后端自动启动（约 5-10 秒）。

**Q: Tauri 窗口显示 "localhost 拒绝连接"？**
A: 必须用 `npx tauri build`（不是 `cargo build --release`）构建，否则前端文件不会嵌入 exe。运行 `python build_tauri.py` 可自动完成。

**Q: 端口 8765 被占用？**
A: 关闭之前启动的 sidecar 进程。Tauri 应用会自动检测端口占用，如果后端已在运行则跳过启动。
