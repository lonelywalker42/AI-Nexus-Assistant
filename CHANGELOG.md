# Changelog

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
