import { useState, useEffect, useRef, useCallback } from "react";
import { papersApi, reviewsApi, type PaperDetail, type Review } from "../api/client";
import { IconSearch, IconStar, IconFile, IconUpload, IconX } from "../components/Icons";
import { renderSimpleMarkdown } from "../utils/markdown";

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
  const [copiedDoi, setCopiedDoi] = useState(false);

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
  const bibtexInputRef = useRef<HTMLInputElement>(null);
  const risInputRef = useRef<HTMLInputElement>(null);

  // 分层阅读
  const [readingLevel, setReadingLevel] = useState<number>(1); // 1=元数据, 2=摘要, 3=全文

  // v3.6.0: 出版社 PDF 拉取
  const [showFetchModal, setShowFetchModal] = useState(false);
  const [fetchDoi, setFetchDoi] = useState("");
  const [fetchTitle, setFetchTitle] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchResult, setFetchResult] = useState<string>("");

  // v3.6.0: 导入下拉菜单
  const [showImportMenu, setShowImportMenu] = useState(false);

  // v3.6.0: 元数据审计
  const [auditResults, setAuditResults] = useState<{ paper_id: string; title: string; issues: string[]; severity: string }[]>([]);
  const [auditStats, setAuditStats] = useState<{ total: number; with_issues: number; by_issue_type: Record<string, number>; severity_counts: Record<string, number> } | null>(null);
  const [showAudit, setShowAudit] = useState(false);

  // v3.6.0: 语义近邻推荐
  const [neighbors, setNeighbors] = useState<{ id: string; title: string; authors: string[]; year: number; doi: string; journal: string; score: number }[]>([]);
  const [loadingNeighbors, setLoadingNeighbors] = useState(false);

  // v3.6.0: 笔记列表
  const [notes, setNotes] = useState<{ id: string; content: string; created_at?: string }[]>([]);
  const [newNote, setNewNote] = useState("");

  // v4.1.0: 导入确认对话框
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importQueue, setImportQueue] = useState<{
    file: File; tempId?: string; metadata?: Record<string, unknown>;
    filename?: string; hasText?: boolean; status: "pending"|"extracting"|"ready"|"importing"|"done"|"error"|"duplicate";
    error?: string; duplicatePaper?: PaperDetail;
  }[]>([]);
  const [currentImportIdx, setCurrentImportIdx] = useState(0);
  const [autoFilling, setAutoFilling] = useState(false);

  // v4.1.0: 拖拽上传
  const [dragOver, setDragOver] = useState(false);

  // v4.4.0: 引用格式修正
  const [showCorrectDialog, setShowCorrectDialog] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [correctOldCitation, setCorrectOldCitation] = useState("");
  const [correctNewCitation, setCorrectNewCitation] = useState("");
  const [correctMetadata, setCorrectMetadata] = useState<Record<string, unknown> | null>(null);

  // v4.1.0: 分类系统
  const [categories, setCategories] = useState<{ id: string; name: string; parent_id: string; sort_order: number; is_system: boolean; system_key: string; paper_count: number }[]>([]);

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
  useEffect(() => { papersApi.listCategories().then(setCategories).catch(console.error); }, []);

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

  const handleCopyDoi = () => {
    if (!selected?.doi) return;
    navigator.clipboard.writeText(selected.doi);
    setCopiedDoi(true);
    setTimeout(() => setCopiedDoi(false), 2000);
  };

  // v4.4.0: 引用格式修正
  const handleCorrectCitation = async (method: "doi" | "title") => {
    if (!selectedId) return;
    setCorrecting(true);
    setCorrectOldCitation(citationText);
    setCorrectNewCitation("");
    setCorrectMetadata(null);
    try {
      const result = await papersApi.correctCitation(selectedId, method);
      setCorrectOldCitation(result.old_citation);
      setCorrectNewCitation(result.new_citation);
      setCorrectMetadata(result.metadata);
    } catch (err) {
      alert(`修正失败: ${err}`);
      setShowCorrectDialog(false);
    } finally {
      setCorrecting(false);
    }
  };

  const handleApplyCitation = async () => {
    if (!selectedId || !correctMetadata) return;
    try {
      const updated = await papersApi.applyCitation(selectedId, correctMetadata);
      setPapers(prev => prev.map(p => p.id === selectedId ? updated : p));
      setShowCorrectDialog(false);
      setCorrectMetadata(null);
      // 刷新引用
      papersApi.citation(selectedId, citationFormat).then(r => setCitationText(r.citation)).catch(() => {});
    } catch (err) {
      alert(`应用失败: ${err}`);
    }
  };

  const handleImportPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    startImport(Array.from(files));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // v4.1.0: 分步导入 — 提取元数据 → 确认对话框
  const startImport = async (files: File[]) => {
    const queue = files.map(f => ({ file: f, status: "pending" as const }));
    setImportQueue(queue);
    setCurrentImportIdx(0);
    setShowImportDialog(true);

    // 逐个提取元数据
    for (let i = 0; i < queue.length; i++) {
      setCurrentImportIdx(i);
      setImportQueue(prev => prev.map((item, idx) => idx === i ? { ...item, status: "extracting" } : item));
      try {
        const result = await papersApi.extractMetadata(files[i]);
        if (result.duplicate && result.paper) {
          setImportQueue(prev => prev.map((item, idx) => idx === i ? { ...item, status: "duplicate", duplicatePaper: result.paper } : item));
        } else {
          setImportQueue(prev => prev.map((item, idx) => idx === i ? {
            ...item, status: "ready", tempId: result.temp_id,
            metadata: result.metadata, filename: result.filename, hasText: result.has_text,
          } : item));
        }
      } catch (err) {
        setImportQueue(prev => prev.map((item, idx) => idx === i ? { ...item, status: "error", error: String(err) } : item));
      }
    }
  };

  // 确认导入单个文件
  const confirmImportItem = async (idx: number) => {
    const item = importQueue[idx];
    if (!item.tempId || !item.metadata) return;
    setImportQueue(prev => prev.map((it, i) => i === idx ? { ...it, status: "importing" } : it));
    try {
      const paper = await papersApi.confirmImport(item.tempId, item.metadata, item.filename || "paper.pdf");
      setImportQueue(prev => prev.map((it, i) => i === idx ? { ...it, status: "done" } : it));
      setPapers(prev => [paper, ...prev]);
      setSelectedId(paper.id);
      setShowDetail(true);
    } catch (err) {
      setImportQueue(prev => prev.map((it, i) => i === idx ? { ...it, status: "error", error: String(err) } : it));
    }
  };

  // 全部确认
  const confirmAllImports = async () => {
    for (let i = 0; i < importQueue.length; i++) {
      if (importQueue[i].status === "ready") {
        await confirmImportItem(i);
      }
    }
  };

  // 自动填充元数据
  const handleAutoFill = async (idx: number) => {
    const item = importQueue[idx];
    if (!item.metadata) return;
    setAutoFilling(true);
    try {
      const doi = String(item.metadata.doi || "");
      const title = String(item.metadata.title || "");
      const result = await papersApi.lookupMetadata(doi, title);
      if (result.metadata) {
        const merged = { ...item.metadata } as Record<string, unknown>;
        for (const [key, val] of Object.entries(result.metadata)) {
          if (val && !merged[key]) {
            merged[key] = val;
          }
        }
        setImportQueue(prev => prev.map((it, i) => i === idx ? { ...it, metadata: merged } : it));
      }
    } catch {
      // 静默失败
    }
    setAutoFilling(false);
  };

  // 更新导入队列中的元数据
  const updateImportMeta = (idx: number, field: string, value: unknown) => {
    setImportQueue(prev => prev.map((it, i) => {
      if (i !== idx || !it.metadata) return it;
      return { ...it, metadata: { ...it.metadata, [field]: value } };
    }));
  };

  // v4.1.0: 拖拽上传
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (files.length > 0) {
      startImport(files);
    }
  }, []);

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

  // v3.6.0: 出版社 PDF 拉取
  const handleFetchPdf = async () => {
    if (!fetchDoi && !fetchTitle) return;
    setFetching(true);
    setFetchResult("");
    try {
      const result = await papersApi.fetchPdf(fetchDoi, fetchTitle);
      setPapers(prev => {
        if (prev.some(p => p.id === result.id)) return prev;
        return [result, ...prev];
      });
      setSelectedId(result.id);
      setShowDetail(true);
      setShowFetchModal(false);
      setFetchDoi("");
      setFetchTitle("");
      setFetchResult("拉取成功！");
    } catch (err) {
      setFetchResult(`拉取失败: ${err}`);
    }
    setFetching(false);
  };

  // v3.6.0: BibTeX/RIS 导入
  const handleImportBibtex = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await papersApi.importBibtex(file);
      alert(`导入完成: ${result.imported}/${result.total} 篇成功`);
      loadPapers();
    } catch (err) {
      alert(`导入失败: ${err}`);
    }
    setImporting(false);
    if (bibtexInputRef.current) bibtexInputRef.current.value = "";
  };

  const handleImportRis = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const result = await papersApi.importRis(file);
      alert(`导入完成: ${result.imported}/${result.total} 篇成功`);
      loadPapers();
    } catch (err) {
      alert(`导入失败: ${err}`);
    }
    setImporting(false);
    if (risInputRef.current) risInputRef.current.value = "";
  };

  // v3.6.0: 元数据审计
  const handleAudit = async () => {
    try {
      const [results, stats] = await Promise.all([papersApi.audit(), papersApi.auditStats()]);
      setAuditResults(results.papers);
      setAuditStats(stats);
      setShowAudit(true);
    } catch (err) {
      alert(`审计失败: ${err}`);
    }
  };

  // v3.6.0: 语义近邻推荐
  const loadNeighbors = async (paperId: string) => {
    setLoadingNeighbors(true);
    try {
      const result = await papersApi.neighbors(paperId, 6);
      setNeighbors(result.neighbors || []);
    } catch {
      setNeighbors([]);
    }
    setLoadingNeighbors(false);
  };

  // v3.6.0: 笔记 CRUD
  const loadNotes = async (paperId: string) => {
    try {
      const result = await papersApi.getNotes(paperId);
      setNotes(result || []);
    } catch {
      setNotes([]);
    }
  };

  const handleCreateNote = async () => {
    if (!selectedId || !newNote.trim()) return;
    try {
      const note = await papersApi.createNote(selectedId, newNote);
      setNotes(prev => [note, ...prev]);
      setNewNote("");
    } catch (err) {
      alert(`保存失败: ${err}`);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!selectedId) return;
    try {
      await papersApi.deleteNote(selectedId, noteId);
      setNotes(prev => prev.filter(n => n.id !== noteId));
    } catch (err) {
      alert(`删除失败: ${err}`);
    }
  };

  const openDetail = (id: string) => {
    if (batchMode) return;
    setSelectedId(id);
    setShowDetail(true);
    setEditingNotes(false);
    setCitationFormat("gb7714");
    setReadingLevel(1); // 重置为元数据层
    // v3.6.0: 加载近邻和笔记
    loadNeighbors(id);
    loadNotes(id);
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
        <button className="btn-gradient btn-click text-xs py-2 px-3 flex items-center gap-1" onClick={() => setShowFetchModal(true)}>
          📥 拉取 PDF
        </button>
        <div className="relative">
          <button className="btn-gradient btn-click text-xs py-2 px-3 flex items-center gap-1" onClick={() => setShowImportMenu(!showImportMenu)}>
            <IconUpload size={12} /> {importing ? "导入中..." : "导入"} ▾
          </button>
          {showImportMenu && (
            <div className="absolute right-0 top-full mt-1 z-50 glass-card p-1 min-w-[140px]" style={{ background: "var(--glass-bg)" }}>
              <button className="w-full text-left text-xs px-3 py-2 rounded hover:bg-[var(--hover-bg)] cursor-pointer"
                onClick={() => { fileInputRef.current?.click(); setShowImportMenu(false); }}>📄 导入 PDF</button>
              <button className="w-full text-left text-xs px-3 py-2 rounded hover:bg-[var(--hover-bg)] cursor-pointer"
                onClick={() => { bibtexInputRef.current?.click(); setShowImportMenu(false); }}>📚 导入 BibTeX</button>
              <button className="w-full text-left text-xs px-3 py-2 rounded hover:bg-[var(--hover-bg)] cursor-pointer"
                onClick={() => { risInputRef.current?.click(); setShowImportMenu(false); }}>📋 导入 RIS</button>
            </div>
          )}
        </div>
        <input ref={fileInputRef} type="file" accept=".pdf" multiple className="hidden" onChange={handleImportPdf} />
        <input ref={bibtexInputRef} type="file" accept=".bib,.bibtex" className="hidden" onChange={handleImportBibtex} />
        <input ref={risInputRef} type="file" accept=".ris" className="hidden" onChange={handleImportRis} />
        <button className="btn-ghost text-xs py-2 px-3" onClick={handleAudit}>🔍 审计</button>
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
        {/* 卡片网格（支持拖拽上传） */}
        <div className={`flex-1 overflow-y-auto min-w-0 ${showDetail ? "hidden lg:block" : ""} ${dragOver ? "ring-2 ring-blue-400 ring-opacity-60" : ""}`}
          onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
          {dragOver && (
            <div className="fixed inset-0 z-40 flex items-center justify-center pointer-events-none" style={{ background: "rgba(59,130,246,0.08)" }}>
              <div className="glass-card p-8 text-center" style={{ border: "2px dashed var(--accent-blue)" }}>
                <IconUpload size={40} style={{ color: "var(--accent-blue)", margin: "0 auto" }} />
                <p className="mt-3 text-lg font-semibold" style={{ color: "var(--accent-blue)" }}>拖放 PDF 到此处导入</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>支持多个文件同时导入</p>
              </div>
            </div>
          )}
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

        {/* 详情面板（右侧滑出）— 分层阅读 */}
        {showDetail && selected && (
          <div className="w-full lg:w-[420px] xl:flex-1 xl:max-w-[600px] flex-shrink-0 overflow-y-auto space-y-3 glass-card p-5 max-h-[calc(100vh-200px)]">
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

            {/* 分层阅读导航 */}
            <div className="flex gap-1 p-0.5 rounded-lg" style={{ background: "var(--hover-bg)" }}>
              {[
                { level: 1, label: "元数据" },
                { level: 2, label: "摘要" },
                { level: 3, label: "全文" },
              ].map(item => (
                <button key={item.level}
                  onClick={() => setReadingLevel(item.level)}
                  className="flex-1 text-[10px] py-1.5 rounded-md transition-all cursor-pointer"
                  style={{
                    background: readingLevel === item.level ? "var(--glass-bg)" : "transparent",
                    color: readingLevel === item.level ? "var(--accent-blue)" : "var(--text-muted)",
                    boxShadow: readingLevel === item.level ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  }}>
                  {item.label}
                </button>
              ))}
            </div>

            {/* Level 1: 元数据（始终可见） */}
            <div className="space-y-3">
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
                  <div className="flex gap-1.5 items-center">
                    <select className="input-glass text-[10px] py-1 px-2 h-[28px] leading-none" value={citationFormat}
                      onChange={e => setCitationFormat(e.target.value)}>
                      {CITATION_FORMATS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                    </select>
                    <button className="btn-ghost text-[10px] py-1 px-2 min-w-[52px] h-[28px] leading-none" onClick={handleCopyCitation}>
                      {copied ? "已复制 ✓" : "复制"}
                    </button>
                    <button className="btn-ghost text-[10px] py-1 px-2 min-w-[52px] h-[28px] leading-none" onClick={() => {
                      setShowCorrectDialog(true);
                      setCorrectOldCitation("");
                      setCorrectNewCitation("");
                      setCorrectMetadata(null);
                    }}>
                      修正引用
                    </button>
                  </div>
                </div>
                <pre className="text-[11px] p-2 rounded-lg whitespace-pre-wrap break-all"
                  style={{ background: "var(--hover-bg)", color: "var(--text-secondary)" }}>
                  {citationText || "无引用数据"}
                </pre>
                {/* DOI 行 */}
                {selected.doi && (
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-[11px] font-medium shrink-0" style={{ color: "var(--text-muted)" }}>DOI:</span>
                    <a href={`https://doi.org/${selected.doi}`} target="_blank" rel="noopener"
                      className="text-[11px] truncate flex-1" style={{ color: "var(--accent-blue)" }}>
                      {selected.doi}
                    </a>
                    <button className="btn-ghost text-[10px] py-1 px-2 min-w-[52px] h-[28px] leading-none shrink-0" onClick={handleCopyDoi}>
                      {copiedDoi ? "已复制 ✓" : "复制"}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Level 2: 摘要（需要切换到摘要层） */}
            {readingLevel >= 2 && (
              <div className="space-y-3 pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
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
              </div>
            )}

            {/* Level 3: 全文（需要切换到全文层） */}
            {readingLevel >= 3 && (
              <div className="space-y-3 pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
                {selected.local_path ? (
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>PDF 全文</h3>
                    <div className="rounded-lg overflow-hidden" style={{ background: "var(--hover-bg)" }}>
                      <iframe
                        src={`http://127.0.0.1:8765/api/papers/${selected.id}/pdf`}
                        className="w-full border-0"
                        style={{ height: "500px" }}
                        title="PDF 阅读器"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <IconFile size={32} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
                    <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                      未关联 PDF 文件
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* v3.6.0: 笔记系统（增强版） */}
            <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>📝 笔记</h3>
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
              {/* 笔记列表 */}
              {notes.length > 0 && (
                <div className="space-y-1.5 mt-2">
                  {notes.map(note => (
                    <div key={note.id} className="flex items-start gap-2 p-2 rounded-lg" style={{ background: "var(--hover-bg)" }}>
                      <p className="flex-1 text-[11px] whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>{note.content}</p>
                      <button onClick={() => handleDeleteNote(note.id)}
                        className="text-[10px] cursor-pointer flex-shrink-0" style={{ color: "var(--text-muted)" }}>✕</button>
                    </div>
                  ))}
                </div>
              )}
              {/* 添加笔记 */}
              <div className="flex gap-1 mt-1">
                <input className="input-glass flex-1 text-[11px] py-1" placeholder="添加笔记..."
                  value={newNote} onChange={e => setNewNote(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") handleCreateNote(); }} />
                <button className="btn-ghost text-[10px] py-1 px-2" onClick={handleCreateNote}
                  disabled={!newNote.trim()}>添加</button>
              </div>
            </div>

            {/* v3.6.0: 相关论文 */}
            {neighbors.length > 0 && (
              <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border-color)" }}>
                <h3 className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>🔗 相关论文</h3>
                <div className="space-y-1.5">
                  {neighbors.map(n => (
                    <div key={n.id} className="p-2 rounded-lg cursor-pointer hover:bg-[var(--hover-bg)] transition-colors"
                      onClick={() => openDetail(n.id)}>
                      <p className="text-[11px] font-medium line-clamp-2" style={{ color: "var(--text-primary)" }}>{n.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {n.year > 0 && <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{n.year}</span>}
                        {n.journal && <span className="text-[9px] truncate" style={{ color: "var(--text-muted)" }}>{n.journal}</span>}
                        <span className="text-[9px] ml-auto" style={{ color: "var(--accent-blue)" }}>
                          {(n.score * 100).toFixed(0)}% 相似
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {loadingNeighbors && (
              <p className="text-[10px] text-center py-2" style={{ color: "var(--text-muted)" }}>加载相关论文中...</p>
            )}

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

      {/* v3.6.0: 拉取 PDF 弹窗 */}
      {showFetchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="glass-card p-6 w-[480px]" style={{ background: "var(--glass-bg)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>📥 从出版社拉取 PDF</h3>
              <button onClick={() => { setShowFetchModal(false); setFetchResult(""); }}
                className="cursor-pointer" style={{ color: "var(--text-muted)" }}><IconX size={18} /></button>
            </div>
            <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
              输入 DOI 或论文标题，自动从出版社网站拉取 PDF。需要在校园网环境下使用。
            </p>
            <input className="input-glass mb-2" placeholder="DOI (如 10.1234/abcd)"
              value={fetchDoi} onChange={e => setFetchDoi(e.target.value)} />
            <input className="input-glass mb-3" placeholder="或输入论文标题"
              value={fetchTitle} onChange={e => setFetchTitle(e.target.value)} />
            {fetchResult && (
              <p className="text-xs mb-2" style={{ color: fetchResult.includes("成功") ? "var(--accent-green)" : "#ef4444" }}>
                {fetchResult}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button className="btn-ghost text-xs" onClick={() => { setShowFetchModal(false); setFetchResult(""); }}>取消</button>
              <button className="btn-gradient btn-click text-xs" onClick={handleFetchPdf}
                disabled={fetching || (!fetchDoi && !fetchTitle)}>
                {fetching ? "拉取中..." : "开始拉取"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* v4.1.0: 导入确认对话框 */}
      {showImportDialog && importQueue.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="glass-card p-6 w-[640px] max-h-[85vh] flex flex-col" style={{ background: "var(--glass-bg)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                📄 导入 PDF 确认 {importQueue.length > 1 && `(${currentImportIdx + 1}/${importQueue.length})`}
              </h3>
              <button onClick={() => { setShowImportDialog(false); setImportQueue([]); }}
                className="cursor-pointer" style={{ color: "var(--text-muted)" }}><IconX size={18} /></button>
            </div>

            {/* 文件列表（多文件时显示） */}
            {importQueue.length > 1 && (
              <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
                {importQueue.map((item, idx) => (
                  <button key={idx}
                    onClick={() => setCurrentImportIdx(idx)}
                    className="px-2 py-1 rounded text-[10px] whitespace-nowrap cursor-pointer"
                    style={{
                      background: idx === currentImportIdx ? "var(--accent-blue)" : "var(--hover-bg)",
                      color: idx === currentImportIdx ? "#fff" : "var(--text-secondary)",
                    }}>
                    {item.status === "done" ? "✓" : item.status === "error" ? "✕" : item.status === "extracting" ? "⏳" : ""} {item.file.name.slice(0, 20)}
                  </button>
                ))}
              </div>
            )}

            {/* 当前文件内容 */}
            {(() => {
              const item = importQueue[currentImportIdx];
              if (!item) return null;

              if (item.status === "extracting") {
                return (
                  <div className="text-center py-12">
                    <div className="animate-spin w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full mx-auto" />
                    <p className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>正在提取元数据...</p>
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{item.file.name}</p>
                  </div>
                );
              }

              if (item.status === "error") {
                return (
                  <div className="text-center py-12">
                    <p className="text-sm" style={{ color: "#ef4444" }}>提取失败: {item.error}</p>
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{item.file.name}</p>
                  </div>
                );
              }

              if (item.status === "duplicate" && item.duplicatePaper) {
                return (
                  <div className="text-center py-8">
                    <p className="text-sm" style={{ color: "#f59e0b" }}>⚠️ 文献库中已存在相似文献</p>
                    <p className="text-xs mt-2 font-medium" style={{ color: "var(--text-primary)" }}>{item.duplicatePaper.title}</p>
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{item.duplicatePaper.year} · {item.duplicatePaper.journal}</p>
                  </div>
                );
              }

              if (item.status === "done") {
                return (
                  <div className="text-center py-8">
                    <p className="text-lg" style={{ color: "var(--accent-green)" }}>✅ 导入成功</p>
                  </div>
                );
              }

              if (item.status === "importing") {
                return (
                  <div className="text-center py-12">
                    <div className="animate-spin w-8 h-8 border-2 border-green-400 border-t-transparent rounded-full mx-auto" />
                    <p className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>正在导入...</p>
                  </div>
                );
              }

              // status === "ready" — 显示可编辑元数据
              const meta = item.metadata || {};
              return (
                <div className="flex-1 overflow-y-auto space-y-3">
                  {/* 自动填充按钮 */}
                  <div className="flex justify-end">
                    <button className="btn-ghost text-xs flex items-center gap-1"
                      onClick={() => handleAutoFill(currentImportIdx)} disabled={autoFilling}>
                      {autoFilling ? "查询中..." : "🔄 自动填充元数据"}
                    </button>
                  </div>

                  <div>
                    <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>标题</label>
                    <input className="input-glass text-xs mt-1 w-full" value={String(meta.title || "")}
                      onChange={e => updateImportMeta(currentImportIdx, "title", e.target.value)} />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>作者（逗号分隔）</label>
                    <input className="input-glass text-xs mt-1 w-full"
                      value={Array.isArray(meta.authors) ? meta.authors.join(", ") : String(meta.authors || "")}
                      onChange={e => updateImportMeta(currentImportIdx, "authors", e.target.value.split(",").map(a => a.trim()).filter(Boolean))} />
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>年份</label>
                      <input className="input-glass text-xs mt-1 w-full" type="number" value={Number(meta.year) || ""}
                        onChange={e => updateImportMeta(currentImportIdx, "year", parseInt(e.target.value) || 0)} />
                    </div>
                    <div className="flex-1">
                      <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>DOI</label>
                      <input className="input-glass text-xs mt-1 w-full" value={String(meta.doi || "")}
                        onChange={e => updateImportMeta(currentImportIdx, "doi", e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>期刊</label>
                    <input className="input-glass text-xs mt-1 w-full" value={String(meta.journal || "")}
                      onChange={e => updateImportMeta(currentImportIdx, "journal", e.target.value)} />
                  </div>
                  <div>
                    <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>摘要</label>
                    <textarea className="input-glass text-xs mt-1 w-full" rows={3} value={String(meta.abstract || "")}
                      onChange={e => updateImportMeta(currentImportIdx, "abstract", e.target.value)} />
                  </div>

                  {/* 分类选择 */}
                  {categories.length > 0 && (
                    <div>
                      <label className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>分类</label>
                      <select className="input-glass text-xs mt-1 w-full"
                        onChange={e => {
                          if (e.target.value) {
                            papersApi.setPaperCategories("", [e.target.value]).catch(() => {});
                          }
                        }}>
                        <option value="">不设置分类</option>
                        {categories.filter(c => !c.is_system).map(c => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {item.hasText === false && (
                    <p className="text-[10px]" style={{ color: "#f59e0b" }}>⚠ 该 PDF 可能是扫描版，无法提取文本</p>
                  )}
                </div>
              );
            })()}

            {/* 底部按钮 */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t" style={{ borderColor: "var(--border-color)" }}>
              <div className="flex gap-2">
                {importQueue.length > 1 && (
                  <button className="btn-ghost text-xs" onClick={confirmAllImports}
                    disabled={!importQueue.some(i => i.status === "ready")}>
                    全部确认导入
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <button className="btn-ghost text-xs"
                  onClick={() => { setShowImportDialog(false); setImportQueue([]); }}>
                  取消
                </button>
                {importQueue[currentImportIdx]?.status === "ready" && (
                  <button className="btn-gradient btn-click text-xs"
                    onClick={() => confirmImportItem(currentImportIdx)}>
                    确认导入
                  </button>
                )}
                {importQueue[currentImportIdx]?.status === "done" && currentImportIdx < importQueue.length - 1 && (
                  <button className="btn-gradient btn-click text-xs"
                    onClick={() => setCurrentImportIdx(prev => prev + 1)}>
                    下一个
                  </button>
                )}
                {importQueue.every(i => i.status === "done" || i.status === "error" || i.status === "duplicate") && (
                  <button className="btn-gradient btn-click text-xs"
                    onClick={() => { setShowImportDialog(false); setImportQueue([]); loadPapers(); }}>
                    完成
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* v3.6.0: 审计面板 */}
      {showAudit && auditStats && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="glass-card p-6 w-[600px] max-h-[80vh] flex flex-col" style={{ background: "var(--glass-bg)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>🔍 元数据质量审计</h3>
              <button onClick={() => setShowAudit(false)}
                className="cursor-pointer" style={{ color: "var(--text-muted)" }}><IconX size={18} /></button>
            </div>
            {/* 统计卡片 */}
            <div className="grid grid-cols-4 gap-2 mb-4">
              {[
                { label: "总论文", value: auditStats.total, color: "var(--accent-blue)" },
                { label: "有问题", value: auditStats.with_issues, color: "#f59e0b" },
                { label: "严重", value: auditStats.severity_counts.high || 0, color: "#ef4444" },
                { label: "中等", value: auditStats.severity_counts.medium || 0, color: "#f59e0b" },
              ].map(card => (
                <div key={card.label} className="glass-card p-3 text-center">
                  <p className="text-xl font-bold" style={{ color: card.color }}>{card.value}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{card.label}</p>
                </div>
              ))}
            </div>
            {/* 问题列表 */}
            <div className="flex-1 overflow-y-auto space-y-1" style={{ maxHeight: "400px" }}>
              {auditResults.length === 0 ? (
                <p className="text-center py-8 text-sm" style={{ color: "var(--accent-green)" }}>✅ 所有论文元数据质量良好</p>
              ) : auditResults.map(item => (
                <div key={item.paper_id} className="flex items-start gap-2 p-2 rounded-lg cursor-pointer hover:bg-[var(--hover-bg)]"
                  onClick={() => { openDetail(item.paper_id); setShowAudit(false); }}>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full mt-0.5"
                    style={{
                      background: item.severity === "high" ? "rgba(239,68,68,0.1)" : item.severity === "medium" ? "rgba(245,158,11,0.1)" : "rgba(107,114,128,0.1)",
                      color: item.severity === "high" ? "#ef4444" : item.severity === "medium" ? "#f59e0b" : "var(--text-muted)",
                    }}>{item.severity}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{item.title}</p>
                    <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{item.issues.join(", ")}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* v4.4.0: 引用格式修正对话框 */}
      {showCorrectDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.5)" }}>
          <div className="glass-card p-6 w-[560px] max-h-[80vh] flex flex-col" style={{ background: "var(--glass-bg)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>修正引用格式</h3>
              <button onClick={() => { setShowCorrectDialog(false); setCorrectMetadata(null); }}
                className="cursor-pointer" style={{ color: "var(--text-muted)" }}><IconX size={18} /></button>
            </div>

            {/* 选择修正方式 */}
            {!correctNewCitation && !correcting && (
              <div className="space-y-3">
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  选择修正方式，将通过外部数据源重新获取元数据并生成 GB/T 7714 引用格式。
                </p>
                {/* 当前引用预览 */}
                <div>
                  <p className="text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>当前引用:</p>
                  <pre className="text-[10px] p-2 rounded-lg whitespace-pre-wrap break-all"
                    style={{ background: "var(--hover-bg)", color: "var(--text-secondary)" }}>
                    {correctOldCitation || citationText || "无引用数据"}
                  </pre>
                </div>
                <div className="flex gap-3">
                  <button className="btn-gradient btn-click text-sm flex-1 py-2"
                    onClick={() => handleCorrectCitation("doi")}
                    disabled={!selected?.doi}>
                    按 DOI 修正 {selected?.doi ? `(${selected.doi})` : "(无DOI)"}
                  </button>
                  <button className="btn-gradient btn-click text-sm flex-1 py-2"
                    onClick={() => handleCorrectCitation("title")}>
                    按标题修正
                  </button>
                </div>
              </div>
            )}

            {/* 加载中 */}
            {correcting && (
              <div className="text-center py-8">
                <div className="animate-spin w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full mx-auto" />
                <p className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>正在从外部数据源获取元数据...</p>
              </div>
            )}

            {/* 修正结果对比 */}
            {correctNewCitation && !correcting && (
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>旧引用:</p>
                  <pre className="text-[10px] p-2 rounded-lg whitespace-pre-wrap break-all"
                    style={{ background: "rgba(239,68,68,0.05)", color: "var(--text-muted)" }}>
                    {correctOldCitation}
                  </pre>
                </div>
                <div>
                  <p className="text-xs font-medium mb-1" style={{ color: "var(--accent-green)" }}>新引用:</p>
                  <pre className="text-[10px] p-2 rounded-lg whitespace-pre-wrap break-all"
                    style={{ background: "rgba(16,185,129,0.05)", color: "var(--text-primary)" }}>
                    {correctNewCitation}
                  </pre>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button className="btn-ghost text-xs" onClick={() => { setShowCorrectDialog(false); setCorrectMetadata(null); }}>
                    取消
                  </button>
                  <button className="btn-gradient btn-click text-xs" onClick={handleApplyCitation}>
                    确认应用
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
