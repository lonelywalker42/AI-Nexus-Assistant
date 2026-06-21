# 开发计划：v3.6.0 — ScholarAIO 特性移植

> 基于 `docs/SCHOLARAIO_REFERENCE.md` 的深度分析，筛选适合 AI Nexus Assistant（Tauri 桌面应用架构）的特性，制定可落地的开发计划。

## 一、可行性分析

### 架构差异

| 维度 | ScholarAIO | AI Nexus Assistant |
|------|-----------|-------------------|
| 形态 | Agent-first CLI + Claude Code Skills | Tauri 桌面应用（React + FastAPI） |
| 交互 | 自然语言驱动，Agent 调用 skill | GUI 点击操作 |
| PDF 解析 | MinerU（重依赖，~2GB） | PyMuPDF（轻量，~15MB） |
| 部署 | Python 虚拟环境 + Node.js | 单 exe 便携版 |

### 特性筛选矩阵

| 特性 | 价值 | 难度 | 适配性 | 决策 |
|------|------|------|--------|------|
| **出版社 PDF 拉取** | ⭐⭐⭐⭐⭐ | 中 | ✅ 直接适配 | **纳入** |
| **arXiv 搜索与导入** | ⭐⭐⭐⭐ | 低 | ✅ API 直接调用 | **纳入** |
| **元数据质量审计** | ⭐⭐⭐⭐ | 低 | ✅ 规则引擎，无 LLM | **纳入** |
| **论文笔记** | ⭐⭐⭐⭐ | 低 | ✅ 简单 CRUD | **纳入** |
| **语义近邻推荐** | ⭐⭐⭐⭐ | 低 | ✅ FAISS 已就绪 | **纳入** |
| **工作区限定搜索** | ⭐⭐⭐ | 低 | ✅ 工作区系统已就绪 | **纳入** |
| **Zotero 导入** | ⭐⭐⭐ | 中 | ⚠️ 需 pyzotero 依赖 | **纳入（简化版）** |
| **BibTeX/RIS 导入** | ⭐⭐⭐ | 低 | ✅ 文件解析 | **纳入** |
| **Inbox 分类管线** | ⭐⭐⭐ | 中 | ⚠️ 简化适配 | **纳入（简化版）** |
| **联邦搜索** | ⭐⭐⭐ | 低 | ✅ arXiv + 本地库 | **纳入** |
| **MinerU PDF 解析** | ⭐⭐⭐ | 高 | ❌ 依赖过重（~2GB） | 不纳入 |
| **AI for Science 运行时** | ⭐⭐ | 高 | ❌ 专业领域工具链 | 不纳入 |
| **rsync 远程备份** | ⭐ | 中 | ❌ Windows 桌面环境不适用 | 不纳入 |
| **本地 WebUI** | — | — | ❌ 已有 Tauri 前端 | 不适用 |
| **DOCX 导出** | ⭐⭐⭐ | 低 | ✅ 已有基础 | 已实现（v3.5.0） |

## 二、开发阶段

### Phase 1：出版社 PDF 拉取（核心功能）

> **目标**：用户在校园网环境下，输入 DOI 或论文标题，自动从出版社网站拉取 PDF 并入库。

#### 1.1 后端：`app/services/pdf_fetch.py`（新建）

```python
# 核心管线
def fetch_pdf_by_doi(doi: str, output_dir: str, timeout: int = 60) -> dict:
    """
    阶段 1: DOI → URL 规范化
      "10.xxxx/yyy" → "https://doi.org/10.xxxx/yyy"
    阶段 2: GET doi.org (follow redirects) → 落地页
      Content-Type 是 PDF？→ 直接保存
      是 HTML？→ 进入阶段 3
    阶段 3: HTML 解析 PDF 链接
      <meta name="citation_pdf_url" content="...">  ← 最高优先级
      <a href="...pdf">                               ← 次优先
      正则匹配 body 中的 https://...pdf               ← 兜底
    阶段 4: 下载 + 验证
      检查 %PDF- 魔数 → 剥离非 PDF 前缀字节 → 保存
    """
```

**关键设计**：
- **代理绕过**：`httpx.Client(proxy=None)` — 项目已有此模式（`web_search.py`）
- **校园网直连**：用户在校园网内时，请求通过校园 IP 到达出版社，自动获得机构订阅权限
- **不使用** Unpaywall/Sci-Hub，纯用户网络权限
- **PDF 验证**：`%PDF-` 魔数检查 + 头部规范化（剥离出版商插入的非 PDF 前缀）
- **候选 URL 逐个尝试**：第一个失败自动尝试下一个
- **超时**：60 秒（中文查询场景已验证此超时合理）

#### 1.2 后端：DOI 解析辅助

```python
def resolve_doi_to_url(doi: str) -> str:
    """DOI → doi.org 重定向 → 出版商落地页 URL"""

def extract_pdf_urls_from_html(html: str) -> list[str]:
    """三种正则模式提取 PDF 候选 URL"""

def validate_pdf(content: bytes) -> bool:
    """检查 %PDF- 魔数"""
```

#### 1.3 API 端点：`server.py`

```python
@app.post("/api/papers/fetch-pdf")
async def fetch_paper_pdf(request: Request):
    """
    Body: {"doi": "10.xxxx/yyy"} 或 {"title": "论文标题"}
    流程:
    1. 解析 DOI/标题 → 出版商 URL
    2. 抓取落地页 → 提取 PDF 链接
    3. 下载 PDF → 验证 → 保存到 data/papers/
    4. 自动提取元数据（PyMuPDF → 正则 → OpenAlex）
    5. 创建 Paper 记录入库
    返回: {"paper_id": "...", "status": "ok", "source": "publisher"}
    """
```

```python
@app.post("/api/papers/batch-fetch-pdf")
async def batch_fetch_papers(request: Request):
    """
    Body: {"dois": ["10.xxx/a", "10.xxx/b", ...]}
    批量拉取，单篇失败不中断，返回每篇状态
    """
```

```python
@app.post("/api/papers/{paper_id}/refetch-pdf")
async def refetch_paper_pdf(paper_id: str):
    """
    对已有论文重新拉取 PDF（用 DOI 或 source_url）
    适用于首次没有 PDF 后补充获取
    """
```

#### 1.4 前端：`PaperLibraryPage.tsx` 扩展

- 新增 **"拉取 PDF"** 按钮（工具栏区域）
- 弹窗输入 DOI 或论文标题
- 显示拉取进度（解析 DOI → 抓取落地页 → 下载 PDF → 提取元数据）
- 成功后自动刷新论文列表
- 批量拉取：支持 DOI 列表粘贴（每行一个）

#### 1.5 依赖

- `httpx` — 已有（AI 服务使用）
- `beautifulsoup4` — 新增（HTML 解析，比正则更健壮）
- `lxml` — 新增（BS4 解析器）

---

### Phase 2：arXiv 集成

> **目标**：在文献搜索页面集成 arXiv 搜索，支持直接从 arXiv 导入论文。

#### 2.1 后端：`app/services/arxiv_service.py`（新建）

```python
def search_arxiv(query: str, max_results: int = 20) -> list[dict]:
    """
    查询 arXiv Atom API (export.arxiv.org/api/query)
    支持字段限定: au:, ti:, abs:, cat:
    返回: [{title, authors, abstract, arxiv_id, pdf_url, published, categories}]
    """

def download_arxiv_pdf(arxiv_id: str, output_dir: str) -> str:
    """
    下载 arXiv PDF (arxiv.org/pdf/{id}.pdf)
    3 秒礼貌间隔限速
    原子写入: .part 临时文件 → rename
    """
```

#### 2.2 API 端点

```python
@app.get("/api/arxiv/search")
async def search_arxiv_papers(q: str, max_results: int = 20):
    """arXiv 搜索"""

@app.post("/api/arxiv/import")
async def import_from_arxiv(request: Request):
    """
    Body: {"arxiv_id": "2301.xxxxx"}
    下载 PDF + 提取元数据 + 入库
    """
```

#### 2.3 前端：LiteraturePage.tsx 扩展

- 搜索结果来源标签新增 **arXiv**（与现有 7 源并列）
- arXiv 结果显示 `arxiv_id`、分类标签
- **"导入到文献库"** 按钮，点击后自动下载 PDF + 入库
- 已入库的 arXiv 论文标记 `[已导入]`

#### 2.4 依赖

- `defusedxml` — 新增（安全 XML 解析）
- `httpx` — 已有

---

### Phase 3：多源导入

> **目标**：支持从 Zotero、BibTeX/RIS 文件、本地 PDF 批量导入。

#### 3.1 BibTeX/RIS 导入

**后端**：`app/services/import_service.py`（新建）

```python
def parse_bibtex(content: str) -> list[dict]:
    """解析 BibTeX 条目 → [{title, authors, year, doi, journal, ...}]"""

def parse_ris(content: str) -> list[dict]:
    """解析 RIS 条目 → [{title, authors, year, doi, journal, ...}]"""

def import_from_file(file_path: str, session: Session) -> list[dict]:
    """
    自动检测格式（.bib/.ris/.xml）→ 解析 → DOI 去重 → 批量入库
    """
```

**API 端点**：

```python
@app.post("/api/papers/import-bibtex")
async def import_bibtex(file: UploadFile):
    """上传 .bib 文件 → 解析 → 批量入库"""

@app.post("/api/papers/import-ris")
async def import_ris(file: UploadFile):
    """上传 .ris 文件 → 解析 → 批量入库"""
```

**前端**：PaperLibraryPage 工具栏新增 **"导入"** 下拉菜单：
- 导入 PDF 文件
- 导入 BibTeX (.bib)
- 导入 RIS (.ris)
- 从 Zotero 导入

#### 3.2 Zotero 导入（简化版）

ScholarAIO 的 Zotero 导入有两种模式（Web API + 本地 SQLite）。对于桌面应用场景，我们采用**简化方案**：

- **仅支持 Zotero 导出的 BibTeX/RIS 文件**：用户从 Zotero 导出 .bib/.ris 文件，然后通过导入功能加载
- **不直接读取 zotero.sqlite**：需要 pyzotero 依赖 + 用户配置 API Key，复杂度高，用户体验差

> 如果后续有强需求，可以考虑添加 Zotero Web API 集成。

#### 3.3 本地 PDF 批量导入

**API 端点**：

```python
@app.post("/api/papers/batch-import")
async def batch_import_pdfs(files: list[UploadFile]):
    """
    批量上传 PDF → PyMuPDF 提取元数据 → DOI 去重 → 批量入库
    返回: [{paper_id, title, status}]
    """
```

> 注意：此端点在 v3.5.0 已存在（`server.py:2903`），需确认是否完善。

---

### Phase 4：论文笔记系统

> **目标**：为每篇论文提供持久化笔记，跨会话复用。

#### 4.1 数据库模型

**`app/models/paper.py` 扩展**：

```python
class PaperNote(Base):
    __tablename__ = "paper_notes"
    id: str              # UUID
    paper_id: str        # 外键 → Paper.id
    content: str         # Markdown 内容
    created_at: datetime
    updated_at: datetime
```

#### 4.2 服务层

**`app/services/paper_service.py` 扩展**：

```python
def add_note(session, paper_id: str, content: str) -> dict
def update_note(session, note_id: str, content: str) -> dict
def delete_note(session, note_id: str) -> None
def get_notes(session, paper_id: str) -> list[dict]
```

#### 4.3 API 端点

```python
@app.get("/api/papers/{paper_id}/notes")
@app.post("/api/papers/{paper_id}/notes")
@app.put("/api/papers/{paper_id}/notes/{note_id}")
@app.delete("/api/papers/{paper_id}/notes/{note_id}")
```

#### 4.4 前端

PaperLibraryPage 论文详情区新增 **"笔记"** 标签页：
- Markdown 编辑器（复用现有 Markdown 渲染组件）
- 自动保存（失焦或 3 秒防抖）
- 笔记列表（按时间倒序）
- 支持日期标题自动生成：`## YYYY-MM-DD`

---

### Phase 5：元数据质量审计

> **目标**：自动检测低质量元数据，提供一键修复建议。

#### 5.1 审计引擎

**`app/services/audit_service.py`（新建）**：

```python
def audit_papers(session) -> list[dict]:
    """
    规则引擎审计（无 LLM）：
    - 缺失字段: DOI / 摘要 / 年份 / 作者 / 期刊 / 标题
    - 标题一致性: meta.title vs AI summary 的标题
    - DOI 重复检测
    - PDF 缺失检测
    返回: [{paper_id, title, issues: ["missing_doi", "no_abstract", ...]}]
    """

def get_audit_stats(session) -> dict:
    """
    审计统计：
    - 总论文数 / 有问题数 / 无 DOI 数 / 无 PDF 数
    - 按问题类型分组计数
    """
```

#### 5.2 API 端点

```python
@app.get("/api/papers/audit")
async def audit_papers_endpoint():
    """返回所有论文的审计结果"""

@app.get("/api/papers/audit/stats")
async def audit_stats():
    """返回审计统计"""
```

#### 5.3 前端

PaperLibraryPage 新增 **"质量审计"** 面板（侧边栏或顶部卡片）：
- 审计统计卡片（总论文 / 有问题 / 无 DOI / 无 PDF）
- 问题列表（可点击跳转到对应论文）
- 批量修复建议（如批量通过 OpenAlex 补充缺失元数据）

---

### Phase 6：语义近邻推荐 + 工作区搜索增强

#### 6.1 语义近邻推荐

**`app/services/paper_service.py` 扩展**：

```python
def get_semantic_neighbors(session, paper_id: str, top_k: int = 10) -> list[dict]:
    """
    基于 FAISS 向量索引，找到与当前论文语义最相似的论文
    用于论文详情页的"相关论文"推荐
    """
```

**API 端点**：

```python
@app.get("/api/papers/{paper_id}/neighbors")
async def paper_neighbors(paper_id: str, top_k: int = 10):
    """语义近邻推荐"""
```

**前端**：论文详情页新增 **"相关论文"** 卡片。

#### 6.2 工作区限定搜索

**`server.py` 扩展**：

```python
@app.get("/api/workspaces/{workspace_id}/search")
async def workspace_search(workspace_id: str, q: str):
    """
    限定在工作区内搜索（FTS5 + 向量）
    复用现有 search 逻辑，添加 paper_ids 过滤
    """
```

**前端**：工作区详情页新增搜索框。

---

## 三、新增依赖汇总

| 包名 | 版本 | 用途 | 新增/已有 |
|------|------|------|----------|
| `httpx` | latest | HTTP 客户端（PDF 下载、arXiv API） | 已有 |
| `beautifulsoup4` | latest | HTML 解析（PDF 链接提取） | **新增** |
| `lxml` | latest | BS4 解析器 | **新增** |
| `defusedxml` | latest | 安全 XML 解析（arXiv Atom API） | **新增** |
| `bibtexparser` | latest | BibTeX 文件解析 | **新增** |

`build_server.py` 需添加对应 `--hidden-import`。

---

## 四、版本号与发布

| 项目 | 值 |
|------|-----|
| 版本号 | v3.6.0 |
| 主题 | 文献获取与质量管控 |
| 变更类型 | 功能增强（Minor） |

### 发布清单

- [ ] Phase 1-6 代码完成
- [ ] `server.py` 新增端点测试
- [ ] 前端 TypeScript 类型检查通过
- [ ] `build_server.py` 更新 hidden imports
- [ ] `build_tauri.py` 构建测试
- [ ] 版本号更新：`package.json`、`tauri.conf.json`、`CLAUDE.md`、`CHANGELOG.md`
- [ ] Git tag + GitHub release

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 出版社反爬机制 | PDF 拉取失败 | 逐候选 URL 尝试 + User-Agent 伪装 + 超时重试 |
| 校园网外无法访问 | 付费墙阻断 | 提示用户连接校园网 / VPN，或手动上传 PDF |
| arXiv 限速 | 批量导入慢 | 3 秒礼貌间隔 + 进度条显示 |
| BS4/lxml 增加打包体积 | exe 变大 | BS4 ~200KB + lxml ~3MB，可接受 |
| BibTeX 解析边界情况 | 导入失败 | 使用成熟库 bibtexparser + 异常捕获 + 部分导入 |
