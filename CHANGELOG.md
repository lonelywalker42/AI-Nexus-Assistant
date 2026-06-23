# Changelog

## v4.3.2 (2026-06-23) — 检查更新修复 + 文献卡片UI优化

### 修复
- **检查更新403错误**: 修复代理环境下检查更新返回HTTP 403的问题 — 添加GitHub API请求头、403自动降级到latest.json备用通道获取版本信息，显示友好错误提示
- **自动更新进度条**: 修复下载进度显示瞬间跳到100%的bug — 正确使用contentLength计算百分比，显示下载大小（MB）和进度百分比
- **文献卡片引用按钮对齐**: 统一引用区域"复制"和"修正引用"按钮大小，与格式选择器视觉对齐（text-[11px] py-1.5）
- **引用格式DOI栏**: 引用文本下方新增DOI行，显示可点击DOI链接并提供一键复制功能

## v4.3.1 (2026-06-23) — 文献检索增强 + DeepSeek导入修复

### 新功能
- **引用格式修正**: 文献库详情面板新增"修正引用"按钮，支持按DOI或标题重新检索OpenAlex/CrossRef元数据，生成标准GB/T 7714引用格式，用户确认后更新
- **DOI复制**: 文献检索结果列表视图和网格视图均显示DOI号，点击一键复制到剪贴卡

### 修复
- **PDF拉取422错误**: 增强PDF获取管线 — 添加Unpaywall API降级链、重试机制、更精确的错误码（504超时/404未找到/403禁止访问），改进DOI格式处理
- **摘要不截断**: 搜索结果和搜索历史保存时不再截断摘要，完整显示
- **DeepSeek导入FOREIGN KEY错误**: 修复并发线程创建Tag时的UNIQUE约束冲突 — Tag创建后立即flush、失败时rollback并重新获取、并发数从20降至5、SQLite busy_timeout设为10秒
- **DeepSeek导入AI摘要全部失败**: 添加response_format自动降级（JSON模式失败则重试普通模式）、对话文本截断至12000字符、改进错误日志和失败状态报告
- **"关联对话"跳转**: 导入卡片的"查看关联对话"改为跳转到导入组详情页面
- **移除"AI对话分析"**: 移除知识卡片上无用的"AI对话分析"按钮（列表/网格/详情三处）

## v4.3.0 (2026-06-23) — 代码规范化 + 检查更新修复

### 修复
- **检查更新 404/403 错误**: 修复所有更新 URL 中 GitHub owner 从 `chenjingwei` → `lonelywalker42`
  - `tauri.conf.json` updater endpoint
  - `SettingsPage.tsx` GitHub API 检查 + 浏览器下载链接
  - `release/latest.json` 下载 URL
  - `docs/PRD-v4-cross-platform-and-updater.md` 文档引用

### 代码规范化
- **前端 API 层统一**: KnowledgePage.tsx 和 SettingsPage.tsx 共 15 处 `raw fetch()` 调用全部替换为 `client.ts` API 方法，消除 JWT 认证绕过风险
- **client.ts 补全**:
  - 新增 `APP_VERSION` 常量，消除 Sidebar/SettingsPage 版本号硬编码
  - 新增 `streamRequest()` 工具函数，`chatApi.stream` 和 `reviewsApi.generate` 共用，修复后者缺失 `try/finally` + `releaseLock()` 的 bug
  - 新增 `backupApi` 命名空间（list/create/restore/exportDb/importDb）
  - 扩展 `systemApi`（mineruStatus/searchServiceStatus/Start/Stop/installMineru）
  - 扩展 `knowledgeImportApi`（fromJson/fromMarkdown/fromPdf/fromUrl）
  - 修复 `writingApi.delete` 和 `papersApi.deleteNote` 返回类型统一为 `{ ok: boolean }`
- **重复代码消除**: `renderSimpleMarkdown`/`escapeHtml` 从 3 个页面文件提取到 `src/utils/markdown.ts`
- **server.py 修复**: 删除被覆盖的重复路由定义 `PATCH /api/tasks/{task_id}`（死代码）
- **server.py 返回格式**: `delete_writing_document` 和 `delete_paper_note` 返回 `{ ok: true }` 替代 `{ success: true }`

### 构建产物
- 版本号统一升级至 v4.3.0（tauri.conf.json + APP_VERSION）
- 便携版: `AI-Nexus-Assistant.exe`
- MSI 安装包: `AI Nexus Assistant_4.3.0_x64_en-US.msi`
- NSIS 安装包: `AI Nexus Assistant_4.3.0_x64-setup.exe`

## v4.2.0 (2026-06-23) — 游戏机模式集成 + 8 款新游戏（共 12 款）

### 新增
- **游戏机模式页面**: 侧边栏「个人助手」新增「🎮 游戏机」入口，iframe 嵌入复古街机游戏
- **8 款新游戏**:
  - **Snake** — 经典贪吃蛇，方向键控制，速度随分数递增
  - **Breakout** — 打砖块，挡板接球消除砖块，多关卡
  - **Minesweeper** — 扫雷，12×12 棋盘，20 颗雷，左键揭开/右键标记
  - **Flappy** — 像素小鸟，空格/点击跳跃，穿越管道
  - **Pac-Man** — 经典吃豆人，迷宫追逐，能量豆反杀幽灵
  - **Pong** — 乒乓球，W/S 控制挡板，对战 AI
  - **Frogger** — 青蛙过河，穿越车流与河道，5 个安全巢穴
  - **Bomberman** — 炸弹人，放置炸弹炸毁墙壁消灭敌人，收集道具
- **IconGamepad** 图标组件（游戏手柄 SVG）
- 游戏菜单升级为 2 列网格布局（12 款游戏），支持方向键导航
- 全部游戏支持存档恢复、历史最高分排行榜

### 改动
- `nexus-ui/public/games.html`: 新增 4 个游戏类 + 菜单 2 列布局 + 方向键导航
- `nexus-ui/src/pages/GameConsolePage.tsx`: 新建游戏机页面（iframe + 全屏）
- `nexus-ui/src/components/Icons.tsx`: 新增 IconGamepad
- `nexus-ui/src/App.tsx`: 注册游戏机页面到侧边栏

## v4.1.1 (2026-06-23) — DeepSeek 对话导入三问题修复

### 修复
- **导入失败率降低**: 放宽消息过滤阈值（`_SHORT_THRESHOLD` 3→1），缩小停用词范围，清洗后消息不足时自动 fallback 保留最长消息
- **摘要生成成功率提升**: AIRouter 添加 `response_format={"type": "json_object"}` 支持，含自动 fallback（模型不支持时自动重试）
- **导入会话分组管理**: ChatPage 新增「📥 导入」分类，导入的会话按分组折叠显示，可展开查看各会话

### 改动
- `app/ai/router.py`: `_call_openai()` 支持 `response_format` 参数，含 fallback 机制
- `app/db.py`: 新增 `_migrate_columns()` 增量迁移函数，自动添加缺失列
- `app/models/chat.py`: ChatSession 新增 `import_group_id` 外键字段（FK → import_groups）
- `app/services/deepseek_import_service.py`: 放宽过滤阈值 + 使用 `response_format` 调用 LLM
- `server.py`: `/api/chat/sessions` 响应包含 `import_group_id` 字段
- `nexus-ui/src/api/client.ts`: ChatSession 类型添加 `import_group_id`
- `nexus-ui/src/pages/ChatPage.tsx`: 新增「📥 导入」分类 + 分组折叠显示 UI

## v4.1.0 (2026-06-23) — PDF 文献导入体验升级（借鉴 PaperQuay）

### 新增
- **分步导入确认对话框**: PDF 导入不再直接入库，先提取元数据预览，用户可编辑后确认导入
- **自动填充元数据**: 导入确认对话框中支持一键查询 OpenAlex/Crossref 自动填充缺失元数据
- **布局分析标题提取**: 基于 PyMuPDF 字体大小分析的多策略标题提取，替代简单的首行推断
- **OpenAlex + Crossref 双级元数据增强**: DOI 提取后先查 OpenAlex，缺失字段再查 Crossref 兜底
- **标题相似度去重**: Dice 系数 + 0.78 阈值，DOI 缺失时防止重复导入
- **拖拽上传**: 文献库页面支持拖放 PDF 文件直接导入
- **自动全文提取**: PDF 导入后自动提取全文文本存入数据库，供后续 RAG 使用
- **通用标题过滤**: 自动排除 "untitled"、"Microsoft Word"、"CNKI" 等无意义标题
- **DOI 正则标准化**: 使用更精确的 `10.\d{4,9}/[-._;()/:A-Z0-9]+` 模式
- **论文分类系统**: 新增 PaperCategory 模型，支持分类 CRUD 端点
- **附件管理表**: 新增 Attachment 模型，支持一个论文关联多个文件

### 改动
- Paper 模型新增 `fulltext` 字段（Text），存储提取的全文文本
- 新增 PaperCategory、PaperCategoryLink、Attachment 数据模型
- 新增 API 端点: extract-metadata、confirm-import、lookup-metadata、categories CRUD
- `import-pdf` 端点增加标题相似度去重和自动全文提取
- `has_fulltext` 字段在所有 PDF 导入路径中一致设置为 True
- LiteraturePage PDF 导入也走 extract-metadata 流程（带去重检查）

## v4.0.1 (2026-06-22) — DeepSeek 对话智能导入

### 新增
- **DeepSeek 对话智能导入**: IDEA 页面新增「🧠 DeepSeek 智能导入」按钮，上传 DeepSeek JSON 后自动通过 LLM 生成结构化知识卡片
- **导入 Pipeline**: 解析 mapping 树 → 消息预处理 → 会话摘要 → 话题切分 → 知识卡片生成 → 标签归一化，完整 6 步 pipeline
- **对话重建**: 导入的 DeepSeek 对话自动重建为 AI 会话（ChatSession），可在 AI 对话页面查看原始对话
- **导入分组管理**: 「AI 对话」分类下新增导入分组列表视图，支持查看分组详情、话题卡片、原始对话
- **进度轮询**: 导入过程中实时显示 LLM 处理进度（2 秒轮询）
- **LLM 并发控制**: 信号量限制最大 20 个并发 LLM 请求，避免 API 过载
- **4 种 JSON 格式支持**: DeepSeek mapping 树、单对话对象、简单 messages 数组、含 messages 键的对象

### 改动
- KnowledgeCard 新增 `import_group_id` 和 `chat_session_id` 字段
- 新增 `ImportGroup` 数据模型（import_groups 表）
- 新增 6 个 API 端点: import/deepseek、import-groups CRUD、progress 轮询、messages 获取
- 卡片列表和详情接口返回 `import_group_id` 和 `chat_session_id` 字段

## v3.7.0 (2026-06-21) — 体验优化 + Bug修复 + 游戏增强

### 新增
- **书架 Reader 翻页 UI**: 改为书本翻页风格（左右点击区域 + 键盘方向键 + 翻页动画 + 折痕线）
- **书架 Reader 护眼模式**: 暖色调背景（米色纸张感），可切换开关
- **书架 Reader PDF 支持**: 集成 pdf.js，canvas 直接渲染原始 PDF 页面（保留格式/图片/公式）
- **音乐列表排序**: 按文件名/标题/艺术家排序，支持升序/降序切换，偏好持久化
- **游戏进度保存**: 退出游戏时自动保存进度，下次进入提示恢复或重新开始
- **游戏历史最高分**: 每个游戏保存前 7 名最高分，游戏结束按 H 键查看排行榜
- **设置配置指南**: 添加 open-webSearch 和 MinerU 的详细配置指南（便携版/安装程序）
- **CLAUDE.md 环境配置**: 添加面向 Claude Code 的环境配置说明（依赖/子模块/常见问题）

### 修复
- **Word Hopper CET6 词库**: 将 250+ 个英文释义翻译为中文
- **写作工作台持久化**: 修复 writingApi.list 缺少 return 语句，添加组件卸载时自动保存
- **IDEA 网页抓取分类**: 修复网页抓取导入的卡片不显示问题，添加"网页抓取"分类
- **EPUB 堆栈溢出**: 修复大文件 EPUB 解析时 `btoa(String.fromCharCode(...buf))` 导致的堆栈溢出，改用分块转换
- **EPUB 空白页**: 改进 body 提取（非贪婪匹配）、空内容检测、fallback 处理
- **PDF 渲染方式**: 从文本提取改为 canvas 直接渲染原页面，保留原始格式

### 依赖
- 新增: `pdfjs-dist`（PDF 阅读支持）

## v3.6.0 (2026-06-21) — ScholarAIO 特性移植：文献获取 + PDF 转换 + 质量管控

### 新增
- **出版社 PDF 拉取**: 输入 DOI 或论文标题，自动从出版社网站拉取 PDF（校园网环境下）
- **MinerU PDF→Markdown**: 可选安装 MinerU，将 PDF 高质量转换为 Markdown（保留公式/图片/表格），PyMuPDF 降级方案
- **arXiv 集成**: arXiv 搜索结果支持一键导入 PDF 并入库
- **多源导入**: 支持 BibTeX (.bib) 和 RIS (.ris) 文件批量导入文献
- **论文笔记系统**: PaperNote 模型 + CRUD API，支持多条笔记持久化
- **元数据质量审计**: 规则引擎检测缺失字段、DOI 重复、可疑年份等问题
- **语义近邻推荐**: 基于 FAISS 向量索引，论文详情页显示相关论文推荐
- **工作区限定搜索**: 在工作区内进行全文搜索

### 新增 API 端点
- `POST /api/papers/fetch-pdf` — 出版社 PDF 拉取
- `POST /api/papers/batch-fetch-pdf` — 批量拉取
- `POST /api/papers/{id}/refetch-pdf` — 重新拉取
- `GET /api/system/mineru-status` — MinerU 状态
- `POST /api/system/install-mineru` — 安装 MinerU
- `POST /api/papers/{id}/convert-markdown` — PDF→Markdown 转换
- `GET /api/arxiv/search` — arXiv 搜索
- `POST /api/arxiv/import` — arXiv 导入
- `POST /api/papers/import-bibtex` — BibTeX 导入
- `POST /api/papers/import-ris` — RIS 导入
- `GET/POST/PUT/DELETE /api/papers/{id}/notes` — 笔记 CRUD
- `GET /api/papers/audit` — 元数据审计
- `GET /api/papers/audit/stats` — 审计统计
- `GET /api/papers/{id}/neighbors` — 语义近邻推荐
- `GET /api/workspaces/{id}/search` — 工作区搜索

### 依赖
- 新增: `beautifulsoup4`, `lxml`, `defusedxml`（内置）
- 可选: `magic-pdf[full]`（MinerU，用户按需安装，~2GB）
- 新增: `pdfjs-dist`（PDF 阅读支持）

### 修复
- **Word Hopper CET6 词库**: 将 250+ 个英文释义翻译为中文
- **音乐列表排序**: 新增按文件名/标题/艺术家排序，支持升序/降序切换
- **书架 Reader 翻页 UI**: 改为书本翻页风格（左右点击区域 + 键盘方向键 + 翻页动画）
- **书架 Reader 护眼模式**: 新增暖色调护眼背景，可切换开关
- **写作工作台持久化**: 修复 writingApi.list 缺少 return 语句，添加组件卸载时自动保存
- **书架 Reader PDF 支持**: 集成 pdf.js，支持 PDF 文本提取和分页阅读
- **设置配置指南**: 添加 open-webSearch 和 MinerU 的详细配置指南（便携版/安装程序）
- **游戏进度保存**: 退出游戏时自动保存进度，下次进入提示恢复或重新开始
- **游戏历史最高分**: 每个游戏保存前 7 名最高分，按 H 键查看排行榜
- **IDEA 网页抓取分类**: 修复网页抓取导入的卡片不显示问题，添加"网页抓取"分类
- **CLAUDE.md 环境配置**: 添加面向 Claude Code 的环境配置说明（依赖/子模块/常见问题）

## v3.5.0 (2026-06-21) — 科研 Agent 工作流 + 体验优化

### 新增
- **科研 Agent 工作流**: 文献综述、论文写作、实验设计、同行评审、多视角讨论 5 种 Agent
- **停止生成按钮**: 流式输出时显示红色"停止生成"按钮，使用 AbortController 取消请求
- **消息重新生成**: 最后一条 AI 回复 hover 显示 🔄 按钮，支持重新生成
- **会话搜索**: AI 对话左侧增加搜索框，支持按标题过滤会话
- **Token 统计**: 消息旁显示 token 消耗和响应时间
- **侧边栏可折叠分组**: 点击组标题 (总览/科研助手/个人助手/设置) 可展开/收起
- **知识卡片批量操作**: 批量模式下支持全选/多选 + 批量导出 JSON + 批量删除
- **知识图谱可视化**: SVG 力导向图展示卡片关联，点击节点查看详情
- **标签层级**: 支持 `#parent/child` 嵌套标签，新增 `/api/knowledge/tags/tree` 端点
- **仪表盘图表**: 本周任务趋势柱状图 + 实验状态分布图
- **实验并排对比**: 选择两个实验对比详情 (状态/目标/背景/结果)
- **多视角讨论**: 4 个视角 (方法论/领域/批判/实践) 多轮辩论 + 综合分析
- **MCP 协议基础**: 基础 MCP 客户端框架，支持工具发现和调用
- **Generative UI**: 工具调用结果渲染为结构化卡片，显示摘要和结果数量
- **OS 主题跟随**: 启动时检测 OS 暗色模式，自动切换主题
- **备份系统升级**: 使用 `sqlite3.backup()` API，透明处理 WAL 模式
- **搜索增强**: DOI 优先去重 + URL 规范化去重 + 加权排序 + per-source 超时控制
- **引文验证**: 4 层验证 (arXiv ID/DOI/URL/标题)，自动移除伪造引文

### 修复
- **Agent 404 错误**: PyInstaller 打包时未包含 agent 模块，添加 hidden imports
- **Agent 阻塞事件循环**: 所有 Agent 添加 `asyncio.to_thread()` 包装同步调用
- **Writing AI 错误处理**: 后端增加模型检查 + 前端增加错误显示
- **搜索 base_url 自动补全**: 自动补全 `/v1` 后缀，避免 404 错误

### 新增 API 端点
- `/api/agent/run` — 运行科研 Agent (review/writing/experiment/peer_review/debate)
- `/api/agent/workflows` — 列出所有 Agent 工作流
- `/api/agent/debug/models` — 调试：查看 AI 模型配置
- `/api/agent/debug/test` — 调试：测试 AI 连接
- `/api/knowledge/tags/tree` — 获取标签层级树结构

### 新增文件
- `app/ai/agents/` — Agent 模块 (workflow/review/writing/experiment/peer_review/debate)
- `app/ai/mcp_client.py` — MCP 协议客户端基础实现
- `nexus-ui/src/pages/ResearchAgentPage.tsx` — 科研 Agent UI 页面

## v3.4.1 (2026-06-21) — 播放同步 + Word Hopper + Bug修复

## v3.4.1 (2026-06-21) — 播放同步 + Word Hopper + Bug修复

### 修复
- 主窗口→时钟首次续播失败(添加_pendingResume机制+localStorage直接检查)
- 时钟→主窗口播放同步(读取clockPlaying状态+seek到正确位置)
- 时钟→主窗口延迟优化(立即读取currentTime)
- 主窗口播放器页面切换丢失(global audio singleton跨页面持久化)
- Word Hopper retry后键盘无响应(改用destroy+new重建)
- 游戏机模式语法错误(draw()缺少闭合大括号)

### 改进
- Word Hopper: 完整CET-6词汇库(A-Z共600+词)
- Word Hopper: 释义字体增大(15px bold)+词性标注(n./v./adj.)
- Word Hopper: Fisher-Yates随机洗牌+按长度分级
- 音乐播放器双向同步(BroadcastChannel+localStorage)
- 主窗口隐藏使用Tauri自定义事件(WebView2不支持visibilitychange)

## v3.4.0 (2026-06-20) — 讨论导出 + README生成 + 归档 + 模板

### 新增
- **对话导出**: AI对话可导出为Markdown文件(含thinking折叠)
- **README自动生成**: 从试验参数和结果自动生成README.md
- **试验归档打包**: 一键下载试验完整数据(JSON格式)
- **写作模板**: AIAA论文/IEEE论文/研究报告/文献综述四种模板

## v3.3.0 (2026-06-20) — 试验管理Git集成 + 知识库增强

### 新增
- **Git状态展示**: 试验项目显示分支、最近commit、未提交文件数
- **代码版本快照**: 每个结果版本可关联当前Git commit
- **结构化参数编辑**: 替代JSON textarea，动态键值对编辑
- **知识库增强搜索**: 排序(时间/标题/评分)、评分筛选、标签筛选
- **网格视图**: 知识卡片网格/列表视图切换
- **AI对话扩展**: 所有类型知识卡片都可发起AI分析

## v3.2.0 (2026-06-20) — 科研写作与文献增强

### 新增
- **写作工作台**: 三栏布局(文档列表+关联文献 | Markdown编辑器+实时预览 | AI助手面板)
- **AI写作助手**: 润色、翻译、扩写、精简、LaTeX格式转换、自定义指令
- **布尔检索**: 文献搜索支持AND/OR/NOT逻辑运算符
- **批量导入**: 搜索结果一键批量导入文献库(自动去重)
- **智能综述**: 支持自定义章节结构(可添加/删除/重排)
- **研究讨论模式**: AI对话新增"选题讨论"分类，内置结构化提示模板(研究空白/创新点/可行性/相关工作)
- **网页链接导入**: 知识库支持从网页URL导入内容(AI自动提取摘要)
- **多格式JSON导入**: 知识库支持ChatGPT/mimo/DeepSeek/ai-literature格式自动识别

### 改进
- **Markdown渲染**: AI对话升级为react-markdown + remark-gfm + remark-math + rehype-katex
- **代码高亮**: AI对话支持语法高亮(prism) + 一键复制代码块
- **聊天UI**: 消息入场动画、流式光标、thinking折叠块、工具调用状态图标
- **阅读器**: 支持EPUB/TXT/MD三种格式，修复EPUB解析器属性顺序兼容性
- **音乐播放器**: 主窗口与时钟窗口同步逻辑优化，BroadcastChannel即时通知

### 修复
- **Reader无内容**: 修复EPUB manifest解析器属性顺序不兼容导致章节为空
- **时钟播放器**: 修复BroadcastChannel处理器因变量提升导致失效
- **时钟播放器**: 修复播放/暂停图标状态不一致(轮询竞态条件)
- **时钟播放器**: 修复频谱可视化在自动续播时无法显示(AudioContext挂起)
- **FastAPI兼容性**: 降级FastAPI 0.115.0解决Starlette 1.x移除on_startup参数

## v3.1.0 (2026-06-20) — 音乐播放器无缝切换 + 懒加载优化 + Toast通知

### 改进
- 音乐播放器懒加载架构(元数据localStorage + 音频IndexedDB)
- 书架懒加载架构(元数据localStorage + 文件IndexedDB)
- Toast通知系统(成功/错误/信息)
- 主窗口隐藏时音乐自动切换到时钟播放器

## v3.0.0 (2026-06-19) — 个人助手(音乐/书架) + iOS UI + 自定义配色

### 新增
- 音乐播放器(唱片UI、频谱可视化、歌词显示)
- 书架(EPUB阅读器、书脊网格)
- iOS风格玻璃拟态UI
- 三套主题 + 自定义配色方案
- 时钟窗口游戏机模式(2048/Tetris/射击)
