# ScholarAIO 参考分析与改进方案

> 基于 [ScholarAIO](https://github.com/ZimoLiao/scholaraio) v1.5.0 的功能分析，制定 AI Nexus Assistant 科研助手功能改进路线图。
>
> 分析日期：2026-06-21

---

## 一、项目定位对比

| 维度 | ScholarAIO | AI Nexus Assistant |
|------|-----------|-------------------|
| **定位** | AI Agent 科研基础设施（CLI + Skills） | 桌面科研助手（PySide6 + Tauri） |
| **交互方式** | Claude Code / Codex 等 AI Agent 驱动 | GUI + AI Chat 混合交互 |
| **目标用户** | 深度使用 AI coding agent 的研究者 | 航空航天/控制领域研究者 |
| **技术栈** | Python CLI + Markdown Skills | Python 后端 + React/TypeScript 前端 |
| **数据存储** | 文件系统 + SQLite（index.db） | SQLAlchemy ORM + SQLite（nexus.db） |
| **分发方式** | pip install + git clone | 单 exe 可执行文件（~51MB） |

**核心差异**：ScholarAIO 是 **agent-first** 设计，所有功能通过 Claude Code skills 路由；AI Nexus Assistant 是 **GUI-first** 设计，AI 作为辅助工具嵌入。两者可以互补——将 ScholarAIO 的底层能力移植到 AI Nexus Assistant 的 GUI 框架中。

---

## 二、功能差距分析

### 2.1 PDF 解析（深度结构提取）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| PDF → Markdown 转换 | ✅ MinerU（本地/云端）+ Docling + PyMuPDF 三级降级 | ❌ 仅存储 PDF 文件路径，无解析 | **重大缺失** |
| 公式保留 | ✅ MinerU 支持 LaTeX 公式提取 | ❌ | 缺失 |
| 图片提取 | ✅ 自动提取并重写 Markdown 引用 | ❌ | 缺失 |
| 长文档分块 | ✅ >100 页自动分片合并 | ❌ | 缺失 |
| Office 文档支持 | ✅ MarkItDown 支持 DOCX/PPTX/XLSX | ❌ | 缺失 |

**改进方案**：
- **P0（高优先级）**：集成 MinerU 作为 PDF 解析引擎，支持本地 API 和云端两种模式
- **P1**：实现 PyMuPDF 降级方案（无需外部服务）
- **P2**：支持 Office 文档导入（MarkItDown）

**参考实现**：`scholaraio/providers/mineru.py`, `scholaraio/providers/pdf_fallback.py`

---

### 2.2 混合搜索（关键词 + 语义融合）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| 全文检索 | ✅ SQLite FTS5 + BM25 排序 | ⚠️ SQLAlchemy LIKE 查询 | **需升级** |
| 向量语义搜索 | ✅ FAISS + Qwen3 嵌入 | ❌ embedding_id 字段存在但未使用 | **重大缺失** |
| 融合排序 | ✅ RRF（Reciprocal Rank Fusion, k=60） | ❌ 仅关键词匹配 | 缺失 |
| 分块搜索 | ✅ 按章节分块（~4800 字符），行级定位 | ❌ | 缺失 |
| 作者搜索 | ✅ LIKE 模糊匹配 | ⚠️ 在全文搜索中包含 | 可优化 |

**改进方案**：
- **P0**：为 Paper 和 KnowledgeCard 表添加 FTS5 虚拟表，替换 LIKE 查询
- **P1**：集成 sentence-transformers + FAISS 实现语义搜索
- **P1**：实现 RRF 融合排序算法
- **P2**：实现论文分块索引（按 Markdown 标题分段）

**参考实现**：`scholaraio/services/index.py`（FTS5 + RRF）, `scholaraio/services/vectors.py`（FAISS）, `scholaraio/services/chunks.py`（分块）

---

### 2.3 文献库管理（多源导入 + 元数据）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| PDF 导入 + 元数据提取 | ✅ 自动从 PDF 提取标题/作者/年份/DOI | ⚠️ 仅存储 PDF，需手动填写元数据 | **需改进** |
| DOI 去重 | ✅ 基于 DOI/专利号/arXiv ID 去重 | ⚠️ 仅按标题精确匹配去重 | 需改进 |
| 多源导入 | ✅ Zotero / EndNote / arXiv / 专利 | ⚠️ 仅从搜索结果导入 | 需扩展 |
| 元数据清洗 | ✅ 审阅式修复 + 已检查标记 | ❌ | 缺失 |
| 论文类型分类 | ✅ 期刊/会议/学位论文/专利/技术报告/标准/讲义 | ⚠️ paper_type 字段存在但未细分 | 可优化 |
| L3 结论提取 | ✅ LLM 自动提取结论章节 | ❌ | 缺失 |
| 目录结构提取 | ✅ LLM 提取 TOC 用于分块 | ❌ | 缺失 |

**改进方案**：
- **P0**：PDF 导入时自动提取元数据（使用 PyMuPDF + 正则 + LLM）
- **P0**：基于 DOI 的去重机制
- **P1**：支持 Zotero / EndNote 批量导入
- **P1**：LLM 自动提取论文结论（L3）和目录结构
- **P2**：元数据清洗审核界面

**参考实现**：`scholaraio/services/ingest/inbox_steps.py`（元数据提取）, `scholaraio/services/ingest/identifiers.py`（去重）, `scholaraio/providers/zotero.py`, `scholaraio/providers/endnote.py`

---

### 2.4 主题发现（Topic Discovery）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| 自动主题聚类 | ✅ BERTopic（UMAP + HDBSCAN + c-TF-IDF） | ❌ | **重大缺失** |
| 主题可视化 | ✅ 层次图/2D 散点/柱状图/热力图/时间线 | ❌ | 缺失 |
| 主题合并/调整 | ✅ 手动合并 + 自动 reduce | ❌ | 缺失 |
| 论文-主题关联 | ✅ 自动归组 + 语义近邻查找 | ❌ | 缺失 |

**改进方案**：
- **P1**：集成 BERTopic 实现自动主题聚类
- **P1**：在 Dashboard 添加主题概览可视化
- **P2**：支持主题合并和手动调整

**参考实现**：`scholaraio/services/topics.py`

---

### 2.5 引用图谱（Citation Graph）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| 正向引用（参考文献） | ✅ 解析 DOI 构建引用表 | ❌ | **重大缺失** |
| 反向引用（被引） | ✅ 反向查询 | ❌ | 缺失 |
| 共同引用分析 | ✅ 多篇论文共享引用 | ❌ | 缺失 |
| 文内引用检查 | ✅ 正则提取 + 库内验证 | ❌ | 缺失 |
| 引用样式 | ✅ 4 种内置 + 自定义 | ⚠️ 5 种格式（GB/T, APA, IEEE, MLA, BibTeX） | 可扩展 |

**改进方案**：
- **P1**：构建 citations 表，从论文 references 字段解析 DOI 建立引用关系
- **P1**：实现正向/反向引用查询
- **P2**：共同引用分析
- **P2**：文内引用验证（写作辅助）

**参考实现**：`scholaraio/services/index.py`（citations 表）, `scholaraio/services/citation_check.py`

---

### 2.6 研究洞察（Insights）

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| 热门关键词分析 | ✅ 搜索词频率统计 | ❌ | **缺失** |
| 高频阅读论文 | ✅ 阅读事件聚合 | ❌ | 缺失 |
| 阅读趋势 | ✅ 按周统计 | ❌ | 缺失 |
| 语义推荐 | ✅ 基于近期阅读推荐未读论文 | ❌ | 缺失 |

**改进方案**：
- **P1**：添加阅读/搜索行为埋点
- **P1**：Dashboard 展示热词、阅读趋势、推荐论文
- **P2**：基于向量相似度的论文推荐

**参考实现**：`scholaraio/services/insights.py`

---

### 2.7 多格式导出

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| BibTeX 导出 | ✅ 批量导出 | ⚠️ 单篇 BibTeX 格式 | 需扩展 |
| RIS 导出 | ✅ | ❌ | 缺失 |
| Markdown 参考文献列表 | ✅ 带引用样式 | ❌ | 缺失 |
| DOCX 导出 | ✅ Markdown → DOCX | ❌ | 缺失 |
| 工作区导出 | ✅ 论文子集导出 | ❌ | 缺失 |

**改进方案**：
- **P1**：批量 BibTeX/RIS 导出
- **P1**：Markdown 参考文献列表生成
- **P2**：DOCX 导出（python-docx）

**参考实现**：`scholaraio/services/export.py`

---

### 2.8 学术写作辅助

| 能力 | ScholarAIO | AI Nexus Assistant | 差距 |
|------|-----------|-------------------|------|
| 写作路由 | ✅ 按交付物/阶段自动路由 | ⚠️ Chat 中有写作模板 | 需结构化 |
| 文献综述 | ✅ 专用 skill + 长文生成 | ⚠️ LiteraturePage 有 review 功能 | 可增强 |
| 论文精读 | ✅ 引导式单篇深读 | ❌ | 缺失 |
| 审稿回复 | ✅ rebuttal 工作流 | ❌ | 缺失 |
| 研究空白分析 | ✅ research-gap skill | ⚠️ Chat 模板中有 | 可结构化 |
| 引用追溯 | ✅ 所有引用可追溯到本地文献库 | ❌ | 缺失 |
| 海报/技术报告 | ✅ 专用 skill | ❌ | 缺失 |

**改进方案**：
- **P1**：结构化写作工作流（文献综述、论文精读、审稿回复）
- **P1**：引用追溯——写作时自动关联本地文献库
- **P2**：海报/技术报告模板

**参考实现**：`skills/academic-writing/`, `skills/literature-review/`, `skills/paper-guided-reading/`, `skills/review-response/`

---

### 2.9 其他功能

| 功能 | ScholarAIO | AI Nexus Assistant | 优先级 |
|------|-----------|-------------------|--------|
| 远程备份（rsync） | ✅ | ⚠️ 本地 ZIP 备份 | P2 |
| 分层阅读 | ✅ 元数据→摘要→结论→全文 | ❌ | P1 |
| 联邦发现 | ✅ 主库 + 探索库 + arXiv 统一搜索 | ⚠️ 7 源在线搜索 | 可增强 |
| 本地 WebUI | ✅ 只读浏览 | ✅ 完整 GUI | 已有 |
| 持久化笔记 | ✅ 跨会话复用 | ⚠️ Paper.user_notes | 可增强 |
| 工作区 | ✅ 论文子集管理 | ❌ | P2 |

---

## 三、改进路线图

### Phase 1：基础能力增强（v3.5.0）

**目标**：补齐文献管理核心能力

| 序号 | 任务 | 涉及文件 | 预估工作量 |
|------|------|---------|-----------|
| 1.1 | PDF 元数据自动提取（PyMuPDF + 正则） | `app/services/paper_service.py` | 2h |
| 1.2 | DOI 去重机制 | `app/services/paper_service.py` | 1h |
| 1.3 | FTS5 全文索引（替换 LIKE 查询） | `app/services/paper_service.py`, `app/services/knowledge_service.py` | 3h |
| 1.4 | 批量 BibTeX/RIS 导出 | `app/services/paper_service.py`, `server.py` | 2h |
| 1.5 | 分层阅读（元数据→摘要→结论） | `nexus-ui/src/pages/PaperLibraryPage.tsx` | 2h |
| 1.6 | 阅读/搜索行为埋点 | `app/services/metrics_service.py`（新建） | 2h |

**依赖**：`pip install pymupdf`（PDF 解析）

---

### Phase 2：智能检索升级（v3.6.0）

**目标**：实现语义搜索和主题发现

| 序号 | 任务 | 涉及文件 | 预估工作量 |
|------|------|---------|-----------|
| 2.1 | 向量嵌入服务（sentence-transformers + FAISS） | `app/search/vectors.py`（新建） | 4h |
| 2.2 | RRF 混合搜索算法 | `app/search/engine.py` | 2h |
| 2.3 | 论文分块索引 | `app/search/chunks.py`（新建） | 3h |
| 2.4 | BERTopic 主题聚类 | `app/search/topics.py`（新建） | 4h |
| 2.5 | Dashboard 主题可视化 | `nexus-ui/src/pages/Dashboard.tsx` | 3h |
| 2.6 | 语义推荐（基于近期阅读） | `app/services/insights_service.py`（新建） | 2h |

**依赖**：`pip install sentence-transformers faiss-cpu bertopic hdbscan umap-learn`

---

### Phase 3：引用图谱与写作（v3.7.0）

**目标**：构建引用关系网络和结构化写作

| 序号 | 任务 | 涉及文件 | 预估工作量 |
|------|------|---------|-----------|
| 3.1 | Citations 表 + 引用关系解析 | `app/models/citation.py`（新建）, `app/services/citation_service.py`（新建） | 3h |
| 3.2 | 正向/反向引用查询 UI | `nexus-ui/src/pages/PaperLibraryPage.tsx` | 3h |
| 3.3 | 文内引用检查 | `app/ai/tools/citation_tool.py`（新建） | 2h |
| 3.4 | 结构化写作工作流 | `nexus-ui/src/pages/WritingPage.tsx`（新建） | 6h |
| 3.5 | 引用追溯（写作→文献库） | 与 3.4 集成 | 2h |
| 3.6 | 论文精读引导 | `nexus-ui/src/pages/PaperLibraryPage.tsx` | 3h |

---

### Phase 4：高级功能（v4.0.0）

**目标**：PDF 深度解析和完整科研工作流

| 序号 | 任务 | 涉及文件 | 预估工作量 |
|------|------|---------|-----------|
| 4.1 | MinerU PDF 解析集成 | `app/services/pdf_service.py`（新建） | 6h |
| 4.2 | 多源导入（Zotero / EndNote） | `app/services/import_service.py`（新建） | 4h |
| 4.3 | 元数据清洗审核 UI | `nexus-ui/src/pages/MetadataAuditPage.tsx`（新建） | 4h |
| 4.4 | 工作区（论文子集管理） | `app/models/workspace.py`, `nexus-ui/src/pages/WorkspacePage.tsx` | 4h |
| 4.5 | DOCX 导出 | `app/services/export_service.py`（新建） | 2h |
| 4.6 | 研究洞察 Dashboard | `nexus-ui/src/pages/InsightsPage.tsx`（新建） | 4h |

---

## 四、关键算法参考

### 4.1 RRF（Reciprocal Rank Fusion）融合排序

来源：ScholarAIO `scholaraio/services/index.py`

```python
def reciprocal_rank_fusion(fts_results, vec_results, k=60):
    """
    RRF 融合公式：score(d) = Σ 1/(k + rank_i(d))
    参考：Cormack et al., SIGIR 2009
    """
    scores = {}
    sources = {}

    for rank, paper in enumerate(fts_results, 1):
        pid = paper["id"]
        scores[pid] = scores.get(pid, 0) + 1.0 / (k + rank)
        sources[pid] = sources.get(pid, set()) | {"fts"}

    for rank, paper in enumerate(vec_results, 1):
        pid = paper["id"]
        scores[pid] = scores.get(pid, 0) + 1.0 / (k + rank)
        sources[pid] = sources.get(pid, set()) | {"vec"}

    # 按融合分数降序排列
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return ranked, sources
```

### 4.2 BERTopic 主题聚类流程

来源：ScholarAIO `scholaraio/services/topics.py`

```
1. 加载预计算的 embeddings（title + abstract）
2. UMAP 降维（n_neighbors=min(15, n//10), n_components=5, metric=cosine）
3. HDBSCAN 聚类（min_cluster_size 可配置，默认 5）
4. c-TF-IDF 主题表示提取（ngram_range=(1,3)）
5. KeyBERTInspired + MMR 增强多样性（diversity=0.3）
6. 离群点重分配（基于 embedding 最近邻）
```

### 4.3 FTS5 索引增量更新

来源：ScholarAIO `scholaraio/services/index.py`

```
1. 遍历论文目录，计算内容 hash（标题+作者+摘要+结论）
2. 与 papers_hash 表比对：
   - 新增：INSERT INTO papers
   - 变更：DELETE + INSERT（先删旧文档再插新文档）
   - 未变：跳过
3. 增量更新 FAISS 索引（纯新增时 append，内容变更时全量重建）
```

---

## 五、依赖引入计划

### Phase 1 依赖
```toml
[project.optional-dependencies]
pdf = ["pymupdf>=1.24.0"]
```

### Phase 2 依赖
```toml
embed = ["sentence-transformers>=2.2.0", "faiss-cpu>=1.7.4", "numpy>=1.24.0"]
topics = ["bertopic>=0.16.0", "hdbscan>=0.8.33", "umap-learn>=0.5.4", "scikit-learn>=1.3.0", "pandas>=2.0.0"]
```

### Phase 3 依赖
```toml
office = ["python-docx>=1.0.0"]
```

### Phase 4 依赖
```toml
import = ["pyzotero>=1.5.0"]
full = ["pymupdf", "sentence-transformers", "faiss-cpu", "bertopic", "python-docx", "pyzotero"]
```

---

## 六、架构适配说明

ScholarAIO 是 CLI + Agent Skills 架构，AI Nexus Assistant 是 GUI + API 架构。移植时需要注意：

1. **ScholarAIO 的 CLI 命令** → **AI Nexus Assistant 的 API 端点**
   - `scholaraio search` → `GET /api/search`
   - `scholaraio ingest` → `POST /api/papers/import-pdf`
   - `scholaraio topics` → `GET /api/topics`

2. **ScholarAIO 的 Skills** → **AI Nexus Assistant 的 AI 工具 + 写作页面**
   - `skills/search` → `app/ai/tools/academic_tool.py`
   - `skills/academic-writing` → `nexus-ui/src/pages/WritingPage.tsx`

3. **ScholarAIO 的文件系统存储** → **AI Nexus Assistant 的数据库 + 文件混合存储**
   - 论文 Markdown 保存在 `data/papers/<uuid>/` 目录
   - 元数据保存在 SQLAlchemy ORM 中
   - 向量索引保存在 SQLite 中

4. **ScholarAIO 的 config.yaml** → **AI Nexus Assistant 的 Settings 页面 + 数据库配置**
   - LLM 配置已在 `ModelConfig` 表中
   - 需新增 `EmbedConfig`、`TopicsConfig` 等配置项

---

## 七、致谢

本改进方案的分析和设计参考了以下开源项目：

- **ScholarAIO** (https://github.com/ZimoLiao/scholaraio) — AI-Native Research Terminal，由 Zi-Mo Liao 开发，MIT 许可证。ScholarAIO 提供了完整的科研基础设施设计，包括 PDF 解析、混合搜索、主题发现、引用图谱、学术写作等功能模块的实现方案。

特别感谢 ScholarAIO 的以下设计思想对本项目的启发：
- **Agent-first 架构**：虽然 AI Nexus Assistant 采用 GUI-first 设计，但 ScholarAIO 的 skill 路由思想可以转化为 AI 工具的结构化调用
- **三级 PDF 解析降级**：MinerU → Docling → PyMuPDF 的优雅降级策略
- **RRF 混合搜索算法**：关键词 + 语义的融合排序是提升搜索质量的关键
- **BERTopic 主题发现**：基于嵌入的自动主题聚类为文献库提供了宏观视角
- **分层阅读理念**：元数据 → 摘要 → 结论 → 全文的按需加载设计

---

## 八、实现状态（2026-06-21）

### Phase 1：基础能力增强 ✅ 已完成

| 任务 | 状态 | 实现文件 |
|------|------|---------|
| PDF 元数据自动提取 | ✅ | `app/services/pdf_service.py` — PyMuPDF 内置元数据 + 正则 + OpenAlex API 三级提取 |
| DOI 去重机制 | ✅ | `app/services/paper_service.py` — DOI 优先去重 → 标题降级去重 |
| FTS5 全文索引 | ✅ | `app/search/fts.py` — FTS5 虚拟表 + 自动同步触发器 + LIKE 降级 |
| 批量 BibTeX/RIS 导出 | ✅ | `server.py` — `/api/papers/export` 端点 |
| 分层阅读 | ✅ | `nexus-ui/src/pages/PaperLibraryPage.tsx` — 元数据/摘要/全文三层切换 |
| 阅读/搜索行为埋点 | ✅ | `app/services/metrics_service.py` — MetricEvent 模型 + 热词/高频阅读/趋势统计 |

### Phase 2：智能检索升级 ✅ 已完成

| 任务 | 状态 | 实现文件 |
|------|------|---------|
| 向量嵌入服务 | ✅ | `app/search/vectors.py` — sentence-transformers + FAISS + 自动签名检测 |
| RRF 混合搜索 | ✅ | `app/search/hybrid.py` — FTS5 + 向量 RRF 融合 + 三级降级 |
| BERTopic 主题聚类 | ✅ | `app/search/topics.py` — BERTopic + 预计算嵌入复用 |

### Phase 3：引用图谱与写作 ✅ 已完成

| 任务 | 状态 | 实现文件 |
|------|------|---------|
| Citations 表 + 引用关系解析 | ✅ | `app/services/citation_service.py` — DOI 正则提取 + 正向/反向/共同引用 |
| 文内引用检查 | ✅ | `server.py` — `/api/citations/check` 端点 |

### Phase 4：高级功能 ✅ 已完成

| 任务 | 状态 | 实现文件 |
|------|------|---------|
| DOCX 导出 | ✅ | `app/services/export_service.py` — Markdown → DOCX + 多格式参考文献 |
| 工作区 | ✅ | `app/services/workspace_service.py` — 论文子集管理 + CRUD |

### 新增 API 端点汇总

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/papers/fts-search` | GET | FTS5 全文搜索 |
| `/api/papers/hybrid-search` | GET | 混合搜索（FTS5 + 向量 RRF） |
| `/api/papers/build-vectors` | POST | 构建向量索引 |
| `/api/papers/export` | GET | 批量 BibTeX/RIS 导出 |
| `/api/papers/{id}/pdf` | GET | PDF 文件流（iframe 预览） |
| `/api/topics/build` | POST | 构建主题模型 |
| `/api/topics` | GET | 主题概览 |
| `/api/topics/{id}/papers` | GET | 主题下论文 |
| `/api/citations/build` | POST | 构建引用关系 |
| `/api/citations/{id}/references` | GET | 正向引用 |
| `/api/citations/{id}/citing` | GET | 反向引用 |
| `/api/citations/stats` | GET | 引用统计 |
| `/api/citations/check` | POST | 文内引用检查 |
| `/api/export/docx` | POST | DOCX 导出 |
| `/api/export/refs` | GET | 参考文献列表 |
| `/api/workspaces` | GET/POST | 工作区 CRUD |
| `/api/workspaces/{id}/papers` | GET/POST/DELETE | 工作区论文管理 |
| `/api/metrics/event` | POST | 行为埋点 |
| `/api/insights` | GET | 研究洞察 |

---

## 九、ScholarAIO 深度技术解析

### 9.1 代码风格规范

#### 导入组织

所有文件以 `from __future__ import annotations` 开头（PEP 604 联合类型），导入顺序严格遵循：

1. `from __future__ import annotations`
2. 标准库（字母序）
3. 第三方包
4. 项目内部导入
5. `TYPE_CHECKING` 守卫（仅类型检查器需要的导入）

```python
from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    import faiss
    from scholaraio.core.config import Config
```

**重度可选依赖**（`faiss`、`torch`、`pymupdf`、`sentence_transformers`）通过 `TYPE_CHECKING` 守卫或函数内惰性导入，避免导入时失败。

#### 文档字符串风格

- 模块级文档字符串：中英双语（中文描述用途，英文描述 API 契约）
- 函数/类文档字符串：Google 风格，包含 `Args:`、`Returns:`、`Raises:` 段落
- 私有函数：简短英文文档字符串

```python
def build_index(papers_dir: Path, db_path: Path, rebuild: bool = False) -> int:
    """建立或增量更新 SQLite FTS5 全文检索索引。

    Args:
        papers_dir: 已入库论文目录，扫描其中的 ``*.json``。
        db_path: SQLite 数据库路径，不存在时自动创建。
        rebuild: 为 ``True`` 时清空旧数据后重建。

    Returns:
        本次索引的论文数量。
    """
```

#### 类型注解

- 现代 Python 3.10+ 语法：`str | None`、`list[str]`、`dict[str, str]`
- `@overload` 装饰器用于条件返回类型
- `TypedDict` 用于结构化字典
- `Literal` 类型用于约束字符串参数
- 所有公共函数有完整的参数和返回类型注解

#### 函数签名约定

- 必需参数用位置参数
- 可选筛选参数用 `*` 后的关键字参数
- `cfg: Config | None = None` 作为标准可选配置参数
- `rebuild: bool = False` 作为索引操作标准模式
- `dry_run: bool = False` 贯穿所有 CLI 命令
- `paper_ids: set[str] | None = None` 用于工作区范围限定

```python
def search(
    query: str,
    db_path: Path,
    top_k: int | None = None,
    cfg: Config | None = None,
    *,
    year: str | None = None,
    journal: str | None = None,
    paper_ids: set[str] | None = None,
) -> list[dict]:
```

#### 注释密度

- 区域分隔符：`# ============================================================================` 横幅注释
- 子区域标记：`# -- FTS5 leg --`、`# -- Vector leg --`
- 内联注释：仅用于解释非显而易见的逻辑
- 不过度注释显而易见的代码

---

### 9.2 错误处理模式

#### 优雅降级（Graceful Degradation）

ScholarAIO 最核心的错误处理模式。以 `unified_search` 为例：

```python
# -- FTS5 leg --
fts_results: list[dict] = []
try:
    fts_results = search(...)
except FileNotFoundError:
    pass

# -- Vector leg (graceful degradation) --
vec_results: list[dict] = []
try:
    from scholaraio.services.vectors import vsearch
    vec_results = vsearch(...)
except (FileNotFoundError, ImportError):
    diagnostics["vector_degraded"] = True
except Exception:
    diagnostics["vector_degraded"] = True
```

关键特点：
- **降级链**：主方案失败则尝试备选方案（MinerU 本地 → MinerU 云端 → Docling → PyMuPDF）
- **`FileNotFoundError` 语义**：不是真正的文件缺失，而是"此功能未配置"的信号
- **诊断字典**：结果包含 `diagnostics` 字典，告知调用方是否发生了降级
- **无裸 `except`**：所有异常处理器捕获具体类型

#### 步骤管道错误处理

Ingest 管道中每个步骤返回 `StepResult` 枚举：

```python
class StepResult(Enum):
    OK = "ok"
    SKIP = "skip"
    FAIL = "fail"
```

步骤通过 `ctx.status` 传递状态：`"pending"`、`"ingested"`、`"duplicate"`、`"needs_review"`、`"failed"`、`"skipped"`。失败项移至 `pending/` 目录供人工审查，而非删除。

#### 日志模式

```python
_log = logging.getLogger("scholaraio.module_name")
```

三层输出：
- 文件：DEBUG 级别，RotatingFileHandler
- 控制台：INFO 级别，裸消息
- `ui()` 函数：同时写入控制台和日志文件（替代 `print()`）

第三方日志器抑制：`httpx`、`urllib3`、`sentence_transformers` 设为 WARNING；`modelscope` 设为 ERROR。

---

### 9.3 性能优化措施

#### 增量索引构建（基于 Hash 的变更检测）

`_index_hash()` 函数为每篇论文的索引字段计算 MD5 哈希。`build_index()` 时加载已有哈希，匹配则跳过：

```python
existing_hashes: dict[str, str] = {}
if not rebuild:
    for row in conn.execute("SELECT paper_id, content_hash FROM papers_hash"):
        existing_hashes[row[0]] = row[1]

h = _index_hash(meta)
if not rebuild and existing_hashes.get(paper_id) == h:
    continue  # 未变更，跳过
```

FTS5、向量、分块三个索引器共享相同的增量更新模式。

#### 自适应 GPU 批处理

1. **GPU 性能分析**：`_run_profile()` 在递增 token 长度（64, 128, 256...）下编码虚拟文本，测量每样本增量 GPU 内存。结果缓存至 `~/.cache/scholaraio/gpu_profile.json`

2. **自适应批大小**：`_compute_batch_size()` 使用性能数据 + 0.85 安全因子计算最优批大小：`available = gpu_total * safety - baseline; bs = available / mem_per_sample`

3. **桶式编码**：文本按 token 数排序，分组到 2 的幂次桶（64, 128, 256...），每个桶有独立最优批大小

4. **OOM 重试减半**：`torch.cuda.OutOfMemoryError` 时批大小减半重试。批大小=1 仍 OOM 则降级到 CPU

5. **二次外推**：超出分析范围的 token 长度，使用二次缩放估算内存（注意力机制为 O(n²)）

#### FAISS 磁盘缓存

- FAISS 索引和论文 ID 列表缓存为 `faiss.index` 和 `faiss_ids.json`
- 内容变更时缓存失效，全量重建
- 纯新增时向量增量追加到缓存索引：`faiss.index.add()`
- ID 重叠时缓存失效（幂等重建）

#### 分块策略

- 章节由目录结构（`meta.json` 中的 TOC）或 Markdown 标题确定
- 章节内段落按 ~4800 字符分组
- 超大单段落在句子边界拆分（正则：`[.!?。！？]\s+`）
- 小块合并直到达到目标大小
- 每个分块有唯一 ID `{paper_id}:{seq:05d}` 和内容哈希用于增量更新

#### Rsync 备份优化

- `rsync -a --stats --human-readable` + 可选 `-z` 压缩
- 三种传输模式：`default`（全量同步）、`append`（恢复部分传输）、`append-verify`（恢复+完整性校验）
- SSH 选项：`BatchMode=yes` 防止交互式挂起，密码认证使用临时 `SSH_ASKPASS` 脚本

---

### 9.4 CLI 设计模式

#### 命令结构

- 使用 `argparse`，单层子命令（`explore`、`ws`、`export`、`migrate` 等为嵌套命令组）
- 每个子命令定义在独立文件中（40+ 模块）
- 命令处理函数签名：`def cmd_xxx(args: argparse.Namespace, cfg: Config) -> None`
- 通过 `set_defaults(func=cmd_xxx)` 分发

#### 运行时入口

```python
def main():
    # 惰性加载：导入发生在 main() 内部，非模块级别
    cfg = load_config()
    ensure_dirs()
    setup_logging()
    # 迁移锁和布局版本检查
    args.func(args, cfg)
```

---

### 9.5 测试模式

#### 测试结构

- pytest + 类组织（`class TestXxx:`）
- 命名约定：`test_` 前缀 + 描述性名称
- 模块级文档字符串描述测试覆盖范围和不覆盖内容

#### Fixture 设计

```python
@pytest.fixture
def tmp_papers(tmp_path):
    """创建临时论文目录，包含两篇示例论文"""
    ...

@pytest.fixture
def tmp_db(tmp_path):
    """返回临时 SQLite 数据库路径"""
    ...
```

#### 测试类型

| 类型 | 说明 |
|------|------|
| 契约测试 | 验证输出结构（搜索结果包含 `paper_id`、`title` 等） |
| 边界测试 | 空输入、不存在路径、边界情况 |
| Monkeypatch | 广泛使用 mock 外部服务 |
| 错误路径测试 | 验证成功和失败路径 |
| 集成测试 | 端到端流程（`build_index` → `search` → 验证结果） |
| 无外部依赖 | 所有测试运行在本地临时文件上，不需要网络或 GPU |

---

### 9.6 配置系统

#### 层次化 Dataclass 组合

```python
@dataclass
class Config:
    paths: PathsConfig
    llm: LLMConfig
    ingest: IngestConfig
    embed: EmbedConfig
    search: SearchConfig
    topics: TopicsConfig
    # ... 16 个子配置
```

#### 配置解析优先级

1. 显式路径
2. 环境变量 `SCHOLARAIO_CONFIG`
3. 从 cwd 向上遍历 6 层
4. `~/.scholaraio/config.yaml`

#### API Key 解析链

配置文件 → 通用环境变量 → 后端特定环境变量 → 回退

#### 输入标准化

```python
_normalize_choice()      # 选择值标准化
_normalize_positive_int() # 正整数标准化
_bool_or_default()       # 布尔值标准化
_coerce_str_list()       # 字符串列表强制转换
```

路径通过 `@property` 方法相对于 `_root` 解析。

---

### 9.7 关键设计模式总结

| 模式 | 示例 | 文件 |
|------|------|------|
| 优雅降级 | FTS+向量搜索回退 | `index.py` |
| Hash 增量更新 | 跳过未变更论文 | `index.py`, `vectors.py`, `chunks.py` |
| 结果 Dataclass | `ConvertResult`, `BackupRunResult` | `mineru.py`, `backup.py` |
| 上下文传递 | `InboxCtx` 管道步骤线程化 | `types.py`, `inbox_steps.py` |
| 降级链 | MinerU → Docling → PyMuPDF | `inbox_steps.py` |
| 惰性导入 | 重度依赖函数内导入 | `vectors.py`, `mineru.py` |
| 模块级缓存 | `_model_cache`, `@lru_cache` | `vectors.py` |
| 配置标准化 | 输入验证 + 安全默认值 | `config.py` |
| `ui()` 双输出 | 用户消息同时写入控制台和日志 | `log.py` |
| 步骤管道 | `StepResult` 枚举 + `InboxCtx` 状态机 | `types.py` |
| 可 Monkeypatch | `_pipeline_attr()` 间接调用用于测试注入 | `inbox_steps.py` |
| WAL 模式 SQLite | 所有 SQLite 操作使用 `PRAGMA journal_mode=WAL` | `index.py`, `chunks.py` |
| Frozen Dataclass | 不可变值对象 | `mineru.py`, `chunks.py` |

---

## 十、ScholarAIO 科研助手功能深度解析

### 10.1 学术写作系统

#### 路由式写作入口（`academic-writing`）

**问题**：用户知道要什么交付物（综述、海报、论文章节），但不知道该调用哪个专用 skill。

**实现**：`academic-writing` 是纯路由器，包含两个查找表：
- **按交付物路由**：文献综述 → `literature-review`，单篇精读 → `paper-guided-reading`，论文章节 → `paper-writing`，审稿回复 → `review-response`，研究空白 → `research-gap`，技术报告 → `technical-report`，海报 → `poster`
- **按写作阶段路由**：选题 → `topics`，论文收集 → `explore`+`search`，起草 → `paper-writing`，润色 → `writing-polish`，回复 → `review-response`，交付 → `document`

工作流：识别交付物 → 识别写作阶段 → 选择主 skill → 告知用户路由计划 → 交给下游 skill。

#### 文献综述（`literature-review`）

**两种模式**：
- **手动模式**：逐步确认——(1) 明确需求 (2) 扫描工作区论文 L1-L2 (3) 提出骨架 (4) 深度阅读 L3/L4 (5) 逐节写作 (6) 导出参考文献
- **快速模式**：三层质量控制——(a) 自动扫描所有论文 L1-L2 (b) 自动生成骨架 (c) **Critic 骨架重构**：子代理审查骨架，强制将"清单式"改为"论证式" (d) 子代理使用批判性阅读模板深度阅读 (e) 自动起草，强制包含丰富元素（数据表、概念图）

**输出格式**：Markdown（快速草稿）或 LaTeX（正式学术综述，含 ctex/xelatex 编译、图表审计、引用闭合检查）

#### 单篇论文精读（`paper-guided-reading`）

**6 步交互工作流**：
1. **本地搜索**：多维检索（关键词 + 语义 + 作者）展示 3-5 个候选
2. **意图确认**：用户确认论文，或本地结果不匹配时降级到 arXiv/网页搜索
3. **全文加载**：L2（摘要）→ L3（结论）→ L4（全文）+ 已有笔记
4. **结构化分析**：基于 20 维框架（科学问题、核心假设、研究设计、数据/样本、方法、分析管道、统计、发现、局限性、与用户研究的关联、图表验证等），但以对话式要点输出
5. **交互式问答**：带证据引用的对话式教学
6. **持久化**：通过 `--append-notes` 写入 `notes.md`

#### 论文章节写作（`paper-writing`）

**章节特定策略**：
- **引言**：宏观到微观漏斗，用工作区引用建立研究脉络、识别空白、陈述贡献
- **相关工作**：聚焦的文献综述，按与当前论文的关系组织
- **方法**：用户描述方法，代理组织，交叉引用工作区论文比较，确保符号一致
- **结果/讨论**：读取用户数据，在工作区搜索可比基线，编写 Python 代码进行统计验证
- **摘要**：最后撰写，严格格式（背景-问题-方法-结果-意义）

**引用诚实规则**：所有引用必须来自工作区真实论文，禁止编造。缺失引用标记为 `[CITATION NEEDED]`。

#### 审稿回复（`review-response`）

1. 解析审稿意见为 MAJOR/MINOR/POSITIVE/QUESTION 类别
2. 对每条意见，在原稿中定位相关段落，在工作区搜索支撑证据
3. 撰写结构化回复：引用-回复-修订格式
4. 多模态辅助：重新分析图表、编写 Python 重现计算、验证 LaTeX 公式推导

#### 研究空白分析（`research-gap`）

**五维分析**：
1. **主题覆盖**：全局主题模型中工作区缺失哪些主题？
2. **时间趋势**：逐年发表模式（热点、下降区、休眠空白）
3. **方法比较**：跨论文方法矩阵（哪些方法广泛使用？哪些组合未尝试？）
4. **引用图谱空洞**：论文间矛盾、未验证的高被引作品、缺失关键引用
5. **作者自述未来工作**：从 L3 结论提取未来工作，交叉搜索检查是否有人已完成

输出按类型分类：知识空白、方法空白、矛盾空白、迁移空白、规模空白。

#### 文档生成（`document`）

三种格式的完整 Python API 参考：
- **python-docx**：标题、段落、图片、表格、目录（XML 字段插入）、分页、页眉页脚
- **python-pptx**：幻灯片布局、文本框、表格、图片、多级列表
- **openpyxl**：工作簿、样式标题、数据行、图表、自动筛选、冻结窗格

文档检查（`scholaraio document inspect`）输出结构化信息：PPTX 每张幻灯片的形状位置/大小/文本预览；DOCX 标题层次/段落/表格/图片/样式统计；XLSX 工作表维度/数据预览/图表信息。

---

### 10.2 文献探索系统

#### 探索库（`explore`）

**问题**：研究者需要调查整个期刊、研究领域或机构产出，无需手动下载论文。

**实现**：
1. **OpenAlex 获取**：多维过滤（ISSN、概念、主题、作者、机构、关键词、年份、最低引用、来源类型、OA 类型）+ 游标分页。数据存储为 JSONL。增量模式支持 DOI 去重。
2. **嵌入**：使用与主库相同的 Qwen3-Embedding-0.6B 模型生成语义向量，构建 FTS5 关键词索引。
3. **主题建模**：BERTopic 聚类，超参数随数据集大小自动调整。
4. **三种搜索模式**：FTS5 关键词搜索、FAISS 语义搜索、RRF 融合搜索。
5. **可视化**：6 种 HTML 图表。

**关键设计**：探索库与主论文库完全隔离——独立 JSONL 存储、独立 SQLite 数据库、独立嵌入、独立 FTS 索引。

#### 联邦发现（`fsearch`）

**问题**：单一搜索范围不足以全面发现文献。

**实现**：`--scope` 参数接受逗号分隔的组合：
- `main`：主库搜索（FTS5 + FAISS + RRF）
- `explore:<name>`：搜索特定探索库（支持 `explore:*` 通配符）
- `proceedings`：搜索会议论文集
- `arxiv`：调用 arXiv Atom API，结果标注 `[ingested]`（已在本地库中）

每个范围独立运行，arXiv 结果与本地库交叉引用（通过 DOI 和 arXiv ID 匹配）。

---

### 10.3 分层阅读实现

**四层模型**：
- **L1（元数据）**：标题、作者、年份、期刊、DOI、引用数——从 `meta.json` 读取
- **L2（摘要）**：摘要文本——从 `meta.json["abstract"]` 读取
- **L3（结论）**：提取的结论段落——存储在 `meta.json["l3_conclusion"]`
- **L4（全文）**：MinerU 转换的完整 Markdown——从 `paper.md` 读取

#### TOC 提取（`enrich_toc`）

1. 正则提取 `paper.md` 中所有 `#` 标题及行号
2. 标题 ≥ 80 个（如书籍）：规则提取——检测印刷目录区域、跳过前言、检测频率 >3 的页眉、从编号推断层级
3. 标题 < 80 个：发送给 LLM，指定保留哪些标题（编号章节、Abstract、Introduction、Conclusion 等），丢弃哪些（页眉、期刊名、出版元数据）。LLM 返回含行号和层级的 JSON

#### L3 结论提取（`enrich_l3`）

**三级级联策略**：
1. **TOC 路径**（最便宜）：如果 TOC 存在，正则匹配结论关键词（`conclusion|conclusions|summary|closing`），提取结论标题到下一个 TOC 条目之间的行，LLM 验证
2. **主路径**：发送所有标题给 LLM 识别结论章节起始标题，Python 提取到下一个真实章节标题，LLM 验证
3. **降级路径**：发送前 100 + 后 200 行给 LLM 询问起止行号，提取并验证

**LLM 验证**：每次提取都经 LLM 确认包含实际结论内容（非页眉或致谢），清理文本（移除章节标题、结论后材料）。最低阈值：提取 100 字符，清理后 50 字符。

**论文类型跳过**：学位论文、书籍、专利等在 `L3_SKIP_TYPES` 中自动跳过。

---

### 10.4 元数据质量审计

#### 审计服务（`audit.py`）

扫描所有论文目录检查：
- **缺失关键字段**：DOI、摘要、年份、作者、期刊、标题（分严重性级别）
- **文件配对**：每个 `meta.json` 必须有匹配的 `paper.md`
- **内容一致性**：MD 过短（<200 字符，可能转换失败）、标题不匹配（JSON 标题与 MD 第一个 H1 的词重叠率 < 0.3）
- **DOI 重复**：按标准化 DOI 分组标记重复
- **目录名格式**：期望 `Author-Year-Title` 模式

**标题不匹配检测**：`_best_title_match()` 遍历所有 JSON 标题变体，提取 4+ 字符关键词，扫描 MD 前 80 行候选标题，计算词重叠率。

#### Scrub 工作流（`scrub`）

增量审查修复工作流：
1. 查找未审查的论文（跳过有 `.scrubbed` 标记的），问题包括：乱码标题、占位符标题（"Introduction"、"TLDR"）、可疑作者（"Unknown"）、可疑年份、异常目录名
2. 逐篇检查（L1 元数据 + L4 全文）
3. 保守修复（`--no-api` 防止 API 覆盖本地修正）
4. 处理目录重命名
5. 用 `.scrubbed` 文件标记已审查论文
6. 批量完成后重建索引

**关键设计**：`.scrubbed` 表示"已审查且当前可接受"，不是"完美"。修复命令保留所有现有元数据，仅覆盖明确指定的字段。

---

### 10.5 导入系统

#### 外部导入编排（`external_import.py`）

批量导入管道：
1. 收集现有 DOI、专利号、arXiv ID 用于去重
2. 每条记录：快速 DOI 去重 → `step_dedup()`（API 丰富 + DOI 检查）→ `step_ingest()`
3. 如提供 PDF 路径（按索引对齐），复制到论文目录
4. API 调用限速（每条记录间 1 秒）
5. 批量 `step_embed()` + `step_index()` 更新向量和 FTS 索引
6. 返回统计：`{ingested, duplicate, needs_review, failed, skipped}`

#### Zotero 导入（`zotero.py`）

**两种模式**：
- **Web API 模式**：使用 `pyzotero` 库获取所有项目，转换 Zotero 创建者格式，下载 PDF 附件
- **本地 SQLite 模式**：直接读取 `zotero.sqlite` 数据库，连接 `items`、`itemData`、`itemDataValues`、`itemCreators`、`creators`、`creatorTypes` 表，在本地存储中查找 PDF

两种模式都通过 `_ITEM_TYPE_MAP` 将 Zotero 项目类型转换为 Crossref 风格论文类型。

#### Endnote 导入（`endnote.py`）

使用 `endnote_utils.core` 解析 XML 和 RIS 格式。XML 模式下：
- 从 `<pdf-urls>` 元素解析 PDF 路径
- `_pick_main_pdf()` 过滤补充材料（SI/supplement 正则），选择最大的非 SI PDF
- 作者名从 "Last, First" 标准化为 "First Last"

#### arXiv 提供者（`arxiv.py`）

**三层访问**：
1. **Atom API**：标准 arXiv API + XML 解析，支持字段搜索（`au:`、`ti:`、`abs:`、`cat:`、`id:`），结果客户端后过滤
2. **最近页面降级**：API 返回空结果时抓取 arXiv 列表 HTML 页面
3. **摘要页面降级**：作为最后手段从 arXiv 摘要 HTML 页面抓取引用元数据

ID 标准化处理裸 ID、`arXiv:` 前缀和完整 URL，剥离版本后缀。下载限速 3 秒间隔，原子文件写入（`.part` 临时文件后重命名）。

---

### 10.6 AI for Science 运行时

**问题**：用户通过代理运行科学软件（Quantum ESPRESSO、LAMMPS、GROMACS 等），但代理对这些工具参数的了解不完美。

**实现**：运行时行为协议，非工具手册：
1. **Toolref 优先**：在做任何事之前先通过 `scholaraio toolref show/search` 查找命令/参数
2. **优雅降级**：toolref 覆盖不完整时，降级到官方文档继续任务，不要求用户先修复文档层
3. **关注点分离**：工具特定 skill 处理何时使用工具和科学规范；toolref 处理接口/参数参考；科学运行时处理不确定性下的行为
4. **升级规则**：仅在文档缺口反复出现、阻塞常见任务或影响正确性时升级

**明确列出的反模式**：不要从内存中转储原始标志；不要告诉用户先改进 toolref；不要将成功的 CLI 运行与有效的科学结果混淆；不要用参数查找替代科学判断。

---

### 10.7 跨切面设计模式总结

| 模式 | 说明 | 应用场景 |
|------|------|---------|
| **分层阅读 L1-L4** | 元数据→摘要→结论→全文的渐进式披露 | 所有阅读 skill |
| **持久化跨会话笔记** | `notes.md` 标准化格式（日期\|工作区\|skill名） | 精读、综述、研究空白 |
| **工作区隔离** | 按项目组织论文子集，引用 ID 而非复制 | 所有写作 skill |
| **防御性 LLM 使用** | 所有 LLM 提取数据都验证 + 最低长度阈值 + 级联降级 | TOC 提取、结论提取 |
| **Skill 组合模型** | 复杂交付物由简单 skill 链式构建 | 海报、技术报告 |
| **Critic 骨架重构** | 子代理审查骨架结构，强制改为论证式 | 文献综述 |
| **批判性阅读模板** | 结构化阅读框架（20 维度） | 单篇精读 |
| **引用诚实规则** | 禁止编造引用，缺失标记 `[CITATION NEEDED]` | 所有写作 skill |
| **增量审查标记** | `.scrubbed` 文件标记已审查论文 | 元数据清洗 |
| **联邦搜索** | 多范围并行搜索 + 本地库交叉引用 | 文献发现 |
| **原子文件写入** | `.part` 临时文件后重命名，防止部分写入 | arXiv 下载 |
| **探索库隔离** | 独立存储、独立数据库、独立索引 | 文献探索 |

---

## 第十一章：功能实现深度解析——出版社 PDF 拉取与全链路功能

> 本章以**出版社 PDF 拉取**为核心，深入分析其实现细节，并扩展到 ScholarAIO 全部关键功能的实现方式。

### 11.1 出版社 PDF 拉取：完整的实现架构

这是 ScholarAIO 最具特色的功能之一——**利用用户自身的合法网络权限**（如校园网 IP）从出版社网站拉取 PDF，不依赖任何第三方影子图书馆。

#### 11.1.1 核心设计哲学

模块文档字符串明确声明：*"Lightweight, rights-respecting PDF acquisition helpers."*

系统**不集成** Unpaywall、Sci-Hub 或任何第三方服务。所有 PDF 获取都通过用户自己的网络环境完成，这意味着：
- 用户在校园网内 → 自动通过机构订阅访问
- 用户配置了代理 → 通过代理访问
- 用户使用 `--direct` 标志 → 绕过代理，直连访问

#### 11.1.2 三阶段 PDF 解析管线

```
阶段 1: 定位器规范化 (_locator_to_url)
  DOI 字符串 → https://doi.org/...
  DOI URL → 直接使用
  完整 URL → 直接使用
  纯标题 → Crossref API 查询 → DOI → URL

阶段 2: 落地页抓取 (fetch_pdf)
  GET URL (stream=True, allow_redirects=True)
  ├─ Content-Type 是 PDF？ → 直接保存
  └─ 是 HTML？ → 进入阶段 3

阶段 3: PDF 链接提取 (_candidate_pdf_urls)
  三种正则模式并行扫描：
  ├─ <meta name="citation_pdf_url" content="...">  ← 最高优先级
  ├─ <a href="...pdf"> / <a href=".../pdf/">
  └─ 正则匹配 HTML body 中的 https://...pdf URL
  → 去重后按优先级逐个尝试下载
```

#### 11.1.3 校园网直连模式的实现

```python
# pdf_fetch.py 核心逻辑
session = requests.Session()
session.trust_env = not direct  # --direct 标志的真正含义
```

- **`direct=True`**：`trust_env = False`，requests 库**忽略**所有代理环境变量（`HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`），连接直接走用户本地网络。如果用户在校园网内，请求通过校园 IP 到达出版社，获得机构订阅访问权限。
- **`direct=False`**（默认）：`trust_env = True`，正常读取代理配置。

测试用例 `test_direct_fetch_ignores_proxy_environment_with_real_http` 显式验证：设置一个不可用的代理环境变量，`direct=True` 时仍然能成功下载。

#### 11.1.4 PDF 验证与头部规范化

下载后执行两步验证：

1. **魔数检查** (`_valid_pdf_payload`)：读取前 1024 字节，查找 `%PDF-` 标记
2. **头部规范化** (`_normalize_pdf_header`)：某些出版社会在 PDF 流前面插入非 PDF 字节（如跟踪像素、广告横幅）。规范化函数定位 `%PDF-` 标记并剥离前面的所有内容，使用流式处理，不会将整个文件读入内存

#### 11.1.5 规范 PDF 命名与批量重拉取

**命名约定**：规范 PDF 与父目录同名
```
papers/Doe-2026-Real-HTTP-Paper/
  ├── Doe-2026-Real-HTTP-Paper.pdf   ← 规范 PDF
  ├── meta.json
  └── paper.md
```

**重拉取优先级**：`source_url` > `doi` > `ids.doi`

**批量模式**：`fetch-pdf --all` 遍历所有论文目录，复用单个 `requests.Session`，逐篇尝试下载，单篇失败不中断批次，最终报告 downloaded/skipped/failed 统计。

#### 11.1.6 多出版商模式适配

系统**不使用**出版商特定的爬虫，而是通过通用 HTML 抓取适配所有出版商：

| 出版商模式 | 适配方式 |
|-----------|---------|
| Elsevier/Springer/Wiley 等 | `<meta name="citation_pdf_url">` 标签（学术出版标准） |
| arXiv | 独立 provider，专用 API |
| 直接 PDF 链接 | `<a href="...pdf">` 锚点匹配 |
| 签名/重定向 URL | `allow_redirects=True` 跟随重定向链 |
| 流前插入非 PDF 字节 | `_normalize_pdf_header` 剥离 |
| 纯标题无 DOI | Crossref API 查询解析为 DOI |

#### 11.1.7 错误处理与重试

- **候选 URL 逐个尝试**：第一个 PDF 链接失败 → 自动尝试下一个
- **API 重试**：HTTP 429/502/503/504 → 指数退避重试（最多 3 次），尊重 `Retry-After` 头
- **批量模式容错**：每篇论文独立捕获 `OSError`/`ValueError`/`RequestException`/`PdfFetchError`，记录错误但不中断批次
- **MinerU 降级链**：本地 MinerU → 云 MinerU → docling → pymupdf

### 11.2 多源导入系统

ScholarAIO 支持从 5 种来源导入，通过统一的 `import_external()` 编排器处理去重、入库、PDF 附加和批量后处理。

#### 11.2.1 Zotero 导入（双模式）

**Web API 模式**：通过 `pyzotero` 库调用 Zotero Web API，获取所有条目（支持 collection/item-type 过滤），转换为统一的 `PaperMetadata` 数据结构，可选下载 PDF 附件。

**本地 SQLite 模式**：以只读模式（`?immutable=1`）打开用户的 `zotero.sqlite`，查询 `items`/`itemData`/`itemCreators` 表，从 Zotero `storage/` 目录解析 PDF 路径。

**集合到工作区映射**：`--import-collections` 标志通过 DOI-to-UUID 匹配，将 Zotero 集合自动创建为 ScholarAIO 工作区。

#### 11.2.2 Endnote 导入

自动检测 `.xml` vs `.ris` 格式。XML 模式解析 `internal-pdf://` 链接并解析到 `<file>.Data/PDF/` 目录。`_pick_main_pdf()` 启发式函数通过正则匹配 SI/supplement 命名模式过滤补充材料。

#### 11.2.3 arXiv 导入

查询 arXiv Atom API（`export.arxiv.org/api/query`），使用 `defusedxml` 安全解析 XML。`search_arxiv()` 构建字段限定查询（`au:`, `ti:`, `abs:`, `cat:`）。PDF 下载有 3 秒礼貌间隔限速。使用 `.part` 临时文件 + 原子重命名防止部分写入。

#### 11.2.4 Web/URL 导入

通过外部 `qt-web-extractor` MCP 服务渲染网页并提取内容，写入文档 inbox，保留来源字段（`source_url`, `source_type`, `extraction_method`）。

#### 11.2.5 共享编排器 `import_external()`

```python
def import_external(records: list[PaperMetadata], pdfs: dict | None):
    # 1. DOI 去重检查
    # 2. 逐条执行 step_dedup()（API 富化 + DOI 检查）
    # 3. 逐条执行 step_ingest()（写入 meta.json + paper.md）
    # 4. 批量 step_embed() + step_index()
```

### 11.3 Inbox 分类系统

系统支持 **5 种 inbox**，各有针对性处理逻辑：

| Inbox | 路径 | 用途 | DOI 去重 | 特殊行为 |
|-------|------|------|---------|---------|
| Regular | `data/spool/inbox` | 标准学术论文 | 是 | 完整管线：MinerU → extract → dedup → ingest |
| Document | `data/spool/inbox-doc` | 非学术文档 | 否 | Office 转换 → MinerU → LLM 提取 → 入库 |
| Thesis | `data/spool/inbox-thesis` | 学位论文 | 否 | 跳过 API 查询，标记 `paper_type=thesis` |
| Patent | `data/spool/inbox-patent` | 专利文档 | 否（用公开号） | 跳过 API 查询，按 `publication_number` 去重 |
| Proceedings | `data/spool/inbox-proceedings` | 会议论文集 | 变化 | Proceedings 特有的拆分/应用逻辑 |

**去重分类结果**：`ingested`（成功入库）/ `duplicate`（DOI 已存在）/ `needs_review`（无 DOI 且未检测为已知类型）/ `failed`（管线错误）

**文档类型检测**（`detection.py`）：
- 专利：检查 `publication_number` → 标题关键词 → 正则扫描 Markdown
- 学位论文：标题关键词 → LLM 分类（前 30,000 字符）
- 书籍：API `paper_type` 字段 → 标题关键词 → LLM 分类
- arXiv 预印本：提取后检查 `arxiv_id` 存在性

### 11.4 工作区系统

工作区是论文子集管理机制，存储在 `workspace/<name>/` 下。

**核心结构**：
```
workspace/my-project/
  ├── workspace.yaml     # 可选：schema_version, name, description, tags
  └── refs/
      └── papers.json    # [{"id": "<uuid>", "dir_name": "<name>", "added_at": "<iso>"}]
```

**操作**：
- `create()`：创建目录和空索引
- `add()`：通过 UUID/目录名/DOI 解析论文引用，去重后追加
- `remove()`：按 UUID 移除，优雅处理过期索引
- `show()`：读取条目并刷新目录名（处理重命名）

**限定范围搜索**：`ws search` 读取工作区论文 ID 集合，传递给 `vsearch()` 或 `unified_search()` 作为 `paper_ids` 过滤器。

**批量添加**：`ws add --search`（联邦搜索结果）/ `ws add --topic`（BERTopic 簇）/ `ws add --all`（整个库）

### 11.5 元数据清洗系统

#### 11.5.1 审计服务（规则引擎，无 LLM）

`audit_papers()` 对每篇论文执行：
- **缺失字段检查**：DOI、摘要、年份、作者、期刊、标题（按 paper_type 条件检查）
- **文件配对验证**：meta.json 和 paper.md 共存；paper.md < 200 字符标记为转换失败
- **标题一致性**：meta.json 标题 vs paper.md H1 标题，词重叠评分 < 0.3 标记不一致
- **目录名格式**：验证 `Author-Year-Title` 模式，检测占位年份（XXXX）、乱码
- **DOI 重复检测**：收集所有 DOI 并标记重复

#### 11.5.2 Scrub 工作流（增量审查）

`list_scrub_suspects()` 检测：
- 乱码标题（含替换字符 `�`）
- 占位标题（introduction, tldr, overview, summary）
- 可疑作者（Unknown, Anonymous, 单字母名）
- 可疑年份（缺失、XXXX 占位）
- 非标准目录名

**修复机制**：`cmd_repair()` 从现有元数据出发，仅覆盖显式提供的字段，保留 UUID 和所有富化字段。`.scrubbed` 标记文件跟踪已审查论文，后续增量跳过。

### 11.6 持久化笔记（跨会话记忆）

每篇论文目录可包含 `notes.md` 文件（自由格式 Markdown）。

**写入协议**：
```bash
scholaraio show "<paper-id>" --append-notes "<text>"
# 格式约定：## YYYY-MM-DD | workspace/task-source | analysis-type
```

**读取协议**：`show` 命令显示时，如果 `notes.md` 存在，在标题之后、正文之前展示。Agent 被指示优先使用已有笔记，避免重复分析。

**跨会话复用**：`notes.md` 与 `meta.json`、`paper.md` 一起存储在磁盘上，跨 Claude 会话持久存在。Agent 可以读取前几次会话的分析结论（参数值、收敛标准、关键发现），在此基础上继续工作。

### 11.7 研究洞察（阅读行为分析）

#### 指标收集

`MetricsStore` 使用 SQLite WAL 模式的 `events` 表，记录：session_id、timestamp、category、name、duration_s、tokens_in/out、model、status、detail。`search`、`vsearch`、`show` 命令自动记录事件。

#### 五维分析

| 维度 | 实现方式 |
|------|---------|
| **搜索热词** | 分词 → 去停用词 → 词频统计 → Top-K |
| **高频阅读论文** | 按论文名聚合 `read` 事件计数 |
| **阅读趋势** | 按 ISO 年-周分组，生成时间序列 |
| **语义近邻推荐** | 取最近 5 篇已读论文 → vsearch 找 Top-10 近邻 → 过滤已读 → 返回最高分未读 |
| **未读推荐** | 基于已读论文的语义相似性，发现可能被忽略的文献 |

### 11.8 联邦发现

`fsearch` 命令接受 `--scope` 参数，逗号分隔多个搜索范围：

```
scholaraio fsearch "drag reduction" --scope main,proceedings,explore:*,arxiv
```

每个范围独立搜索，结果按来源分段显示。arXiv 结果通过 DOI 和 arXiv ID 与本地库交叉引用，标记 `[ingested]` 状态。

| 范围 | 搜索方式 |
|------|---------|
| `main` | 主库统一搜索（FTS5 + FAISS 语义，RRF 排序） |
| `explore:<name>` | 指定探索库搜索 |
| `explore:*` | 遍历所有探索库 |
| `proceedings` | 会议论文集搜索 |
| `arXiv` | arXiv Atom API 查询 |

### 11.9 远程备份（rsync）

**配置**：`config.yaml` 中定义命名备份目标，每个指定 host、user、path、port、identity_file、mode、compress、exclude。

**命令构建**：`build_rsync_command()` 构造 rsync 命令：
- 基础标志：`-a --stats --human-readable`
- 可选：`-z`（压缩）、`--append`/`--append-verify`（模式）
- 远程 Shell：`_build_remote_shell()` 构建 SSH 命令，`BatchMode=yes`
- 密码处理：创建临时 askpass 脚本，设置 `SSH_ASKPASS`/`SSH_ASKPASS_REQUIRE=force`

**认证失败引导**：提供 `ssh-keyscan` 和密钥验证命令的引导说明。

### 11.10 AI for Science 运行时（科学软件文档）

`toolref` 系统是一个本地文档注册表，支持 5 种科学工具：

| 工具 | 文档来源 | 索引方式 |
|------|---------|---------|
| Quantum ESPRESSO | git clone `INPUT_*.def` 文件 | DEF 解析器 |
| LAMMPS | git clone `doc/src/*.rst` | RST 解析器 |
| GROMACS | git clone `docs/**/*.rst` | RST 解析器 |
| OpenFOAM | manifest 页面抓取 | HTML 解析器 |
| Bioinformatics | manifest 页面（minimap2, samtools 等） | HTML 解析器 |

**搜索**：FTS5 MATCH 查询 + 智能扩展（`_expand_search_query()` 将领域概念映射到工具特定术语，如 "drag coefficient" → "force coeffs"）。结果按标题/页面名/摘要/内容匹配质量评分，带工具特定加成。

**运行时协议**：Agent 优先使用 toolref 查找参数，覆盖不全时回退到官方文档，永远不要求用户修复文档空白。

### 11.11 多格式导出

| 格式 | 实现方式 |
|------|---------|
| **BibTeX** | `meta_to_bibtex()`：cite key = `LastNameYearTitleWord`，LaTeX 特殊字符转义，paper_type 映射到 BibTeX 条目类型 |
| **RIS** | `meta_to_ris()`：AU/PY/JO/VL/IS/SP/EP/DO/AB 字段格式化，页码范围拆分 SP/EP |
| **Markdown 引用列表** | 支持内置样式（APA/Vancouver/Chicago/MLA）和自定义 Python 样式（`data/libraries/citation_styles/<name>.py`） |
| **DOCX** | `_md_to_docx()` 解析器处理标题、代码块、表格、列表、引用、行内格式 |

### 11.12 本地 WebUI（只读浏览与质检）

**服务器**：基于 `http.server.ThreadingHTTPServer` 的只读 HTTP 服务器，所有写方法（POST/PUT/PATCH/DELETE）返回 `405 METHOD NOT_ALLOWED`。

**API 端点**：
- `GET /api/main/papers`：完整库视图（元数据 + 审计问题 + PDF 可用性）
- `GET /api/main/detail?id=<id>`：论文详情（摘要、L3 结论、TOC、IDs）
- `GET /api/main/pdf?id=<id>`：流式传输本地 PDF
- `GET /api/proceedings/papers`：会议论文集视图

**视图模型**：`build_main_library_view()` 扫描所有论文目录，读取 meta.json，运行 `audit_papers()`（30 秒缓存），构建行字典。

### 11.13 关键实现文件索引

| 功能 | 核心实现文件 |
|------|------------|
| PDF 拉取 | `scholaraio/services/pdf_fetch.py` |
| PDF CLI | `scholaraio/interfaces/cli/fetch_pdf.py` |
| PDF 附加 | `scholaraio/interfaces/cli/attach_pdf.py` |
| Zotero 导入 | `scholaraio/providers/zotero.py` |
| Endnote 导入 | `scholaraio/providers/endnote.py` |
| arXiv 导入 | `scholaraio/providers/arxiv.py` |
| 导入编排 | `scholaraio/services/ingest/external_import.py` |
| Inbox 管线 | `scholaraio/services/ingest/inbox_steps.py` |
| 文档类型检测 | `scholaraio/services/ingest/detection.py` |
| 工作区 | `scholaraio/projects/workspace.py` |
| 元数据审计 | `scholaraio/services/audit.py` |
| 元数据修复 | `scholaraio/interfaces/cli/repair.py` |
| 持久化笔记 | `scholaraio/services/loader.py` |
| 指标收集 | `scholaraio/services/metrics.py` |
| 研究洞察 | `scholaraio/services/insights.py` |
| rsync 备份 | `scholaraio/services/backup.py` |
| 科学工具文档 | `scholaraio/stores/toolref/` |
| 联邦搜索 | `scholaraio/interfaces/cli/fsearch.py` |
| 多格式导出 | `scholaraio/services/export.py` |
| 本地 WebUI | `scholaraio/interfaces/cli/gui.py` |
| 库视图模型 | `scholaraio/services/library_view.py` |
