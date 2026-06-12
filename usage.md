# 使用说明

## 环境要求

### PySide6 版
- Python 3.10+
- Windows 10/11
- 约 250MB 磁盘空间

### Tauri 2 版
- Rust 1.70+ (通过 rustup 安装)
- Node.js 18+
- Visual Studio Build Tools (C++ 工作负载)
- 约 500MB 磁盘空间

---

## 安装

### PySide6 版

```bash
# 基础安装
cd AI-Nexus-Assistant
pip install -e .

# 完整安装（含 ChromaDB 向量搜索，约 +400MB）
pip install -e ".[full]"
```

### Tauri 2 版

```bash
# 1. 安装 Rust
winget install Rustlang.Rustup

# 2. 安装 VS Build Tools (C++ 工作负载)
# 下载: https://aka.ms/vs/17/release/vs_BuildTools.exe
# 安装时勾选 "使用 C++ 的桌面开发"

# 3. 安装前端依赖
cd nexus-ui
npm install

# 4. 启动开发模式
npm run tauri dev
```

---

## 启动

### PySide6 版

```bash
python main.py
```

启动后显示无边框窗口，左侧侧边栏导航，右侧内容区域，底部状态栏显示时钟。

### Tauri 2 版

```bash
cd nexus-ui
npm run tauri dev
```

---

## 功能说明

### 全局仪表盘

应用首页，展示关键指标：
- 今日任务数 + 完成率
- 文献总数 + 本月新增
- 进行中试验数
- 知识卡片总数
- 近期活动流（任务/搜索/试验）

### 任务与日程

**日历视图**
- 左侧月历，有待办日期显示圆点标记
- 橙色 = 待办未完成，绿色 = 全部完成
- 点击日期查看该日待办

**添加待办**
1. 输入框输入任务内容
2. 选择优先级（普通/低/高/紧急）
3. 点击"添加"或按 Enter

**跳转今日**
- 点击"跳转今日"按钮回到当天

### 文献管理

#### 关键词检索
1. 在关键词组中输入搜索词
2. 组内用 AND 连接，组间用 OR 连接
3. 勾选数据源（默认: OpenAlex + arXiv + Semantic Scholar）
4. 点击"搜索"

**注意**: 搜索使用空格连接关键词（与 ai-literature 原版一致），不是 AND/OR 布尔运算符。

#### AI 综述
1. 先通过关键词检索获取文献
2. 切换到"AI 综述" Tab
3. 点击"生成综述"
4. 综述以 **Markdown 格式** 渲染（支持标题、列表、代码块）
5. 流式生成，实时显示

#### 选题讨论
1. 输入研究方向或兴趣
2. 点击"开始讨论"
3. AI 返回 JSON 格式选题方案
4. 自动解析并美化为 **Markdown 格式** 显示

#### 历史记录
- 所有操作自动保存（最多 100 条）
- **双击** 查看详情（搜索结果/综述/选题）
- 点击 **"重载"** 按钮重新执行搜索或查看历史内容
- 底部预览区显示详情

### 试验管理

**布局**: 左侧试验列表 + 右侧详情（3 Tab）

**基本信息 Tab**
- 状态选择：planning / running / completed / suspended
- 背景、目标、实验设置（自动保存）

**试验结果 Tab**
- 添加新版本（描述 + 参数JSON + 代码片段 + 结果数据 + 结论）
- 版本号自动递增
- 参数对比视图

**关联 Tab**
- 关联文献和任务

### 知识库

**浏览与筛选**
- 搜索框：按标题/摘要/笔记模糊搜索
- 来源过滤：全部 / 手动创建 / 文献导入 / AI对话
- 标签过滤

**新建知识卡片**
- 填写标题、摘要、分类路径、标签

**卡片详情**
- 编辑摘要和用户笔记
- 星级评分（1-5 星）

**多格式导入**（设置页面）
- ai-literature JSON — 文献库 + 搜索历史
- DeepSeek 对话 JSON — 转为知识卡片
- PDF 文献 — PyMuPDF 解析

### AI 对话

**模型选择**
- 左上角下拉框选择 AI 模型
- 模型列表从设置页面同步

**发送消息**
- 输入框输入消息
- Enter 发送，Shift+Enter 换行
- AI 回复以 **Markdown 格式** 渲染

**Thinking 折叠**
- DeepSeek-R1 等思考模型的推理过程默认折叠
- 点击可展开/折叠

**写作辅助**
- 选中文本（或直接输入），点击快捷按钮：
  - 润色：改进学术表达
  - 翻译：中英互译
  - LaTeX：转为 LaTeX 代码
  - 摘要：生成中英文摘要

**会话管理**
- 新建对话 / 删除对话（带确认）
- 会话列表实时更新

### 桌面时钟

**状态栏时钟**
- 主窗口底部右侧显示 HH:MM:SS

**浮动时钟**
- 托盘菜单 → "显示浮动时钟"
- 双击切换模式：辉光管 → 机械表 → 番茄钟
- 右键菜单：模式切换 / 番茄钟控制 / 关闭

**番茄学习钟**
- 默认 25 分钟工作 + 5 分钟休息
- 右键菜单可选 15/25/30/45 分钟
- 蓝色进度环（工作中）/ 绿色（休息中）/ 灰色（空闲）

### 命令面板

按 **Ctrl+K** 唤出：
- 输入关键词搜索所有模块
- 输入页面名称快速跳转
- ↑↓ 键导航，Enter 选择，Esc 关闭

### 设置

**AI 模型配置**
- 添加/编辑/删除模型
- 支持 OpenAI 和 Anthropic 协议
- DeepSeek thinking 内容自动折叠

**主题切换**
- 浅色 / 深色一键切换
- 所有页面即时更新

**数据管理**
- 导入 ai-literature JSON
- 导入 DeepSeek 对话 JSON
- 导入 PDF 文献
- 手动备份

---

## 系统行为

### 无边框窗口
- 自定义标题栏：拖拽移动 + 最小化/最大化/关闭
- 关闭按钮 → 最小化到系统托盘（不退出）

### 系统托盘
- 双击托盘图标恢复窗口
- 右键菜单：打开主窗口 / 显示浮动时钟 / 退出

### 自动备份
- 每次启动时自动执行
- 保留策略：1 月备份 + 1 周备份 + 6 日备份
- 备份文件位于 `data/backups/`

---

## 数据存储

```
data/
├── nexus.db          # SQLite 主数据库
├── nexus.db-wal      # WAL 日志
├── nexus.db-shm      # 共享内存
├── backups/          # 自动备份
├── exports/          # 导出文件
└── uploads/          # 上传的文件
```

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+K | 命令面板（全局搜索） |
| Enter | 发送消息 / 添加任务 |
| Shift+Enter | 换行（对话输入框） |
| Esc | 关闭对话框 |

---

## 构建 EXE

### PySide6 版

```bash
python build.py
```

输出位于 `dist/` 目录。

### Tauri 2 版

```bash
cd nexus-ui
npm run tauri build
```

输出位于 `nexus-ui/src-tauri/target/release/`。

---

## 常见问题

**Q: 搜索没有结果？**
A: 确认数据源已勾选，网络连接正常。Scopus 需要 API Key。搜索使用空格连接关键词，不是 AND/OR。

**Q: AI 功能不工作？**
A: 在设置中添加 AI 模型配置，确保 API Key 正确。

**Q: 主题切换后部分页面样式未更新？**
A: 切换主题后会自动刷新当前页面。如果其他页面样式未更新，切换到该页面即可。

**Q: Tauri 版编译失败？**
A: 确保安装了 VS Build Tools 的 C++ 工作负载。在管理员 PowerShell 中运行：
```powershell
& "C:\Program Files (x86)\Microsoft Visual Studio\Installer\setup.exe" modify --installPath "C:\Program Files\Microsoft Visual Studio\2022\Community" --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
```

**Q: 如何备份数据？**
A: 应用启动时自动备份。也可在设置中点击"手动备份"。

**Q: 浮动时钟如何使用？**
A: 右键系统托盘 → "显示浮动时钟"。双击切换模式（辉光管/机械表/番茄钟），右键菜单控制番茄钟。
