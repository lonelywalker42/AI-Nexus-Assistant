# 开发进展

## 总体进度

```
Phase 1: 基础框架 + 任务 + 文献 + 设置     [████████████████████] 100%  ✅ 完成
Phase 2: 试验管理 + 知识库 + AI对话         [████████████████████] 100%  ✅ 完成
Phase 3: 仪表盘 + 时钟 + 命令面板 + 打包    [████████████████████] 100%  ✅ 完成
```

---

## Phase 1: 已完成（2026-06-11）

### 1. 项目骨架 ✅

| 文件 | 说明 |
|------|------|
| `pyproject.toml` | 项目配置，依赖声明，可选 `[full]` extras |
| `main.py` | 应用入口，QApplication + Fusion + 字体 + init_db |
| `app/db.py` | SQLAlchemy engine + SessionLocal + Base + WAL模式 |
| `app/utils/paths.py` | PyInstaller 兼容的路径工具 |

### 2. 数据模型 ✅

| 模型 | 表名 | 字段数 | 说明 |
|------|------|--------|------|
| `Task` | tasks | 11 | 待办事项，关联周计划/文献/试验 |
| `WeeklyPlan` | weekly_plans | 5 | 周计划，级联删除任务 |
| `Paper` | papers | 16 | 学术文献，含引用/评分/笔记/AI摘要 |
| `ModelConfig` | model_configs | 9 | AI模型配置，OpenAI/Anthropic协议 |
| `SearchHistory` | search_history | 7 | 搜索/综述/选题历史 |

### 3. 统一主题系统 ✅

- 暗色主题（Catppuccin Mocha）+ 亮色主题
- `ThemeManager` 单例，`theme_changed` 信号
- 7 个 QSS 模板常量：BTN_PRIMARY / BTN_SECONDARY / BTN_DANGER / INPUT / COMBO / TABLE / TAB / SCROLLBAR

### 4. 主窗口框架 ✅

- 侧边栏 200px + QStackedWidget
- 6 项导航（Phase 1 激活 3 项：任务/文献/设置）
- QSystemTrayIcon 系统托盘（关闭最小化，右键菜单）
- 主题切换自动更新样式

### 5. 任务与日程模块 ✅

| 组件 | 说明 |
|------|------|
| `task_service.py` | CRUD + 周计划 + 月度统计 + 日期标记 |
| `task_page.py` | 左侧日历+统计，右侧待办列表+过滤器 |
| `calendar_widget.py` | 自定义 QCalendarWidget，paintCell 绘制圆点标记 |
| `stat_card.py` | 统计数字卡片，hover 高亮 |

### 6. 文献搜索引擎层 ✅

| 模块 | 说明 |
|------|------|
| `engine.py` | `UnifiedSearchEngine` — 8源并行 + 去重 + 摘要补全 + 评分 + 引用 |
| `sources/openalex.py` | OpenAlex API，倒排索引摘要重建 |
| `sources/crossref.py` | CrossRef REST API |
| `sources/semantic_scholar.py` | Semantic Scholar Graph API |
| `sources/arxiv.py` | arXiv Python 包 |
| `sources/pubmed.py` | PubMed E-utilities (esearch + efetch XML) |
| `sources/google_scholar.py` | scholarly 库 |
| `sources/scopus.py` | Elsevier Scopus API |
| `enricher.py` | OpenAlex 摘要补全 + 速率限制 |
| `scorer.py` | Levenshtein + 中文二元分词 + 停用词 + 相似度评分 |
| `citation.py` | GB/T 7714-2015 引用格式化（中英文分别处理） |

### 7. AI 服务层 ✅

- `AIRouter` 类：OpenAI + Anthropic 双协议
- 同步 `chat()` + 流式 `stream_chat()`
- DeepSeek `reasoning_content` 处理 → thinking 折叠
- Anthropic `thinking` block 处理
- 模型选择：purpose 匹配 → 活跃状态 → fallback

### 8. 文献管理页面 ✅

- 5 Tab 结构：关键词检索 / 标题检索 / AI综述 / 选题讨论 / 历史记录
- 关键词组构建器（AND/OR 组，动态添加/删除）
- 数据源复选框 + 最大结果数
- QThread 后台搜索 + 进度条
- `PaperCard` 组件（标题/作者/摘要/来源/操作按钮）
- 搜索历史持久化

### 9. 设置页面 ✅

- AI 模型配置：表格展示 + 添加/删除对话框
- 主题切换：暗色/亮色 QComboBox
- 搜索设置：数据源复选框 + 最大结果数
- 数据管理：导入按钮（占位）

---

## Phase 2: 已完成（2026-06-12）

### 试验管理模块 ✅

- [x] `app/models/experiment.py` — Experiment + ExperimentResult（版本化结果 + 代码片段存档）
- [x] `app/services/experiment_service.py` — CRUD + 版本管理 + Markdown 导出
- [x] `app/ui/pages/experiment_page.py` — 分栏布局 + 3 Tab（信息/结果/关联）+ 参数对比

### 知识库模块 ✅

- [x] `app/models/knowledge.py` — KnowledgeCard + Tag + CardTag 关联表
- [x] `app/services/knowledge_service.py` — 卡片 CRUD + 标签管理 + 从文献生成卡片
- [x] `app/ui/pages/knowledge_page.py` — 卡片网格 + 搜索 + 分类/标签过滤 + 星级评分

### AI 对话模块 ✅

- [x] `app/models/chat.py` — ChatSession + ChatMessage（含 thinking_content）
- [x] `app/services/chat_service.py` — 会话管理 + 消息持久化 + 消息构建
- [x] `app/ui/pages/chat_page.py` — 对话界面 + QThread 流式输出 + thinking 折叠
- [x] 写作辅助 prompt（润色/翻译/LaTeX/摘要）
- [x] 跨模块联动（保存为知识卡片）

### 主窗口更新 ✅

- 侧边栏 6 项导航全部激活
- 版本号更新为 v0.2.0

---

## Phase 3: 已完成（2026-06-12）

### 仪表盘 ✅

- [x] 统计聚合（任务/文献/试验/知识卡片）— 6 个 StatCard 网格
- [x] 近期活动流 — 最近完成的任务 + 搜索历史 + 试验更新
- [x] 进度可视化 — 月度完成率

### 时钟组件 ✅

- [x] `app/ui/widgets/clock_widget.py` — QPainter 辉光管/机械表双模式
- [x] 嵌入状态栏（紧凑模式 HH:MM:SS）
- [x] 浮动窗口（完整辉光管效果 + 双击切换机械表）

### 命令面板 ✅

- [x] `app/ui/dialogs/command_palette.py` — Ctrl+K 唤出
- [x] 全局搜索（任务/文献/试验/知识卡片）
- [x] 跨模块结果分组
- [x] 页面快速跳转

### 打包与备份 ✅

- [x] `build.py` — PyInstaller 构建脚本
- [x] `app/services/backup_service.py` — 自动备份（1月 + 1周 + 6日）
- [x] 启动时自动备份 + 备份清理

### 主窗口更新 ✅

- 侧边栏 7 项导航（新增仪表盘）
- 状态栏集成时钟组件
- Ctrl+K 命令面板快捷键
- 版本号更新为 v0.3.0

---

## 测试状态

| 测试项 | 状态 |
|--------|------|
| 模块导入 | ✅ 通过 |
| 主窗口启动（7页面+状态栏+时钟） | ✅ 通过 |
| 试验 CRUD + 版本管理 | ✅ 通过 |
| 知识卡片 + 标签管理 | ✅ 通过 |
| 对话会话 + 消息持久化 | ✅ 通过 |
| 仪表盘统计聚合 | ✅ 通过 |
| 自动备份 | ✅ 通过 |
| 命令面板搜索 | ✅ 通过 |
| 相似度评分算法 | ✅ 通过 |
| GB/T 7714 引用格式化 | ✅ 通过 |
| 数据库建表 + CRUD | ✅ 通过 |
| 主窗口启动 | ✅ 通过 |
