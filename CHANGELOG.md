# Changelog

## v4.5.1 (2026-06-24) — 五子棋 AI 引擎全面升级

### 改进
- **五子棋 AI 引擎重构**: 基于深度调研结果，全面升级 AI 算法架构
  - **7 档 AI 难度** (原 5 档):
    - LV.1 RANDOM — 随机落子（入门）
    - LV.2 GREEDY — 贪心威胁评估（简单）
    - LV.3 DEFEND — 贪心 + 即时胜负检测（普通）
    - LV.4 THINKER — Minimax 深度 2 + Alpha-Beta 剪枝（困难）
    - LV.5 EXPERT — 迭代加深搜索 2 秒 + 置换表 + History Heuristic（专家）
    - LV.6 MASTER — VCF 杀棋搜索 + 迭代加深 3 秒（大师）
    - LV.7 HELL — VCF+VCT 威胁空间搜索 + 迭代加深 5 秒（地狱）
  - **核心技术**: Zobrist 哈希置换表、History Heuristic 走法排序、精细化 pattern 评估函数
  - **VCF/VCT**: Victory by Continuous Four/Three 威胁空间搜索，检测强制获胜路径
  - 帮助界面显示所有难度说明 + 选中高亮 + 每级胜率统计
- **对弈胜率统计**: localStorage 存储每级难度的胜/负/平记录和胜率，游戏结束和帮助界面均可查看
- **工作归档页面**: 新增总览-工作归档页面，按周查看每日已完成任务、AI 日报、工作总结
  - 左上: 带 ISO 周数标签的月历导航
  - 右上: 最近 20 周活跃度热力图
  - 下方: 7 天归档卡片（已完成任务 + AI 日报 + 今日总结）

## v4.5.0 (2026-06-24) — 新增两款游戏

### 新功能
- **五子棋 (GOMOKU)**: 15×15 棋盘，玩家(黑) vs AI(白)，支持鼠标点击和键盘操作
  - **5 档 AI 难度**:
    - LV.1 RANDOM — 随机落子
    - LV.2 GREEDY — 贪心威胁评估（移植参考项目 `1<<k` 威胁评分算法）
    - LV.3 DEFEND — 贪心 + 即时胜负检测 + 防守优先
    - LV.4 THINKER — Minimax 深度 2 + alpha-beta 剪枝
    - LV.5 MASTER — Minimax 深度 4 + 完整 pattern 评估（活四/冲四/活三等）
  - 帮助界面按 D 键切换难度，棋盘星位标记，最后落子红点标记，AI 思考动画
  - 参考算法: [RainbowRoad1/Cgame/Five-in-a-row](https://github.com/RainbowRoad1/Cgame/tree/master/Five-in-a-row)
- **走迷宫 (MAZE)**: 递归回溯法生成迷宫，从入口走到 ◆ 出口
  - 关卡递进: 每通关一关迷宫尺寸增大（11×11 → 31×31），计时+步数双重评分
  - 参考算法: [RainbowRoad1/Cgame/Maze](https://github.com/RainbowRoad1/Cgame/tree/master/Maze)
- **游戏总数从 16 增至 18**，主窗口个人助手-游戏机 + 时钟窗口右键菜单均可访问

## v4.4.5 (2026-06-24) — Bug 修复

### Bug 修复
- **删除卡片后标签计数未同步**: `delete_card` 和 `delete_import_group` 删除卡片时仅删除 `CardTag` 关联，未递减 `Tag.usage_count`，导致已删除卡片的标签仍然存在且计数不准确
- **孤立标签清理**: 新增 `cleanup_orphan_tags` 服务 + `/api/knowledge/tags/cleanup` 端点，IDEA 页面加载时自动重新计算标签引用数，删除无引用标签
- **导入分组删除精确计数**: `delete_import_group` 改为先收集受影响标签再删除，最后按实际引用数精确修正 `usage_count`

## v4.4.4 (2026-06-24) — 性能优化 + 稳定性修复

### 性能优化
- **list_cards 端点 N+1 查询优化**: 将逐卡片查询标签改为单次批量查询，324 张卡片响应时间从 0.19s 降至 0.003s（**54 倍提速**）

### 稳定性修复
- **前端 loadCards() 重试机制**: 添加 `fetchWithRetry` 包装，最多重试 3 次，指数退避（500ms → 1s → 2s），避免单次请求失败即永久显示"网络连接失败"
- **request() 双保险超时**: `AbortSignal.timeout()` + `Promise.race` 兜底机制，解决部分 WebView2 版本 AbortSignal 兼容性问题
- **错误识别增强**: 新增 `AbortError` 和 `Load failed` 错误类型识别

## v4.4.3 (2026-06-24) — Bug 修复

### Bug 修复
- **IDEA 页面 DeepSeek 导入后所有卡片不显示**: 修复导入完成后未显式调用 `loadCards()` 刷新卡片列表的 Bug — useEffect 依赖数组不含 `activeCategory`，且 filter 值若已是默认值则不触发重载，导致 `allCards` 停留在旧数据，新导入的 DeepSeek 卡片不在 AI 对话分类中显示
- **请求无超时导致"网络连接失败"**: `request()` 函数的 `fetch()` 调用无超时机制，324+ 卡片 × N+1 标签查询可导致响应缓慢，请求挂起后前端误报网络错误；添加 30 秒 `AbortSignal.timeout` 防挂起
- **GET 请求多余的 Content-Type 头**: `request()` 对所有请求统一设置 `Content-Type: application/json`，GET 请求无需此头，可能触发代理兼容问题

## v4.4.2 (2026-06-24) — Bug 修复

### Bug 修复
- **IDEA 页面卡片加载 500 错误**: 修复 `server.py` 中 `list_cards` 端点使用 `t.tag_name` 访问 `Tag` 对象导致 `AttributeError`，所有知识卡片（文献/AI对话/手动/随手记/网页）无法加载，前端误显示为"网络连接失败"
- **游戏机键盘事件监听器累积**: 修复 Game2048/Invaders/Hextris/Tower/Racer 等游戏按 R 重启时 `init()` 被多次调用但未移除旧的 keydown 监听器，导致单次按键触发多个方块/操作

## v4.4.1 (2026-06-24) — Bug 修复 + 开发者文档

### Bug 修复
- **DOCX 导出中文乱码**: 重写 `export_docx()` — 设置东亚字体（宋体）、行内格式解析（粗体/斜体/代码/链接）、标题/列表格式正确渲染
- **文献库 PDF 拉取 "failed to fetch"**: `extract_pdf_metadata()` 包裹 try-except 失败不阻断入库；`_paper_to_dict` 增加 None 兜底；前端错误信息区分网络层/API 层
- **TodayPage 按钮配色**: "AI 整理"和"添加"按钮从 `btn-primary` 统一为 `btn-gradient`
- **IDEA 按钮文字换行**: "DeepSeek 智能导入"按钮改为 `btn-gradient` + `whitespace-nowrap`

### 文档
- **开发者环境配置指南**: 新增 `docs/DEV-SETUP.md`（527 行），含架构图、系统要求、Submodule 配置、各平台说明、构建流程、版本号同步清单、常见问题排查
- **依赖补全**: README.md / CLAUDE.md 补充 `httpx`、`python-docx` 安装说明

## v4.4.0 (2026-06-24) — Bug 修复 + UI 设计语言规范化

### Bug 修复
- **Mines hard 模式崩溃**: 修复按 D 切换难度后网格数组未重新初始化导致游戏无响应的 Bug
- **DeepSeek 导入后卡片不显示**: 修复导入完成后竞态条件（两个并发请求）和轮询错误静默吞掉的问题
- **PDF 拉取 422 错误**: 移除 `proxy=None` 硬编码，改为尊重系统代理设置（与 ScholarAIO 一致）；错误状态码从 422 改为 502
- **非功能性按钮**: 移除 LiteraturePage 中无 onClick 的"在线检索"占位按钮

### UI 设计语言规范化
- **设计语言文档**: 新增 `docs/DESIGN_LANGUAGE.md`，定义色彩、排版、圆角、间距、阴影、动画、图标、组件规范
- **emoji 图标替换**: 全面替换页面标题/按钮中的 emoji 为 SVG 图标组件（Icons.tsx 新增 7 个图标）
  - ResearchAgentPage: 🤖→IconBrain, 📚→IconBook, ✍️→IconEdit, 🧪→IconFlask, 📝→IconClipboard, 💬→IconChat
  - KnowledgePage: 📊→IconChart, 🧠→IconBrain, ☰→IconList, ⊞→IconGrid, 📁→IconFolder, 📂→IconFolder
  - PaperLibraryPage: 📥→IconDownload, 📄→IconFile, 📚→IconBook, 📋→IconClipboard, 🔍→IconSearch, 📝→IconEdit, 🔗→IconLink, 🔄→IconRefresh
  - TodayPage: ✅→IconCheck, ⚠️→IconWarning, 📋→IconClipboard, 📊→IconChart, ✨→IconSparkle
  - ChatPage: 🔍→IconSearch, 🔄→IconRefresh, 💭→IconBrain, 📊→IconChart, ✅→IconCheck
  - SettingsPage: 🌸→IconSun, 📖→IconBook
  - ResearchAgentPage: ⏳→IconClock, ✅→IconCheck, ❌→IconX
- **圆角系统统一**: CSS 设计令牌 `--radius-card` 从 20px 调整为 16px，`--radius-element` 从 14px 调整为 12px
- **阴影系统精简**: 阴影值统一为设计语言规范（极淡阴影，仅弹出层使用）

### 新增图标组件
- `IconWarning` — 警告三角形
- `IconRefresh` — 刷新/重试
- `IconDownload` — 下载
- `IconLink` — 链接
- `IconDocument` — 文档
- `IconHash` — 井号/标签

### 文件变更
- `nexus-ui/public/games.html`: Mines 难度切换修复
- `nexus-ui/src/pages/KnowledgePage.tsx`: 轮询错误处理 + 竞态修复 + emoji 替换
- `nexus-ui/src/pages/PaperLibraryPage.tsx`: 错误信息优化 + emoji 替换
- `nexus-ui/src/pages/ChatPage.tsx`: emoji 替换
- `nexus-ui/src/pages/ResearchAgentPage.tsx`: emoji 替换
- `nexus-ui/src/pages/TodayPage.tsx`: emoji 替换
- `nexus-ui/src/pages/SettingsPage.tsx`: emoji 替换
- `nexus-ui/src/pages/LiteraturePage.tsx`: 移除非功能性按钮
- `nexus-ui/src/components/Icons.tsx`: 新增 7 个图标组件
- `nexus-ui/src/styles.css`: 圆角/阴影设计令牌更新
- `app/services/pdf_fetch.py`: 代理处理改为尊重系统代理
- `server.py`: PDF 拉取错误状态码修正
- `docs/DESIGN_LANGUAGE.md`: 设计语言规范文档

## v4.3.8 (2026-06-24) — SpringNote P0-P2 全面改进

### 新功能
- **AI 结构化日报 (P0-5.1.1)**: TodayPage 新增「快速想法」输入区，用户输入自然语言，AI 自动解析为完成事项/问题记录/明日计划三栏结构化内容，存储在 localStorage
- **结构化概览卡片 (P1-5.1.4)**: TodayPage 进度条下方展示三栏概览（✅完成/⚠️问题/📋计划），数据来自 AI 整理结果
- **自动周报摘要 (P1-5.1.2)**: TodayPage 自动汇总本周所有日报，展示完成项和遗留问题统计
- **活跃度热力图 (P1-5.1.3)**: Dashboard 和 TodayPage 新增 GitHub 贡献风格热力图（140天/20周），5级绿色渐变，悬停 tooltip
- **SpringNote 仿色主题**: 新增 `[data-theme="spring"]` 樱粉配色方案
- **标签着色系统**: djb2 哈希 + 12 色调色板，全局一致着色
- **标签点击过滤**: 知识卡片标签可直接点击过滤
- **工具调用结果展开**: AI 对话搜索结果可展开全部

### UI 改进 (P1/P2)
- **按钮尺寸统一 (P0-5.3.1)**: 新增标准化按钮系统 — `btn-primary`(黑色胶囊)、`btn-ghost`(透明边框)、`btn-icon`(34x34px)、`btn-danger`(红底)，所有按钮统一 32px 高度 + 999px 圆角
- **卡片样式简化 (P1-5.2.1)**: 玻璃卡片移除默认阴影（`box-shadow: none`），hover 时极淡阴影 `0 4px 30px rgba(0,0,0,0.06)`
- **排版优化 (P1-5.2.2)**: 主字体切换为 Inter，启用 `font-feature-settings: 'tnum' on`（tabular figures）
- **动画精炼 (P2-5.2.3)**: 统一缓动曲线为 `ease-out-cubic`(0.33,1,0.68,1)，微交互缩短至 120ms，FAB 脉冲动效移除改为静态柔和阴影
- **阴影规范 (P2-5.2.4)**: 持久内容（卡片/面板）无阴影，仅弹窗/浮动层使用阴影

### 修复
- **主题切换闪烁**: `theme-transitioning` CSS 类实现 0.3s 平滑过渡
- **综述池数量提示**: 超 20 篇显示「最多取前 20 篇」
- **API 错误提示增强**: 429/401/超时/5xx 分类提示 + 重试建议

### 文件变更
- `nexus-ui/src/styles.css`: Inter 字体 + 标准化按钮系统 + 动画/阴影规范 + spring 主题
- `nexus-ui/src/utils/tagColors.ts`: 标签哈希着色
- `nexus-ui/src/pages/TodayPage.tsx`: AI 结构化日报 + 结构化概览 + 周报摘要 + 热力图
- `nexus-ui/src/pages/Dashboard.tsx`: 活跃度热力图
- `nexus-ui/src/pages/SettingsPage.tsx`: 春日主题按钮
- `nexus-ui/src/pages/KnowledgePage.tsx`: 标签着色 + 点击过滤
- `nexus-ui/src/pages/PaperLibraryPage.tsx`: 标签着色
- `nexus-ui/src/pages/ChatPage.tsx`: 工具结果展开 + 错误提示
- `nexus-ui/src/pages/LiteraturePage.tsx`: 综述池提示 + 错误提示

## v4.3.6 (2026-06-23) — 游戏机修复 + 写作导出 + 去重增强 + UI统一

### 修复
- **Pong首次失分卡死**: 修复球出界后 respawn 逻辑使用索引赋值导致数组错位 — 改用 push 方式 respawn，AI 追踪增加空值保护
- **Flappy Bird障碍间距**: 管道生成间隔从200帧增至250帧，垂直间隙从150px增至160px，间隙生成范围优化
- **Pac-Man ESC退出（补丁）**: game over 状态缺少 Escape 键处理 — 补充 `if (e.key === 'Escape') { backToMenu(); return; }`
- **Racer无行驶车辆（补丁）**: 障碍物从 dist=0 生成导致首帧不可见 — 改为 dist=-0.5；移速公式 `(speed+80)` 去掉 +80 基础值，使障碍物仅在玩家加速时逼近
- **Mines hard模式无响应（补丁）**: help 界面 handleKey 仅处理 D/Escape，其余按键直接 return — 补充任意键 dismiss help 并启动游戏循环
- **IDEA卡片显示（补丁）**: API 返回数据增加 Array.isArray 防御性检查；错误信息细化（区分后端未就绪 vs API 错误），方便定位问题
- **引用按钮UI统一（补丁）**: "复制"/"修正引用" 按钮移除 min-w-[52px] 固定宽度，改用 whitespace-nowrap 自适应文字宽度
- **写作导出无响应（补丁）**: 导出下拉菜单从 CSS group-hover 改为 click 状态切换 + 点击外部关闭，兼容 Tauri WebView2
- **DeepSeek导入去重（补丁）**: 导入完成后自动调用 deduplicate_sessions("import") 清除历史对话中的标题重复项
- **UI一致性修复**: SettingsPage 按钮补全 text-xs；玻璃卡片标题统一为 text-sm font-semibold；硬编码颜色替换为 CSS 变量
- **PDF拉取错误信息**: 优化 422 错误提示，提供 4 种具体操作建议（校园网/手动下载/Sci-Hub/作者主页）

### 新功能
- **写作导出功能**: 写作工作台新增"导出"按钮，支持 Markdown 和 DOCX 两种格式
- **导出含文献引用**: 导出时自动附加关联文献的 GB/T 7714 引用格式参考文献列表
- **DeepSeek去重增强**: 五重去重机制（标题精确/标题模糊0.70/内容哈希/source_url/消息数+标题相似度），显著降低重复导入概率

### 文件变更
- `nexus-ui/public/games.html`: Pong respawn + Flappy间距 + Pac-Man ESC + Racer障碍
- `nexus-ui/src/pages/KnowledgePage.tsx`: loading/error 状态管理
- `nexus-ui/src/pages/PaperLibraryPage.tsx`: DOI 按钮样式统一
- `nexus-ui/src/pages/WritingPage.tsx`: 导出按钮 + Markdown/DOCX 下载
- `nexus-ui/src/api/client.ts`: writingApi.exportDoc API
- `app/services/deepseek_import_service.py`: 五重去重逻辑
- `app/services/pdf_fetch.py`: 错误信息优化
- `server.py`: /api/writing/documents/{id}/export 端点
- 版本号同步: tauri.conf.json, Cargo.toml, client.ts, server.py, CLAUDE.md

## v4.3.5 (2026-06-23) — PDF多源拉取 + IDEA修复 + 游戏机增强 + 字体主题

### 新功能
- **PDF多源拉取**: 新增Semantic Scholar API、Crossref全文链接、Sci-Hub镜像三个fallback源，显著提升PDF下载成功率
- **DeepSeek导入内容哈希去重**: 新增MD5内容哈希比对（前3条用户消息），即使标题不同也能检测重复对话
- **对话历史去重**: AI对话页新增"去重"按钮，自动检测并删除标题重复的历史会话（保留最新）
- **字体大小调整**: 设置页自定义主题新增"字体大小"选项（小11px/中13px/大15px），全局联动
- **Pong 7关卡多球**: 新增7级难度系统，每级增加一个球，AI速度递增，球速递增，多球独立运动
- **SpringNote参考文档**: 新增SpringNote开源项目分析文档，提取日程/日报UI改进方案

### 修复
- **IDEA卡片显示**: 修复DeepSeek导入后其他分类卡片无法显示的问题 — 导入完成后重置activeCategory过滤器，分类计数使用未过滤的全量卡片数据
- **Minesweeper数字对齐**: 修复hard模式下数字与方块位置偏移 — 添加textBaseline='middle'，居中绘制坐标
- **Flappy障碍间距**: 管道生成间隔从150帧增至200帧，垂直间隙从140px增至150px
- **Racer障碍增强**: 障碍生成间隔从120帧降至80帧，速度阈值从20降至10，车辆尺寸增大1.5x，颜色扩展至10种
- **引用按钮UI统一**: 修正引用按钮添加min-w-[52px]，三个控件统一h-[28px] leading-none

### 改进
- **DeepSeek去重误导信息**: 全部对话被去重时显示"所有对话已存在，无需重复导入"而非"无有效消息"
- **Minesweeper textBaseline**: 所有数字和地雷符号显式设置textBaseline='middle'确保跨平台一致性

### 文件变更
- `app/services/pdf_fetch.py`: 新增_try_semantic_scholar/_try_crossref_fulltext/_try_scihub三个fallback函数
- `app/services/deepseek_import_service.py`: 内容哈希去重 + 去重计数返回 + 错误信息改进
- `app/services/chat_service.py`: 新增deduplicate_sessions函数
- `server.py`: 新增POST /api/chat/sessions/deduplicate端点
- `nexus-ui/src/api/client.ts`: 新增deduplicateSessions API
- `nexus-ui/src/pages/KnowledgePage.tsx`: allCards状态 + activeCategory重置
- `nexus-ui/src/pages/ChatPage.tsx`: 去重按钮
- `nexus-ui/src/pages/PaperLibraryPage.tsx`: 引用按钮尺寸统一
- `nexus-ui/src/pages/SettingsPage.tsx`: 字体大小设置UI
- `nexus-ui/src/styles.css`: --font-size-base CSS变量 + 7处硬编码替换
- `nexus-ui/src/App.tsx`: 字体大小初始化
- `nexus-ui/public/games.html`: Minesweeper对齐 + Flappy间距 + Pong多球 + Racer障碍增强
- `docs/SPRINGNOTE_REFERENCE.md`: SpringNote开源项目分析文档

## v4.3.4 (2026-06-23) — PDF拉取增强 + DeepSeek导入优化 + 游戏机修复

### 新功能
- **DeepSeek导入去重**: 导入对话JSON时自动检测重复会话（标题相似度>0.85或source_url匹配），避免重复创建卡片和会话
- **手动摘要生成**: DeepSeek导入失败的会话卡片显示"生成摘要"按钮，支持逐个手动重新生成AI摘要
- **DeepSeek对话直接展示**: IDEA页面"AI 对话"分类改为直接展示卡片列表，不再嵌套导入分组；对话页导入会话直接显示在列表中
- **Minesweeper难度选择**: 新增易/中/难三档（9×9/10雷、12×12/20雷、16×16/40雷），帮助界面按D键切换
- **Pong难度递增**: 每2分钟AI速度+0.5、球速+8%，底部显示LV指示器
- **Racer对向来车**: 新增随机车道来车障碍物，透视缩放绘制，碰撞检测触发游戏结束

### 修复
- **PDF拉取失败增强**: 新增iframe/embed标签解析、10+出版社专用URL模式（ScienceDirect/Springer/Wiley/IEEE/ACM/Nature等）、多User-Agent轮换重试
- **引用按钮UI统一**: 引用格式选择器、复制按钮、修正引用按钮的宽高和内边距调整为与页面其他按钮一致（text-[10px] py-1 px-2）
- **游戏菜单鼠标偏移**: 修复mousemove/click处理器使用旧常量导致点击位置与实际游戏槽位不一致的问题
- **游戏存档显示错误**: 修复存档时间始终显示当前时间的bug（timestamp读取路径错误）
- **游戏存档覆盖**: 修复在恢复存档界面按ESC时用未初始化数据覆盖真实存档的问题
- **存档事件监听器泄漏**: 修复恢复存档界面的mousemove监听器未被正确移除的问题
- **Breakout关卡速度**: 修复过关后球速递增被硬编码覆盖的bug，改用lvlSpd公式按关卡递增
- **Minesweeper retry**: 游戏结束画面新增可点击的[RESTART]按钮，支持鼠标点击重试
- **Flappy障碍间距**: 管道生成间隔从90帧增至150帧，管道速度从120降至100 px/s
- **Pong墙壁反弹**: 改用Math.abs+位置钳制防止球卡在边界振荡

### 改进
- **DeepSeek导入并发降级**: LLM批处理并发数从5降至2，避免API过载
- **Racer游戏性**: 从纯驾驶演示升级为有障碍物碰撞的完整游戏

### 文件变更
- `app/services/pdf_fetch.py`: PDF链接提取增强 + 多UA重试
- `app/services/deepseek_import_service.py`: 去重机制 + 并发降级 + 手动摘要再生
- `server.py`: 新增regenerate-summary端点
- `nexus-ui/src/api/client.ts`: 新增regenerateSummary API
- `nexus-ui/src/pages/PaperLibraryPage.tsx`: 引用按钮UI统一
- `nexus-ui/src/pages/KnowledgePage.tsx`: 导入后重置过滤器 + 直接展示卡片 + 手动摘要按钮
- `nexus-ui/src/pages/ChatPage.tsx`: 导入会话直接展示
- `nexus-ui/public/games.html`: 10项游戏修复

## v4.3.3 (2026-06-23) — PDF拉取增强 + AI对话批量删除 + DeepSeek导入优化

### 新功能
- **AI对话批量删除**: 新增批量选择模式、全选/取消全选、按分类清空对话功能
- **PDF拉取增强**: 新增Crossref标题→DOI查询、5种PDF链接提取模式（meta标签/link标签/锚点/JavaScript重定向/正则）、改进错误提示
- **DeepSeek导入分批处理**: LLM摘要生成改为分批次处理（每批5个），等待上一批次完成后再处理下一批次，避免API过载
- **关联对话跳转**: IDEA卡片列表和网格视图新增关联对话图标按钮，点击可跳转到对应AI对话
- **应用介绍产品化**: 更新About弹窗中的应用介绍为更专业的产品化描述

### 修复
- **对话跳转失败**: 修复从知识卡片点击"查看关联对话"后无法跳转的问题 — 添加hashchange监听器和initialSessionId参数传递
- **IDEA卡片显示**: 修复关联对话图标在列表视图中不显示的问题

### 改进
- **LitKB参考分析**: 新增LitKB项目功能分析文档，提取结构化笔记、中英文互译搜索、集合分组等功能参考
- **错误提示优化**: PDF拉取失败时提供更详细的解决建议（校园网、代理、登录等）

### 文件变更
- `app/services/pdf_fetch.py`: Crossref查询 + PDF链接提取增强
- `app/services/deepseek_import_service.py`: 分批处理LLM任务
- `server.py`: 批量删除对话API
- `nexus-ui/src/api/client.ts`: 批量删除API客户端
- `nexus-ui/src/App.tsx`: hash跳转监听
- `nexus-ui/src/pages/ChatPage.tsx`: 批量删除UI + 初始会话加载
- `nexus-ui/src/pages/KnowledgePage.tsx`: 关联对话图标
- `nexus-ui/src/components/Sidebar.tsx`: 产品化应用介绍
- `docs/LITKB_REFERENCE.md`: LitKB项目参考分析文档

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
