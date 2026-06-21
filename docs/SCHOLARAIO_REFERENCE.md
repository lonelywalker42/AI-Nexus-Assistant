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
