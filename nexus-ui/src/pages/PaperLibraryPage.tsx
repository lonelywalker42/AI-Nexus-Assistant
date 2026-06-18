import { useState, useEffect, useRef } from "react";
import { papersApi, reviewsApi, type PaperDetail, type Review } from "../api/client";
import { IconSearch, IconStar, IconFile, IconUpload, IconX } from "../components/Icons";

const SORT_OPTIONS = [
  { value: "created_at", label: "入库时间" },
  { value: "year", label: "年份" },
  { value: "star_rating", label: "评分" },
  { value: "title", label: "标题" },
];

const CITATION_FORMATS = [
  { value: "gb7714", label: "GB/T 7714" },
  { value: "apa", label: "APA" },
  { value: "ieee", label: "IEEE" },
  { value: "mla", label: "MLA" },
  { value: "bibtex", label: "BibTeX" },
];

export default function PaperLibraryPage() {
  const [papers, setPapers] = useState<PaperDetail[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [loading, setLoading] = useState(false);

  // 详情面板
  const [showDetail, setShowDetail] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState("");
  const [citationFormat, setCitationFormat] = useState("gb7714");
  const [citationText, setCitationText] = useState("");
  const [copied, setCopied] = useState(false);

  // 综述
  const [reviews, setReviews] = useState<Review[]>([]);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [selectedForReview, setSelectedForReview] = useState<string[]>([]);
  const [reviewTitle, setReviewTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [reviewContent, setReviewContent] = useState("");

  // 批量选择
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // PDF 导入
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const selected = papers.find(p => p.id === selectedId);

  const loadPapers = () => {
    setLoading(true);
    papersApi.list({ search, sort_by: sortBy, sort_order: sortOrder })
      .then(result => {
        setPapers(prev => {
          // 合并服务器结果与本地新增（防止竞态覆盖）
          const serverIds = new Set(result.map((p: PaperDetail) => p.id));
          const localOnly = prev.filter(p => !serverIds.has(p.id));
          return [...result, ...localOnly];
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadPapers(); }, [search, sortBy, sortOrder]);
  useEffect(() => { reviewsApi.list().then(setReviews).catch(console.error); }, []);

  // 加载引用
  useEffect(() => {
    if (selectedId) {
      papersApi.citation(selectedId, citationFormat).then(r => setCitationText(r.citation)).catch(() => setCitationText(""));
    }
  }, [selectedId, citationFormat]);

  const handleStar = async (id: string, rating: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    await papersApi.update(id, { star_rating: rating } as Partial<PaperDetail>);
    setPapers(prev => prev.map(p => p.id === id ? { ...p, star_rating: rating } : p));
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此文献？")) return;
    await papersApi.delete(id);
    setPapers(prev => prev.filter(p => p.id !== id));
    if (selectedId === id) { setSelectedId(null); setShowDetail(false); }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确定删除 ${selectedIds.size} 篇文献？`)) return;
    await papersApi.batchDelete(Array.from(selectedIds));
    setPapers(prev => prev.filter(p => !selectedIds.has(p.id)));
    setSelectedIds(new Set());
    setBatchMode(false);
    if (selectedId && selectedIds.has(selectedId)) { setSelectedId(null); setShowDetail(false); }
  };

  const handleSaveNotes = async () => {
    if (!selectedId) return;
    await papersApi.update(selectedId, { user_notes: notesValue } as Partial<PaperDetail>);
    setPapers(prev => prev.map(p => p.id === selectedId ? { ...p, user_notes: notesValue } : p));
    setEditingNotes(false);
  };

  const handleAiSummary = async (id: string) => {
    setPapers(prev => prev.map(p => p.id === id ? { ...p, ai_summary: "生成中..." } : p));
    try {
      const res = await papersApi.aiSummary(id);
      setPapers(prev => prev.map(p => p.id === id ? { ...p, ai_summary: res.ai_summary } : p));
    } catch {
      setPapers(prev => prev.map(p => p.id === id ? { ...p, ai_summary: "生成失败" } : p));
    }
  };

  const handleCopyCitation = () => {
    navigator.clipboard.writeText(citationText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleImportPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setImporting(true);
    for (const file of Array.from(files)) {
      try {
        const bytes = await file.arrayBuffer();
        const res = await fetch("http://127.0.0.1:8765/api/papers/import-pdf", {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(file.name) },
          body: bytes,
        });
        const data = await res.json();
        if (data.error) {
          alert(`导入失败: ${data.error}`);
        } else {
          setPapers(prev => [data, ...prev]);
          setSelectedId(data.id);
          setShowDetail(true);
        }
      } catch (err) {
        alert(`导入失败: ${err}`);
      }
    }
    setImporting(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleGenerateReview = async () => {
    if (selectedForReview.length === 0) return;
    setGenerating(true);
    setReviewContent("");
    let fullContent = "";
    try {
      for await (const chunk of reviewsApi.generate(selectedForReview, reviewTitle)) {
        if (chunk.type === "content") {
          fullContent += chunk.data;
          setReviewContent(fullContent);
        }
      }
      reviewsApi.list().then(setReviews).catch(console.error);
    } catch (err) {
      setReviewContent(`生成失败: ${err}`);
    }
    setGenerating(false);
  };

  const toggleBatchSelect = (id: string, e?: React.SyntheticEvent) => {
    e?.stopPropagation();
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const openDetail = (id: string) => {
    if (batchMode) return;
    setSelectedId(id);
    setShowDetail(true);
    setEditingNotes(false);
    setCitationFormat("gb7714");
  };

  const getSourceColor = (source: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      openalex: { bg: "rgba(59,130,246,0.1)", text: "var(--accent-blue)" },
      arxiv: { bg: "rgba(239,68,68,0.1)", text: "#ef4444" },
      semantic_scholar: { bg: "rgba(16,185,129,0.1)", text: "var(--accent-green)" },
      crossref: { bg: "rgba(245,158,11,0.1)", text: "#f59e0b" },
      pubmed: { bg: "rgba(139,92,246,0.1)", text: "#8b5cf6" },
      pdf_import: { bg: "rgba(107,114,128,0.1)", text: "var(--text-muted)" },
    };
    return colors[source] || { bg: "rgba(107,114,128,0.1)", text: "var(--text-muted)" };
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* 顶部工具栏 */}
      <div className="flex gap-2 items-center flex-wrap">
        <div className="relative flex-1 min-w-48">
          <IconSearch size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input className="input-glass pl-8 w-full text-sm" placeholder="搜索文献..."
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input-glass text-xs py-2 w-24" value={sortBy} onChange={e => setSortBy(e.target.value)}>
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button className="btn-ghost text-xs px-2 py-2" onClick={() => setSortOrder(o => o === "desc" ? "asc" : "desc")}
          title={sortOrder === "desc" ? "降序" : "升序"}>
          {sortOrder === "desc" ? "↓" : "↑"}
        </button>
        <button className="btn-gradient btn-click text-xs py-2 px-3 flex items-center gap-1" onClick={() => fileInputRef.current?.click()}>
          <IconUpload size={12} /> {importing ? "导入中..." : "导入 PDF"}
        </button>
        <input ref={fileInputRef} type="file" accept=".pdf" multiple className="hidden" onChange={handleImportPdf} />
        <button className={`btn-ghost text-xs py-2 ${batchMode ? "!bg-red-500 !text-white" : ""}`}
          onClick={() => { setBatchMode(!batchMode); setSelectedIds(new Set()); }}>
          {batchMode ? "取消" : "批量"}
        </button>
        {batchMode && selectedIds.size > 0 && (
          <button className="btn-ghost text-xs py-2 !bg-red-500 !text-white" onClick={handleBatchDelete}>
            删除 ({selectedIds.size})
          </button>
        )}
      </div>

      {/* 统计信息 */}
      <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
        <span>共 {papers.length} 篇文献</span>
        <span>·</span>
        <span>{papers.filter(p => p.star_rating > 0).length} 篇已评分</span>
        {papers.filter(p => p.ai_summary).length > 0 && (
          <>
            <span>·</span>
            <span>{papers.filter(p => p.ai_summary).length} 篇有 AI 摘要</span>
          </>
        )}
        <div className="flex-1" />
        <button className="btn-ghost text-xs" onClick={() => { setSelectedForReview([]); setShowReviewModal(true); }}>
          生成综述
        </button>
      </div>

      {/* 卡片网格 + 详情面板 */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* 卡片网格 */}
        <div className={`flex-1 overflow-y-auto ${showDetail ? "hidden lg:block lg:w-0 lg:flex-none" : ""}`}>
          {loading && <p className="text-xs text-center py-8" style={{ color: "var(--text-muted)" }}>加载中...</p>}

          {!loading && papers.length === 0 && (
            <div className="text-center py-16">
              <IconFile size={40} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
              <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>暂无文献</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>导入 PDF 或从搜索结果入库</p>
            </div>
          )}

          {!loading && papers.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {papers.map(p => (
                <div key={p.id}
                  onClick={(e) => batchMode ? toggleBatchSelect(p.id, e) : openDetail(p.id)}
                  className="glass-card p-4 cursor-pointer transition-all hover:scale-[1.01] flex flex-col gap-2 relative group"
                  style={selectedId === p.id ? { borderLeft: "3px solid var(--accent-blue)" } : {}}
                >
                  {/* 批量选择复选框 */}
                  {batchMode && (
                    <div className="absolute top-3 left-3">
                      <input type="checkbox" checked={selectedIds.has(p.id)}
                        onChange={() => toggleBatchSelect(p.id)}
                        className="rounded" onClick={e => e.stopPropagation()} />
                    </div>
                  )}

                  {/* 标题 */}
                  <h3 className="text-sm font-semibold leading-snug line-clamp-2 pr-6"
                    style={{ color: "var(--text-primary)" }}>
                    {batchMode && <span className="w-5 inline-block" />}
                    {p.title}
                  </h3>

                  {/* 来源标签 + 星级 */}
                  <div className="flex items-center justify-between">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                      style={{ background: getSourceColor(p.source).bg, color: getSourceColor(p.source).text }}>
                      {p.source || "未知"}
                    </span>
                    <div className="flex items-center gap-0.5">
                      {[1, 2, 3, 4, 5].map(s => (
                        <button key={s} onClick={(e) => handleStar(p.id, s === p.star_rating ? 0 : s, e)}
                          className="cursor-pointer">
                          <IconStar size={10} filled={s <= p.star_rating}
                            style={{ color: s <= p.star_rating ? "#f59e0b" : "var(--text-muted)" }} />
                        </button>
                      ))}
                      {p.ai_summary && (
                        <span className="ml-1 text-[10px] px-1 rounded"
                          style={{ background: "rgba(16,185,129,0.1)", color: "#10b981" }}>AI</span>
                      )}
                    </div>
                  </div>

                  {/* 作者 + 年份 + 期刊 */}
                  <div className="text-xs line-clamp-1" style={{ color: "var(--text-secondary)" }}>
                    {p.authors.length > 0 && <span>{p.authors.slice(0, 3).join(", ")}{p.authors.length > 3 ? " 等" : ""}</span>}
                    {p.year > 0 && <span> · {p.year}</span>}
                    {p.journal && <span> · {p.journal}</span>}
                  </div>

                  {/* 摘要预览 */}
                  {(p.ai_summary || p.abstract) && (
                    <p className="text-[11px] leading-relaxed line-clamp-3"
                      style={{ color: "var(--text-muted)" }}>
                      {p.ai_summary || p.abstract}
                    </p>
                  )}

                  {/* 标签 */}
                  {p.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-auto">
                      {p.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="px-1.5 py-0.5 rounded text-[9px]"
                          style={{ background: "rgba(59,130,246,0.06)", color: "var(--accent-blue)" }}>
                          {tag}
                        </span>
                      ))}
                      {p.tags.length > 3 && (
                        <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>+{p.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 详情面板（右侧滑出） */}
        {showDetail && selected && (
          <div className="w-full lg:w-[380px] xl:w-[420px] flex-shrink-0 overflow-y-auto space-y-3 glass-card p-5 max-h-[calc(100vh-200px)]">
            {/* 关闭按钮 */}
            <div className="flex items-start justify-between">
              <h2 className="text-base font-bold leading-relaxed flex-1 pr-2" style={{ color: "var(--text-primary)" }}>
                {selected.title}
              </h2>
              <button onClick={() => { setShowDetail(false); setSelectedId(null); }}
                className="flex-shrink-0 cursor-pointer p-1 rounded-lg transition-colors"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                <IconX size={16} />
              </button>
            </div>

            {/* 基本信息 */}
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs" style={{ color: "var(--text-secondary)" }}>
              {selected.authors.length > 0 && <span>{selected.authors.slice(0, 5).join(", ")}{selected.authors.length > 5 ? " 等" : ""}</span>}
              {selected.year > 0 && <span>{selected.year}</span>}
              {selected.journal && <span>{selected.journal}</span>}
              {selected.doi && <a href={`https://doi.org/${selected.doi}`} target="_blank" rel="noopener"
                className="text-xs" style={{ color: "var(--accent-blue)" }}>DOI: {selected.doi}</a>}
            </div>

            {/* 评分 */}
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>评分:</span>
              {[1, 2, 3, 4, 5].map(s => (
                <button key={s} onClick={() => handleStar(selected.id, s === selected.star_rating ? 0 : s)}
                  className="cursor-pointer">
                  <IconStar size={14} filled={s <= selected.star_rating}
                    style={{ color: s <= selected.star_rating ? "#f59e0b" : "var(--text-muted)" }} />
                </button>
              ))}
            </div>

            {/* 标签 */}
            {selected.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {selected.tags.map(tag => (
                  <span key={tag} className="px-2 py-0.5 rounded-full text-[10px]"
                    style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>{tag}</span>
                ))}
              </div>
            )}

            {/* 引用 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>引用格式</h3>
                <div className="flex gap-2 items-center">
                  <select className="input-glass text-[10px] py-1" value={citationFormat}
                    onChange={e => setCitationFormat(e.target.value)}>
                    {CITATION_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                  </select>
                  <button className="btn-ghost text-[10px] py-1" onClick={handleCopyCitation}>
                    {copied ? "已复制 ✓" : "复制"}
                  </button>
                </div>
              </div>
              <pre className="text-[10px] p-2 rounded-lg whitespace-pre-wrap break-all"
                style={{ background: "var(--hover-bg)", color: "var(--text-secondary)" }}>
                {citationText || "无引用数据"}
              </pre>
            </div>

            {/* AI 摘要 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>AI 摘要</h3>
                <button className="btn-ghost text-[10px] py-1" onClick={() => handleAiSummary(selected.id)}>
                  {selected.ai_summary ? "重新生成" : "生成摘要"}
                </button>
              </div>
              <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                {selected.ai_summary || "未生成 AI 摘要"}
              </p>
            </div>

            {/* 原始摘要 */}
            {selected.abstract && (
              <div className="space-y-1">
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>原始摘要</h3>
                <p className="text-[11px]" style={{ color: "var(--text-secondary)" }}>{selected.abstract}</p>
              </div>
            )}

            {/* 笔记 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>笔记</h3>
                {!editingNotes ? (
                  <button className="btn-ghost text-[10px] py-1" onClick={() => { setNotesValue(selected.user_notes); setEditingNotes(true); }}>
                    编辑
                  </button>
                ) : (
                  <div className="flex gap-1">
                    <button className="btn-ghost text-[10px] py-1" onClick={handleSaveNotes}>保存</button>
                    <button className="btn-ghost text-[10px] py-1" onClick={() => setEditingNotes(false)}>取消</button>
                  </div>
                )}
              </div>
              {editingNotes ? (
                <textarea className="input-glass" rows={3} value={notesValue}
                  onChange={e => setNotesValue(e.target.value)} />
              ) : (
                <p className="text-xs" style={{ color: selected.user_notes ? "var(--text-secondary)" : "var(--text-muted)" }}>
                  {selected.user_notes || "暂无笔记"}
                </p>
              )}
            </div>

            {/* 关联综述 */}
            {selected.review_id && (() => {
              const review = reviews.find(r => r.id === selected.review_id);
              return review ? (
                <div className="space-y-1">
                  <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>关联综述</h3>
                  <p className="text-xs" style={{ color: "var(--accent-blue)" }}>{review.title}</p>
                </div>
              ) : null;
            })()}

            {/* 删除按钮 */}
            <div className="pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
              <button onClick={() => handleDelete(selected.id)}
                className="text-xs transition-colors cursor-pointer"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
              >删除此文献</button>
            </div>
          </div>
        )}
      </div>

      {/* 综述生成弹窗 */}
      {showReviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="glass-card p-6 w-[600px] max-h-[80vh] flex flex-col" style={{ background: "var(--glass-bg)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>生成文献综述</h3>
              <button onClick={() => { setShowReviewModal(false); setReviewContent(""); }}
                className="cursor-pointer" style={{ color: "var(--text-muted)" }}><IconX size={18} /></button>
            </div>

            <input className="input-glass mb-3" placeholder="综述标题（可选）"
              value={reviewTitle} onChange={e => setReviewTitle(e.target.value)} />

            <div className="flex-1 overflow-y-auto space-y-1.5 mb-4" style={{ maxHeight: "300px" }}>
              {papers.map(p => (
                <label key={p.id} className="flex items-start gap-2 cursor-pointer p-2 rounded-lg"
                  style={{ background: selectedForReview.includes(p.id) ? "rgba(59,130,246,0.1)" : "transparent" }}>
                  <input type="checkbox" checked={selectedForReview.includes(p.id)}
                    onChange={e => {
                      if (e.target.checked) setSelectedForReview(prev => [...prev, p.id]);
                      else setSelectedForReview(prev => prev.filter(id => id !== p.id));
                    }}
                    className="mt-1 rounded" />
                  <div>
                    <p className="text-sm" style={{ color: "var(--text-primary)" }}>{p.title}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{p.year} · {p.journal}</p>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>已选 {selectedForReview.length} 篇</span>
              <div className="flex gap-2">
                <button className="btn-ghost text-xs" onClick={() => { setShowReviewModal(false); setReviewContent(""); }}>取消</button>
                <button className="btn-gradient btn-click text-xs"
                  onClick={handleGenerateReview} disabled={selectedForReview.length === 0 || generating}>
                  {generating ? "生成中..." : "生成综述"}
                </button>
              </div>
            </div>

            {reviewContent && (
              <div className="mt-4 p-4 rounded-lg overflow-y-auto" style={{ background: "var(--hover-bg)", maxHeight: "400px" }}>
                <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(reviewContent) }} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function renderSimpleMarkdown(md: string): string {
  if (!md) return "";
  const codeBlocks: string[] = [];
  let result = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="lang-${escapeHtml(lang)}">${escapeHtml(code.trim())}</code></pre>`);
    return `__CODEBLOCK_${idx}__`;
  });
  result = result.replace(/(?:^|\n)(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g, (_, header, _sep, body) => {
    const ths = header.split("|").filter((c: string) => c.trim()).map((c: string) => `<th>${c.trim()}</th>`).join("");
    const rows = body.trim().split("\n").map((row: string) => {
      const tds = row.split("|").filter((c: string) => c.trim()).map((c: string) => `<td>${c.trim()}</td>`).join("");
      return `<tr>${tds}</tr>`;
    }).join("");
    return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
  });
  result = result.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
  result = result.replace(/^- (.+)$/gm, '<li>$1</li>');
  result = result.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  result = result.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  result = result.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  result = result.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
  result = result.replace(/^---$/gm, '<hr>');
  result = result.replace(/\n\n/g, '</p><p>');
  result = result.replace(/\n/g, '<br>');
  result = result.replace(/__CODEBLOCK_(\d+)__/g, (_, idx) => codeBlocks[parseInt(idx)]);
  return result;
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
