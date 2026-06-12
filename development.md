# 开发进展

## 总体进度

```
Phase 1: 基础框架 + 任务 + 文献 + 设置     [████████████████████] 100%  ✅ 完成
Phase 2: 试验管理 + 知识库 + AI对话         [████████████████████] 100%  ✅ 完成
Phase 3: 仪表盘 + 时钟 + 命令面板 + 打包    [████████████████████] 100%  ✅ 完成
Phase 4: Bug修复 + UI优化 + 无边框窗口      [████████████████████] 100%  ✅ 完成
Phase 5: Tauri 2 前端重构                   [████░░░░░░░░░░░░░░░░]  20%  🚧 进行中
```

---

## Phase 1: 基础框架 ✅ (2026-06-11)

### 1. 项目骨架 ✅
- `pyproject.toml` — 项目配置 + 依赖声明
- `main.py` — QApplication + Fusion + init_db
- `app/db.py` — SQLAlchemy engine + WAL模式
- `app/utils/paths.py` — PyInstaller兼容路径

### 2. 数据模型 ✅
- `Task` + `WeeklyPlan` — 任务与周计划
- `Paper` — 学术文献
- `ModelConfig` — AI模型配置
- `SearchHistory` — 搜索历史

### 3. 统一主题系统 ✅
- 暗色/亮色双主题 (Catppuccin)
- ThemeManager + theme_changed信号
- 10+ QSS模板常量

### 4. 主窗口框架 ✅
- 侧边栏260px + QStackedWidget
- 7项导航 + 分组标签
- QSystemTrayIcon系统托盘

### 5. 任务与日程模块 ✅
- 日历视图 + 待办CRUD + 周计划
- 优先级四级 + 分类标签
- 统计面板 + 月度完成率

### 6. 文献搜索引擎层 ✅
- 8个数据源适配器
- 统一引擎 + 并行搜索
- 相似度评分 + GB/T 7714引用

### 7. AI服务层 ✅
- OpenAI + Anthropic双协议
- 流式输出 + thinking折叠
- 多模型路由

### 8. 文献管理页面 ✅
- 5 Tab结构
- 关键词组构建器
- PaperCard组件

### 9. 设置页面 ✅
- AI模型配置 + 主题切换
- 搜索设置 + 数据导入

---

## Phase 2: 核心功能 ✅ (2026-06-12)

### 试验管理模块 ✅
- Experiment + ExperimentResult模型（版本化+代码片段）
- CRUD + 版本管理 + Markdown导出
- 分栏布局 + 3 Tab（信息/结果/关联）

### 知识库模块 ✅
- KnowledgeCard + Tag + CardTag关联表
- 卡片CRUD + 标签管理 + 从文献生成卡片
- 卡片网格 + 搜索 + 分类/标签过滤 + 星级评分

### AI对话模块 ✅
- ChatSession + ChatMessage（含thinking_content）
- 会话管理 + 消息持久化
- 对话界面 + QThread流式输出 + thinking折叠
- 写作辅助（润色/翻译/LaTeX/摘要）
- 跨模块联动（保存为知识卡片）

### 主窗口更新 ✅
- 侧边栏7项导航全部激活
- 版本号v0.2.0

---

## Phase 3: 完善 ✅ (2026-06-12)

### 仪表盘 ✅
- 6个统计卡片 + 近期活动流
- 月度完成率 + 任务/文献/试验/知识卡片统计

### 时钟组件 ✅
- QPainter辉光管/机械表双模式
- 紧凑模式嵌入状态栏
- 浮动窗口（完整效果+双击切换）

### 命令面板 ✅
- Ctrl+K全局搜索
- 跨模块结果分组
- 页面快速跳转

### 打包与备份 ✅
- PyInstaller构建脚本
- 自动备份（1月+1周+6日）
- 启动时自动备份 + 过期清理

---

## Phase 4: Bug修复 + UI优化 ✅ (2026-06-12)

### 文献搜索关键修复 ✅
- 数据源名称映射（UI显示名→引擎内部key）
- 查询格式修正（空格连接而非AND/OR）
- 引擎选择支持大小写不敏感匹配
- 根本原因: "OpenAlex" != "openalex" 导致搜索永远返回0

### 主题切换修复 ✅
- 侧边栏/导航列表/状态栏样式随主题更新
- 所有页面添加reapply_theme方法
- 切换主题后自动刷新当前页面

### 全页面UI优化 ✅
- 统一RADIUS常量（16-24px大圆角）
- 使用共享QSS模板
- 修复硬编码颜色
- 滚动条统一细圆风格

### AI对话Markdown渲染 ✅
- AI回复使用QTextBrowser支持Markdown
- 流式输出累积后setMarkdown渲染

### 文献管理渲染修复 ✅
- AI综述: QTextBrowser + 流式Markdown渲染
- 选题讨论: JSON解析美化为Markdown格式
- 历史记录: 双击详情 + 重载按钮 + 底部预览区

### 无边框窗口 + 浮动时钟 ✅
- 主窗口FramelessWindowHint无边框
- 自定义标题栏（拖拽+最小化/最大化/关闭）
- 托盘菜单"显示浮动时钟"
- clock-1999辉光管/机械表/番茄钟完整可用

---

## Phase 5: Tauri 2 前端重构 🚧 (2026-06-12)

### 已完成
- [x] Rust安装 (1.96.0)
- [x] Tauri 2项目创建 (`nexus-ui/`)
- [x] React + TypeScript + Tailwind CSS配置
- [x] Open Sans字体集成
- [x] 玻璃质感CSS样式系统
- [x] 7个页面组件（Dashboard/Task/Literature/Experiment/Knowledge/Chat/Settings）
- [x] Sidebar组件（分组导航）
- [x] Tauri配置（无边框窗口）

### 进行中
- [ ] VS Build Tools C++工作负载安装
- [ ] Tauri Rust编译
- [ ] Python FastAPI后端API包装
- [ ] 前后端HTTP通信

### 待完成
- [ ] 所有页面功能完善
- [ ] 流式AI对话
- [ ] Markdown渲染
- [ ] 打包发布

---

## 测试状态

| 测试项 | 状态 |
|--------|------|
| 模块导入 | ✅ 通过 |
| 数据库CRUD | ✅ 通过 |
| 主窗口启动 | ✅ 通过 |
| 文献搜索（名称映射修复后） | ✅ 通过 |
| 主题切换 | ✅ 通过 |
| AI对话Markdown渲染 | ✅ 通过 |
| 历史记录重载 | ✅ 通过 |
| 无边框窗口+拖拽 | ✅ 通过 |
| 浮动时钟 | ✅ 通过 |
| 自动备份 | ✅ 通过 |

---

## Git历史

```
e7b25b4 fix: 文献管理渲染修复 - Markdown/JSON/历史重载
2c30c74 fix: 5项重大修复 - 搜索/主题/UI/Markdown/无边框
2ab9795 fix: 侧边栏导航修复 + AI对话页面UI优化
741bae5 feat: 5项修复 + 玻璃质感UI重构
4ddfd26 fix: 5项修复 - UI配色/任务跳转/文献搜索/托盘图标/时钟番茄钟
1cfadf8 style: UI美化 - 精致主题系统 + 组件样式优化
0021d53 feat: Phase 2 - 试验管理 + 知识库 + AI对话
225101a fix: pyproject.toml build-backend and package discovery
96f5eff fix: QSizePolicy import and task_service query
fef9c46 feat: Phase 1 - 项目骨架 + 任务 + 文献 + 搜索引擎 + AI服务 + 设置
```
