# LitKB 项目参考分析

> 基于 [LitKB](https://github.com/yuchen-zheng-eloxi/litkb) v2.6.11 的功能分析，提取对 AI Nexus Assistant 科研助手功能的参考价值。
>
> 分析日期：2026-06-23

---

## 一、项目概述

**定位**: LitKB (Literature Knowledge Base) 是一个**纯本地运行**的个人科研文献知识库工具，口号是 "Runs on YOUR machine. No cloud, no Docker, no account"。

**目标用户**: 材料/化学/物理/生物等需要大量阅读论文的科研工作者，尤其是中国用户（有完整中文用户手册）。

**设计理念**: 与 Zotero 互补而非竞争——做 Zotero 不擅长的事（检索+整理+AI），不做 Zotero 擅长的事（PDF阅读/高亮）。LitKB 明确定位为"检索+AI辅助整理"工具。

**当前版本**: v2.6.11，体积从 1.62GB 精简到 561MB。

---

## 二、核心功能列表

### 2.1 论文检索 (Home)

- 基于 OpenAlex API 的全球 2.4 亿篇论文实时搜索（免费、无需注册）
- 多字段多条件搜索（CNKI 风格）：6 个字段（摘要/标题/关键词/作者/期刊/DOI）
- 多行 AND/NOT 组合查询
- 摘要字段支持中英文互译（如"高熵合金"自动翻译为 "high entropy alloy"）
- 高级筛选：年份范围、是否 OA、最低引用数
- 3 种排序：相关性/高被引/最新
- arXiv API 作为补充源（OpenAlex 有 1-2 周延迟，arXiv 预印本约 3 天延迟）

### 2.2 我的库 (Library)

- 论文入库后可编辑元数据（标题/作者/期刊/年份，来自 OpenAlex 自动补全）
- 结构化笔记（v2.6.8 起 7 个字段）：key_question（关键问题）、methodology（方法）、main_result（主要结果）、my_review（评述）、concepts（关键概念）
- 自由标签系统
- 阅读状态：unread / reading / read / starred
- 单篇论文 AI 问答/总结
- 支持导入 .bib (BibTeX) / .ris (EndNote) / .csv / .tsv / .txt (DOI 列表)

### 2.3 集合管理 (Collections)

- 将相关论文归组，支持快捷建集合（输入关键词自动匹配 Library 内论文）
- 集合综述生成：LLM 通读论文后生成 3000-10000 字综述
  - v2.6.7+ 真实引用论文原文（不止 abstract）
  - v2.6.10 多 pass 提取：将论文拆为 3 段（abstract+intro / methods+results / discussion+conclusion）各跑 1 次 LLM，合并去重
- 综述长度按论文数动态调整（1-3 篇 300-500 字，50+ 篇 10000-15000 字）
- AI 率检测：LLM 自评综述的 AI 生成比例，返回 AI 率 + 命中特征 + 改进建议
- 知识库问答（RAG）：集合作为上下文，问 AI 综合问题
- 学习笔记：用户笔记可拼入 AI 对话上下文（15000 字上限）

### 2.4 研究课题 (Topics)

- 从集合中自动挖掘研究课题（LLM 驱动）
- 课题可手动编辑、改状态（待评估/进行中/已完成）
- 6 维深度分析：可行性/理论/实验计划/预期结果/风险/差异化
- 跨论文关联：关联 Library 中的关键文献
- 关键词引导研究：围绕用户指定关键词生成研究方向

### 2.5 趋势追踪 (Trends)

- 单篇论文引用曲线（输入 DOI/OpenAlex ID/标题）
- 关键词发文+引用热度趋势
- 数据来自 OpenAlex（免费）

### 2.6 PDF 处理

- 后台自动从 4 个源（arXiv/Unpaywall/Semantic Scholar/Crossref）抓取 PDF
- pypdf 解析为纯文本存入 DB 的 fulltext 字段
- 抓不到的用 abstract 兜底，标记 [no-fulltext]

### 2.7 LLM 配置

- 支持 DeepSeek / OpenAI / Ollama（本地免费）
- 协议按 URL 自动判断
- 测试连接 + 刷新模型列表
- 切换 LLM 不用重启
- Token 用量统计

---

## 三、技术架构

### 后端

- Python 3.10+ / FastAPI / SQLAlchemy (async) / SQLite (aiosqlite)
- Alembic 用于数据库迁移
- OpenAI SDK（统一调用 DeepSeek/OpenAI/Ollama）
- httpx 异步 HTTP 客户端
- pypdf 处理 PDF
- fastembed (ONNX) 替代 sentence-transformers（从 700MB+ 降到轻量级）
- chromadb 向量存储（可选，keyword-only 模式下可禁用）
- json-repair 库处理 LLM 输出的 JSON 解析
- arxiv 库作为论文搜索补充源
- loguru 日志

### 前端

- React 18 + TypeScript + Vite
- Ant Design 5（UI 组件库）
- Zustand（状态管理）
- React Router 6
- Axios（HTTP 客户端）
- dayjs（日期处理）
- zod（数据校验）

### 部署架构

- 纯本地运行，start.bat 一键启动
- 前端 dev server (localhost:5173) + 后端 uvicorn (localhost:8001)
- SQLite 单文件存储（data/litkb.db）
- 零 Docker / 零 Redis / 零 PostgreSQL

### 数据模型

- Paper — 论文元数据
- UserLibrary — 用户库中的论文（含笔记、标签、状态）
- Collection — 集合（主题分组）
- CollectionPaper — 集合-论文关联
- ResearchTopic — 研究课题
- Watchlist — 监控列表（趋势追踪）

---

## 四、特色功能（差异化特性）

### 4.1 多 pass 综述生成

- 将论文拆为 3 段分别用 LLM 提取，再合并去重，显著提高信息覆盖率（+18%）
- 这是其他工具少见的深度处理策略

### 4.2 AI 率检测

- 对 LLM 生成的综述进行自我检测，返回 AI 生成比例和改进建议
- 虽然准确度约 60-70%，但概念本身有实用价值

### 4.3 中英文互译搜索

- 摘要字段搜索时自动将中文翻译为英文（如"高熵合金" -> "high entropy alloy"）
- 对中国用户非常友好

### 4.4 研究课题 6 维深度分析

- 可行性/理论/实验计划/预期结果/风险/差异化
- 从文献集合中自动挖掘研究方向

### 4.5 趋势追踪

- 基于 OpenAlex 的引用曲线和发文热度分析
- 免费、无需注册

### 4.6 鲁棒的 LLM JSON 解析

- 配对括号计数 + 跳过字符串字面量 + json_repair 兜底
- 处理 LLM 输出中 <think> 思考链污染问题
- 这是实际工程中非常有价值的经验

### 4.7 schema drift 自动修复

- 启动时自动 ALTER TABLE ADD COLUMN，无需 Alembic 手动迁移
- 与 AI Nexus Assistant 的 `_migrate_columns()` 策略类似

---

## 五、对 AI Nexus Assistant 的参考价值

### 5.1 可以借鉴的功能设计

| 功能 | LitKB 实现 | 建议借鉴方式 |
|------|-----------|-------------|
| **结构化笔记模板** | 7 字段（key_question/methodology/main_result/my_review/concepts） | 在文献库的 Paper 模型中增加结构化笔记字段，比当前的纯文本 notes 更有组织性 |
| **阅读状态管理** | unread/reading/read/starred | 为 Paper 增加阅读状态，方便追踪阅读进度 |
| **集合/主题分组** | Collection 将论文按研究主题归组 | 当前文献库缺少主题分组功能，可增加类似的知识集合 |
| **集合综述生成** | 多 pass 提取 + 动态长度 + 引用原文 | 可为文献搜索的 review 功能增加多 pass 策略，提高综述质量 |
| **中英文互译搜索** | 摘要搜索自动翻译中文关键词 | 在 LiteraturePage 搜索中增加自动翻译，对中文用户非常实用 |
| **趋势追踪** | OpenAlex 引用曲线 + 关键词热度 | 可作为文献库的增值功能，帮助用户追踪研究热点 |
| **AI 率检测** | LLM 自评综述的 AI 生成比例 | 可作为综述生成后的附加功能 |
| **研究课题挖掘** | 从集合中自动挖掘 + 6 维深度分析 | 可集成到知识卡片系统中，从用户积累的知识中发现研究方向 |

### 5.2 可以改进的用户体验

| 方面 | LitKB 做法 | AI Nexus Assistant 现状 | 改进建议 |
|------|-----------|----------------------|---------|
| **一键启动** | start.bat 双击即可，浏览器自动打开 | 需要手动启动 server.py + tauri dev | 已有 Tauri 桌面应用，体验更好；但可参考其 inspect.bat 的预检诊断思路 |
| **LLM 配置** | 独立设置页，支持测试连接、刷新模型列表、当前生效卡片 | SettingsPage 中的模型配置 | 可增加"测试连接"按钮，让用户立即验证 API key 是否有效 |
| **Token 用量统计** | 每次 LLM 调用都记录，设置页可查看 | 无 | 可增加 Token 用量统计，帮助用户控制成本 |
| **导入格式** | .bib / .ris / .csv / .tsv / .txt (DOI 列表) | PDF 导入 + DeepSeek 导入 | 可增加 .bib/.ris 批量导入，方便从 Zotero/EndNote 迁移 |
| **引用格式** | GB/T 7714 / APA / BibTeX | GB/T 7714 | 已支持，可考虑增加 APA/BibTeX 切换 |

### 5.3 技术实现上的启发

| 技术点 | LitKB 经验 | 对 AI Nexus Assistant 的启发 |
|--------|-----------|---------------------------|
| **LLM JSON 解析鲁棒性** | 配对括号计数 + 去 <think> 标签 + json-repair 库 | 当前 router.py 的 JSON mode 可参考其 `_parse_json_robust` 策略，特别是处理 reasoning model 的思考链输出 |
| **多 pass 信息提取** | 论文拆 3 段分别 LLM 提取再合并 | 可用于提高文献摘要/综述的信息覆盖率 |
| **schema drift 自动修复** | 启动时 ALTER TABLE ADD COLUMN | AI Nexus Assistant 已有 `_migrate_columns()`，思路一致 |
| **fastembed 替代 sentence-transformers** | ONNX 推理替代 PyTorch，体积从 700MB+ 大幅缩小 | 如果未来增加本地 embedding 功能，优先考虑 fastembed |
| **asyncio 协程任务** | 替代 Redis/arq 的后台任务方案 | 可用于文献批量处理、综述生成等耗时操作 |
| **OpenAlex API** | 免费、无需注册、2.4 亿篇论文 | 可作为现有 8 源搜索的补充源，覆盖面广且免费 |
| **crash 日志系统** | 完整 traceback 写入 crash.log + 进程启动时清空旧日志 | 可增强错误诊断能力 |
| **LLM thinking chain 处理** | 关闭 thinking（enable_thinking=False）避免输出污染 | 对 DeepSeek reasoner 等模型的输出处理有参考价值 |

### 5.4 LitKB 的局限性（AI Nexus Assistant 的优势）

| 方面 | LitKB | AI Nexus Assistant |
|------|-------|-------------------|
| **部署形态** | 浏览器访问 localhost，非原生应用 | Tauri 桌面应用，原生体验 |
| **PDF 阅读** | 不做 PDF 阅读，依赖 Zotero | 有 PDF 导入和元数据提取 |
| **搜索源** | 仅 OpenAlex + arXiv | 8 源学术搜索，覆盖面更广 |
| **工具集成** | 纯文献管理 | 集成 Todo/实验管理/知识卡片/AI对话/时钟等 6 大工具 |
| **联网搜索** | 无 | AI 对话支持工具调用 + 联网搜索 |
| **实验管理** | 无 | 完整的实验管理系统 |
| **知识卡片** | 无独立知识卡片系统 | 知识卡片 + 标签系统 |
| **DeepSeek 导入** | 无 | 支持 DeepSeek 对话批量导入为知识卡片 |

---

## 六、总结

LitKB 是一个定位清晰、功能聚焦的文献管理工具，其核心价值在于：

1. **OpenAlex 集成** — 免费搜索全球 2.4 亿篇论文
2. **AI 深度加工** — 多 pass 综述、研究课题挖掘、6 维分析
3. **极致简洁** — 零依赖部署，SQLite 单文件

对 AI Nexus Assistant 而言，最值得借鉴的是：

- **结构化笔记模板** — 提升文献阅读笔记的组织性
- **中英文互译搜索** — 对中文用户非常实用
- **集合/主题分组** — 文献按研究主题归组
- **OpenAlex 作为搜索补充源** — 覆盖面广且免费
- **LLM JSON 解析的鲁棒性处理** — 处理 reasoning model 输出

AI Nexus Assistant 在工具集成度、桌面应用体验、多源搜索覆盖面上已有明显优势，补上文献深度整理和 AI 辅助分析的能力后，将形成更完整的科研助手生态。

---

## 七、改进路线图建议

### Phase 1：文献管理增强（短期）

| 任务 | 优先级 | 预估工作量 |
|------|--------|-----------|
| 结构化笔记模板（5字段） | P0 | 2h |
| 阅读状态管理（unread/reading/read/starred） | P0 | 1h |
| 中英文互译搜索 | P1 | 3h |
| .bib/.ris 批量导入 | P1 | 4h |

### Phase 2：AI 辅助分析（中期）

| 任务 | 优先级 | 预估工作量 |
|------|--------|-----------|
| 集合/主题分组功能 | P1 | 4h |
| 多 pass 综述生成 | P1 | 6h |
| AI 率检测 | P2 | 2h |
| 研究课题挖掘 | P2 | 6h |

### Phase 3：数据源扩展（中期）

| 任务 | 优先级 | 预估工作量 |
|------|--------|-----------|
| OpenAlex API 集成 | P1 | 4h |
| 趋势追踪（引用曲线） | P2 | 4h |
| Token 用量统计 | P2 | 3h |

### Phase 4：技术优化（长期）

| 任务 | 优先级 | 预估工作量 |
|------|--------|-----------|
| fastembed 本地 embedding | P2 | 4h |
| LLM JSON 解析增强 | P1 | 2h |
| crash 日志系统 | P2 | 2h |
