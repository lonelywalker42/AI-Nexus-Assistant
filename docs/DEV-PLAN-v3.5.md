# 开发计划：v3.6.0 — ScholarAIO 特性移植

> 基于 `docs/SCHOLARAIO_REFERENCE.md` 的深度分析，筛选适合 AI Nexus Assistant（Tauri 桌面应用架构）的特性，制定可落地的开发计划。

## 一、可行性分析

### 架构差异

| 维度 | ScholarAIO | AI Nexus Assistant |
|------|-----------|-------------------|
| 形态 | Agent-first CLI + Claude Code Skills | Tauri 桌面应用（React + FastAPI） |
| 交互 | 自然语言驱动，Agent 调用 skill | GUI 点击操作 |
| PDF 解析 | MinerU（重依赖，~2GB） | PyMuPDF（内置）+ MinerU（可选安装） |
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
| **MinerU PDF 解析** | ⭐⭐⭐⭐⭐ | 中 | ✅ 可选安装 + 优雅降级 | **纳入** |
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

### Phase 1.5：MinerU PDF→Markdown 结构化转换

> **目标**：将 PDF 转换为结构化 Markdown（保留公式、图片、表格、版面结构），供 LLM 高质量阅读。采用**可选安装 + 优雅降级**策略。

#### 为什么需要 MinerU

当前系统使用 PyMuPDF 提取 PDF 文本，存在以下问题：
- **公式丢失**：数学公式变成乱码纯文本
- **表格破碎**：多栏表格变成无结构文本流
- **版面混乱**：双栏论文的左右栏文本混在一起
- **图片丢失**：无法提取图片和图注

MinerU（`magic-pdf`）解决这些问题，输出结构化 Markdown，LLM 可直接高质量阅读。

#### 架构设计：三级降级

```
用户触发 PDF→Markdown 转换
    │
    ├─ MinerU 已安装？
    │   ├─ 是 → MinerU 转换（最优质量）
    │   │       └─ 失败？→ 降级到 PyMuPDF
    │   └─ 否 → PyMuPDF 提取（基础质量）
    │           └─ 显示提示："安装 MinerU 可获得更好的转换质量"
    │
    └─ 输出: paper.md 存储到论文目录
```

#### 1.5.1 后端：`app/services/pdf_converter.py`（新建）

```python
def check_mineru_available() -> bool:
    """检测 MinerU 是否已安装（import magic_pdf）"""

def convert_pdf_to_markdown(pdf_path: str, output_dir: str) -> dict:
    """
    自动选择转换器：
    1. MinerU 可用 → magic_pdf 转换（保留公式/图片/表格）
    2. MinerU 不可用 → PyMuPDF 提取纯文本
    返回: {"method": "mineru"|"pymupdf", "output_path": str, "pages": int}
    """

def _convert_with_mineru(pdf_path: str, output_dir: str) -> dict:
    """
    调用 magic_pdf API：
    - 解析 PDF → 结构化中间表示
    - 输出 Markdown（含 LaTeX 公式、Markdown 表格、图片引用）
    - 保留章节层级（H1/H2/H3）
    """

def _convert_with_pymupdf(pdf_path: str, output_dir: str) -> dict:
    """
    PyMuPDF 降级方案：
    - 逐页提取文本块
    - 按阅读顺序排列（处理双栏）
    - 输出纯文本 Markdown（无公式/图片）
    """
```

#### 1.5.2 MinerU 安装管理

**设置页面**新增 MinerU 区域：
- 状态指示：✅ 已安装 / ❌ 未安装
- 安装按钮：`pip install magic-pdf[full]`（带进度条）
- 卸载按钮
- 说明文字：*"MinerU 可将 PDF 高质量转换为 Markdown，保留公式、图片和表格。安装后 LLM 阅读论文效果显著提升。约需 2GB 磁盘空间。"*

**API 端点**：

```python
@app.get("/api/system/mineru-status")
async def mineru_status():
    """返回 MinerU 安装状态: {"available": true/false, "version": "..."}"""

@app.post("/api/system/install-mineru")
async def install_mineru():
    """
    后台安装 MinerU: pip install magic-pdf[full]
    SSE 返回安装进度
    """
```

#### 1.5.3 与阅读流程集成

**论文入库时**自动触发转换：
```
PDF 导入/拉取 → 提取元数据 → 创建 Paper 记录 → 后台触发 PDF→Markdown 转换
                                                            │
                                                            └─ paper.md 存储到论文目录
```

**LLM 阅读时**优先使用 Markdown：
- AI 摘要生成：读取 `paper.md` 而非原始 PDF
- AI 对话引用：基于 Markdown 内容回答
- 分层阅读 L4（全文）：显示渲染后的 Markdown 而非 PDF iframe

**批量转换**：设置页面提供"批量转换所有 PDF"按钮，对已有论文库执行一次性转换。

#### 1.5.4 前端：阅读体验升级

PaperLibraryPage 分层阅读调整：
- **L3（全文）**：两个子标签
  - **Markdown 视图**（默认）：渲染后的 Markdown，含公式（KaTeX）、表格、图片
  - **PDF 预览**：原始 PDF iframe（保留，用于查看排版）
- 如果 `paper.md` 不存在，显示"未转换"提示 + "立即转换"按钮
- 如果使用 PyMuPDF 降级转换，显示提示"安装 MinerU 可获得更好的转换质量"

#### 1.5.5 依赖与打包

| 方案 | 安装方式 | 包体积 | 转换质量 |
|------|---------|--------|---------|
| **基础（默认）** | PyMuPDF（已有） | 0 | ⭐⭐ 纯文本 |
| **增强（可选）** | `pip install magic-pdf[full]` | ~2GB | ⭐⭐⭐⭐⭐ 结构化 Markdown |

**打包策略**：MinerU **不包含**在 exe 中，作为可选运行时依赖。用户在设置页面按需安装。这避免了 exe 体积从 51MB 膨胀到 2GB+。

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

| 包名 | 版本 | 用途 | 新增/已有 | 打包策略 |
|------|------|------|----------|---------|
| `httpx` | latest | HTTP 客户端（PDF 下载、arXiv API） | 已有 | 内置 |
| `beautifulsoup4` | latest | HTML 解析（PDF 链接提取） | **新增** | 内置 |
| `lxml` | latest | BS4 解析器 | **新增** | 内置 |
| `defusedxml` | latest | 安全 XML 解析（arXiv Atom API） | **新增** | 内置 |
| `bibtexparser` | latest | BibTeX 文件解析 | **新增** | 内置 |
| `magic-pdf[full]` | latest | PDF→Markdown 结构化转换（MinerU） | **新增** | **可选运行时**（~2GB，用户按需安装） |

`build_server.py` 需添加对应 `--hidden-import`（不含 magic-pdf，它是运行时可选依赖）。

---

## 四、版本号与发布

| 项目 | 值 |
|------|-----|
| 版本号 | v3.6.0 |
| 主题 | 文献获取 + PDF 结构化转换 + 质量管控 |
| 变更类型 | 功能增强（Minor） |

### 发布清单

- [ ] Phase 1 ~ 1.5 ~ 2-6 代码完成
- [ ] MinerU 可选安装 + PyMuPDF 降级验证
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
| MinerU 安装失败 | 无法使用 PDF→Markdown | PyMuPDF 降级方案兜底，不影响核心功能 |
| MinerU 转换耗时长 | 批量转换慢 | 后台异步转换 + 进度显示 + 单篇转换优先 |
| MinerU 模型下载 | 首次使用需下载模型 | 设置页面提示 + 下载进度条 |
