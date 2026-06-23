# Changelog

## v3.6.0 (2026-06-23)

### 游戏机模式扩展 + 复古像素 UI

**新增 4 款游戏（共 16 款）**
- Space Invaders（太空侵略者）：经典固定射击，外星人波次进攻
- Hextris（六边形方块）：旋转六边形，匹配同色方块消除
- Tower Stacking（叠塔游戏）：点击/按键堆叠方块，偏差会被切掉
- Pseudo-3D Racer（伪 3D 赛车）：复古街机风格赛车，加速/刹车/转向

**游戏机 UI 全面升级**
- CRT 扫描线效果：半透明扫描线叠加，还原复古显示器质感
- 霓虹绿主题色：标题、边框、LED 指示灯统一采用 #00ff41 霓虹绿
- 像素字体支持：优先加载 Press Start 2P / VT323 像素字体
- CRT 显示器边框：圆角边框 + 内发光 + 外发光模拟 CRT 显示器
- 动画 LED 指示灯：右上角呼吸灯效果
- 控制提示栏：底部显示 SELECT/START/ESC 控制说明

**参考来源**
- 调研报告：docs/GAME-CONSOLE-RESEARCH.md
- 设计系统：UI/UX ProMax Retro-Futurism + Pixel Art 风格

## v3.5.0 (2026-06-21)

### 科研助手功能增强（参考 ScholarAIO）

**Phase 1：基础能力增强**
- PDF 元数据自动提取：PyMuPDF 内置元数据 + 正则 + OpenAlex API 三级提取
- DOI 去重机制：优先按 DOI 去重，降级到标题匹配
- FTS5 全文索引：SQLite FTS5 虚拟表 + 自动同步触发器，替代 LIKE 查询
- 批量 BibTeX/RIS 导出：支持选择性导出
- 分层阅读：元数据 → 摘要 → 全文三层切换
- 阅读/搜索行为埋点：热词统计、高频阅读、阅读趋势

**Phase 2：智能检索升级**
- 向量语义搜索：sentence-transformers + FAISS
- RRF 混合搜索：FTS5 + 向量 RRF 融合排序（k=60）
- BERTopic 主题聚类：自动主题发现

**Phase 3：引用图谱**
- 引用关系解析：DOI 正则提取 + 正向/反向/共同引用
- 文内引用检查：Author (Year) 格式识别 + 库内验证

**Phase 4：高级功能**
- DOCX 导出：Markdown → DOCX 转换
- 工作区：论文子集管理

### 新增 API 端点
- `/api/papers/fts-search` — FTS5 全文搜索
- `/api/papers/hybrid-search` — 混合搜索
- `/api/papers/build-vectors` — 构建向量索引
- `/api/papers/export` — 批量导出
- `/api/topics` — 主题概览
- `/api/citations/*` — 引用图谱
- `/api/workspaces` — 工作区管理
- `/api/insights` — 研究洞察

## v3.1.0 (2026-06-19)

### 改进
- 音乐播放器：主窗口关闭时自动暂停，时钟播放器续放（无缝切换）
- 音乐/书架持久化改为懒加载架构：元数据存localStorage，音频/文件数据按需从IndexedDB加载
- EPUB阅读器：文字自适应窗口、主题继承、窗口resize响应
- 新增Toast通知系统（替代alert()）
- CSS新增骨架屏加载动画、页面过渡动画
- 书架openDetail按需加载文件

### Bug 修复
- 音乐播放进度同步修复：clock每1秒读取状态并显示
- 书架IndexedDB异步事务修复（同音乐修复方案）
- EPUB阅读器改用ArrayBuffer直接传入+spread:auto

## v3.0.0 (2026-06-19)

### Bug 修复
- 倒计时停止按钮：同时结束倒计时、回到时钟模式、恢复音乐播放
- 倒计时结束时自动暂停音乐，播放提示音；停止提示音后自动恢复音乐
- 文档更新：CLAUDE.md 新增开发维护全寿命周期体系

## v2.2.1 (2026-06-19)

### Bug 修复
- 时钟音乐播放器改用 webkitdirectory + IndexedDB 存储 ArrayBuffer
- 播放列表和提示音通过 IndexedDB 持久化，重启后自动恢复
- 移除不可用的 showDirectoryPicker 和 tauri-plugin-dialog

## v2.2.0 (2026-06-18)

### 时钟窗口音乐播放器
- 新增音乐播放器控件（上一首/播放/下一首/音量）
- Web Audio API 频谱可视化（Canvas 实时 FFT）
- 支持文件夹加载，按文件名排序
- 顺序播放 / 随机播放模式切换
- 拖拽音频文件到播放器
- 倒计时结束提示音 + 手动停止按钮
- IndexedDB 持久化（播放列表和提示音重启后自动恢复）
- 时钟窗口改为隐藏而非关闭，保留播放状态

### 数据备份修复
- 备份/恢复均处理 .db + .db-wal + .db-shm 三个文件
- 备份前执行 PRAGMA wal_checkpoint(FULL)
- 新增 ZIP 导出/导入功能（设置页面）

### web 搜索修复
- httpx 创建时 proxy=None 绕过本地代理（如 Clash）导致的 502 错误
- 搜索超时从 15s 增至 60s
- 搜索失败时告诉模型基于已有知识回答，不再循环重试
- 达到工具调用轮次上限后强制生成最终回复

### AI 对话改进
- 工具调用轮次的 thinking 不再显示给用户
- 消息格式兼容 DeepSeek（content 使用空字符串替代 null）
- 自动标题生成（≤10 字关键词提取）

### UI 优化
- 文献库详情面板宽度自适应
- 复制按钮增大点击区域
- 支持自定义应用名称（设置→个性化）

## v2.1.0 (2026-06-18)

### 新功能
- **今日工作**：每日任务同步、进度看板、工作日志、实时时钟
- **侧边栏重构**：总览 / 科研助手 / 个人助手 / 设置四大分组
- **文献检索 UI 升级**：统一搜索条、筛选面板、列表/网格视图切换
- **IDEA 随手记**：快速记录想法，关联 AI 对话分析
- **AI 对话分类**：通用 / 文献综述 / IDEA / 研究四类分组
- **应用重命名**：设置→个性化，自定义显示名称

### 修复
- 网络搜索：AI 阅读搜索结果并综合回答
- 托盘退出：taskkill /F /T 杀死完整进程树
- 构建脚本：open-webSearch 目录清理增加重试机制

## v2.0.0 (2026-06-17)

### 科研助手功能全面升级
- 文献库：PDF 导入、AI 元数据提取、引用格式（GB/T 7714/APA/IEEE/MLA/BibTeX）
- 试验管理：版本化记录、参数对比表、AI 分析
- AI 对话：流式输出、thinking 内容、@引用文献、工具调用（联网搜索）
- 知识库：标签系统、AI 生成卡片
- 仪表盘：数据总览、快捷入口

### 架构变更
- Tauri 2 + React 前端替代 PySide6
- FastAPI REST API（36+ 端点）
- SQLite WAL 模式

## v1.4.0 (2026-06-14)

- 深色日历主题
- 无 cmd 启动（sidecar 嵌入）
- 滚动隔离修复
- Web Search 集成

## v1.3.0 (2026-06-14)

- 待办日历 UI 重构
- 窗口重复创建修复
- 无色透明玻璃模式

## v1.2.0 (2026-06-13)

- 历史记录增强
- Markdown 渲染
- 数据库信息显示

## v1.1.0 (2026-06-13)

- 原生右键菜单
- 暖色主题
- AI 对话修复
