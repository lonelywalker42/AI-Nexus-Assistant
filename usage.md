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
# 安装时勾选 "使用 C++ 的桌面开发"

# 3. 安装 Windows SDK
winget install Microsoft.WindowsSDK.10.0.26100

# 4. 克隆项目
git clone https://github.com/lonelywalker42/AI-Nexus-Assistant.git
cd AI-Nexus-Assistant

# 5. 安装 Python 依赖
pip install -e .
pip install fastapi uvicorn

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

---

## 启动

### Tauri 2 版

```bash
# 终端 1: 启动 Python 后端
cd AI-Nexus-Assistant
python server.py
# 输出: Starting AI Nexus Assistant API on http://127.0.0.1:8765

# 终端 2: 启动 Tauri 前端
cd AI-Nexus-Assistant/nexus-ui
npm run tauri dev
# 或直接运行构建好的 exe:
# ./src-tauri/target/release/nexus-ui.exe
```

后端 API 文档: http://127.0.0.1:8765/docs

### PySide6 版

```bash
python main.py
```

---

## 功能说明

### 全局仪表盘

应用首页，展示关键指标：
- 今日任务数 + 完成率
- 月度完成率
- 进行中/规划中/已完成试验数
- 知识卡片总数
- 近期活动流

数据从 FastAPI `/api/dashboard` 实时加载。

### 任务与日程

**日历视图**
- 左侧月历，有待办日期显示圆点标记
- 橙色 = 待办未完成，绿色 = 全部完成
- 点击日期切换，带日期标记

**添加待办**
1. 输入框输入任务内容
2. 选择优先级（普通/低/高/紧急）
3. 点击"添加"或按 Enter

**跳转今日**
- 点击"跳转今日"按钮回到当天

**操作**
- 点击圆圈切换完成状态
- 点击 ✕ 删除任务
- 时间显示：创建于 / 完成于

### 文献管理

#### 关键词检索
1. 输入关键词（支持多个，OR 连接）
2. 勾选数据源（默认: OpenAlex + arXiv + Semantic Scholar）
3. 点击"搜索"

搜索使用空格连接关键词，结果以卡片形式展示。

#### AI 综述 / 选题讨论 / 历史记录
- 切换 Tab 使用
- 综述以 Markdown 格式渲染
- 选题 JSON 自动美化为 Markdown
- 历史支持双击详情和重载

### 试验管理

**布局**: 左侧列表 + 右侧详情

**新建试验**: 点击"新建试验"输入名称

**试验结果**: 查看版本化结果（版本号/描述/结论/日期）

### 知识库

**浏览**: 卡片网格展示，支持搜索和来源过滤

**新建卡片**: 点击"新建卡片"

**来源类型**: 手动创建 / 文献导入 / AI 对话

### AI 对话

**模型选择**: 左上角下拉框

**发送消息**: 输入框 + Enter 发送

**流式输出**: AI 回复实时显示，thinking 内容可折叠

**会话管理**: 新建 / 删除对话

**写作辅助**: 润色 / 翻译 / LaTeX / 摘要快捷按钮

**保存为知识卡片**: 将 AI 回复保存到知识库

### 桌面时钟（PySide6 版）

- 状态栏显示 HH:MM:SS
- 托盘菜单"显示浮动时钟"
- 双击切换：辉光管 → 机械表 → 番茄钟

### 设置

**AI 模型配置**: 添加/删除模型，支持 OpenAI 和 Anthropic 协议

**主题**: 浅色 / 深色切换

**数据管理**: 导入 ai-literature JSON / DeepSeek 对话 / PDF / 手动备份

---

## 系统行为（PySide6 版）

### 无边框窗口
- 自定义标题栏：拖拽移动 + 最小化/最大化/关闭
- 关闭 → 最小化到系统托盘

### 系统托盘
- 双击恢复窗口
- 右键：打开 / 显示浮动时钟 / 退出

### 自动备份
- 启动时自动执行
- 保留：1 月 + 1 周 + 6 日
- 位置：`data/backups/`

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+K | 命令面板（PySide6 版） |
| Enter | 发送消息 / 添加任务 |
| Shift+Enter | 换行 |

---

## 构建

### Tauri 2 版

```bash
cd nexus-ui
npm run tauri build
# 输出: src-tauri/target/release/nexus-ui.exe (11MB)
```

### PySide6 版

```bash
python build.py
# 输出: dist/ 目录
```

---

## 常见问题

**Q: Tauri 版编译失败？**
A: 确保安装了 VS Build Tools 的 C++ 工作负载和 Windows SDK。

**Q: 后端启动失败？**
A: 确保安装了 `fastapi` 和 `uvicorn`：`pip install fastapi uvicorn`

**Q: 搜索没有结果？**
A: 确认网络连接正常。搜索使用空格连接关键词。

**Q: AI 功能不工作？**
A: 在设置中添加 AI 模型配置，确保 API Key 正确。

**Q: 如何备份数据？**
A: PySide6 版自动备份。Tauri 版在设置中点击"手动备份"。

**Q: 两个版本数据互通吗？**
A: 是的，两个版本共用同一个 `data/nexus.db` 数据库。
