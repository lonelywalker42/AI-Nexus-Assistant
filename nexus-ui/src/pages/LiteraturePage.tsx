import { useState, useEffect, useRef } from "react";
import { searchApi, historyApi, chatApi, modelsApi, knowledgeApi, papersApi, enhancedSearchApi, type Paper, type HistoryRecord, type ModelConfig, type KnowledgeCard } from "../api/client";
import { IconSearch, IconChevronRight, IconSparkle, IconBookmark, IconList, IconGrid, IconUpload, IconFilter, IconGlobe, IconX } from "../components/Icons";

const SOURCES = [
  { key: "openalex", label: "OpenAlex", default: true },
  { key: "arxiv", label: "arXiv", default: true },
  { key: "semantic_scholar", label: "Semantic Scholar", default: true },
  { key: "crossref", label: "CrossRef", default: false },
  { key: "pubmed", label: "PubMed", default: false },
  { key: "google_scholar", label: "Google Scholar", default: false },
  { key: "scopus", label: "Scopus", default: false },
];

const SOURCE_COLORS: Record<string, { bg: string; text: string }> = {
  openalex: { bg: "rgba(59,130,246,0.1)", text: "#3b82f6" },
  arxiv: { bg: "rgba(239,68,68,0.1)", text: "#ef4444" },
  semantic_scholar: { bg: "rgba(16,185,129,0.1)", text: "#10b981" },
  crossref: { bg: "rgba(245,158,11,0.1)", text: "#f59e0b" },
  pubmed: { bg: "rgba(139,92,246,0.1)", text: "#8b5cf6" },
  google_scholar: { bg: "rgba(59,130,246,0.08)", text: "#6366f1" },
  scopus: { bg: "rgba(236,72,153,0.1)", text: "#ec4899" },
};

export default function LiteraturePage() {
  const [tab, setTab] = useState<"search" | "review" | "topic" | "history">("search");
  const [keywords, setKeywords] = useState([""]);
  // Boolean search: operators between keyword rows
  const [operators, setOperators] = useState<string[]>([]); // AND/OR/NOT between rows
  const [useBoolean, setUseBoolean] = useState(false);
  // Batch import
  const [batchImporting, setBatchImporting] = useState(false);
  // Smart review sections
  const [customSections, setCustomSections] = useState(["研究背景", "研究现状", "方法对比", "研究趋势", "关键结论"]);
  const [showSectionEditor, setShowSectionEditor] = useState(false);
  const [selectedSources, setSelectedSources] = useState(SOURCES.filter(s => s.default).map(s => s.key));
  const [results, setResults] = useState<Paper[]>([]);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState("");

  // 新增：视图模式、筛选展开、摘要展开、综述池
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [showFilters, setShowFilters] = useState(false);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Set<number>>(new Set());
  const [reviewPool, setReviewPool] = useState<Set<number>>(new Set());
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // AI 综述
  const [reviewInput, setReviewInput] = useState("");
  const [reviewContent, setReviewContent] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [reviewSource, setReviewSource] = useState<"search" | "kb" | "custom">("search");
  const [kbCards, setKbCards] = useState<KnowledgeCard[]>([]);
  const [selectedKbCards, setSelectedKbCards] = useState<string[]>([]);

  // 选题讨论
  const [topicInput, setTopicInput] = useState("");
  const [topicContent, setTopicContent] = useState("");
  const [discussing, setDiscussing] = useState(false);

  // 历史记录
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);
  const [pendingReview, setPendingReview] = useState<string | null>(null);
  const [pendingTopic, setPendingTopic] = useState<{ content: string; topic: string } | null>(null);

  useEffect(() => {
    if (tab === "review" && pendingReview !== null) {
      setReviewContent(pendingReview);
      setPendingReview(null);
    }
  }, [tab, pendingReview]);

  useEffect(() => {
    if (tab === "topic" && pendingTopic !== null) {
      setTopicContent(pendingTopic.content);
      if (pendingTopic.topic) setTopicInput(pendingTopic.topic);
      setPendingTopic(null);
    }
  }, [tab, pendingTopic]);

  const [models, setModels] = useState<ModelConfig[]>([]);
  const reviewEndRef = useRef<HTMLDivElement>(null);
  const topicEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    modelsApi.list().then(setModels).catch(console.error);
  }, []);

  useEffect(() => {
    if (tab === "history") {
      historyApi.list().then(setHistory).catch(console.error);
    }
  }, [tab]);

  useEffect(() => {
    if (tab === "review" && reviewSource === "kb") {
      knowledgeApi.listCards({ source_type: "literature" }).then(setKbCards).catch(console.error);
    }
  }, [tab, reviewSource]);

  const handleSearch = async () => {
    const validKeywords = keywords.filter(k => k.trim());
    if (validKeywords.length === 0) return;
    setSearching(true);
    setStats("搜索中...");
    try {
      let res;
      if (useBoolean && validKeywords.length > 1) {
        // Boolean search: build groups with operators
        const groups = validKeywords.map((kw, i) => ({
          keywords: kw.trim().split(/\s+/),
          field: "all",
          operator: i === 0 ? "AND" : (operators[i - 1] || "OR"),
        }));
        res = await enhancedSearchApi.search(groups, selectedSources);
      } else {
        const query = validKeywords.join(" ");
        res = await searchApi.search(query, selectedSources);
      }
      setResults((res as any).papers || []);
      setStats(`找到 ${(res as any).count} 篇文献（已自动保存到历史记录）`);
      setReviewPool(new Set());
      setExpandedAbstracts(new Set());
    } catch (err) {
      setStats(`搜索失败: ${err}`);
    }
    setSearching(false);
  };

  // Batch import selected results to library
  const handleBatchImport = async () => {
    const poolResults = reviewPool.size > 0
      ? Array.from(reviewPool).map(i => results[i]).filter(Boolean)
      : results;
    if (poolResults.length === 0) {
      alert("请先搜索文献或选择要导入的文献");
      return;
    }
    setBatchImporting(true);
    try {
      const res = await enhancedSearchApi.batchImport(poolResults as unknown as Record<string, unknown>[]) as any;
      alert(`导入完成：${res.imported} 篇成功，${res.skipped} 篇已存在`);
    } catch (err) {
      alert(`导入失败: ${err}`);
    }
    setBatchImporting(false);
  };

  const toggleSource = (key: string) => {
    setSelectedSources(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const toggleReviewPool = (idx: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setReviewPool(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  const toggleExpandAbstract = (idx: number) => {
    setExpandedAbstracts(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  // AI 综述
  const handleReview = async () => {
    setReviewing(true);
    setReviewContent("");

    let prompt = "";

    const sectionsText = customSections.length > 0
      ? customSections.map((s, i) => `  ${i + 1}. ${s}`).join("\n")
      : "  1. 研究背景\n  2. 研究现状\n  3. 方法对比\n  4. 研究趋势\n  5. 关键结论";

    if (reviewSource === "custom" && reviewInput.trim()) {
      prompt = `请基于以下文献数据生成一份结构化的AI综述报告，按照以下结构撰写（使用 Markdown 二级标题）：\n${sectionsText}\n\n文献数据：\n\n${reviewInput.slice(0, 4000)}`;
    } else if (reviewSource === "kb" && selectedKbCards.length > 0) {
      const selected = kbCards.filter(c => selectedKbCards.includes(c.id));
      const paperSummaries = selected.map((c, i) =>
        `[${i + 1}] ${c.title}\n摘要: ${c.summary || "无"}\n要点: ${c.key_points?.join("; ") || "无"}`
      ).join("\n\n");
      prompt = `请基于以下知识库文献生成一份结构化的AI综述报告，按照以下结构撰写（使用 Markdown 二级标题）：\n${sectionsText}\n\n${paperSummaries}`;
    } else if (reviewSource === "search" && results.length > 0) {
      const poolResults = reviewPool.size > 0
        ? Array.from(reviewPool).map(i => results[i]).filter(Boolean)
        : results;
      const paperSummaries = poolResults.slice(0, 20).map((p, i) =>
        `[${i + 1}] ${p.title} (${p.year}) - ${p.authors?.slice(0, 3).join(", ")} | ${p.journal}\n${p.abstract?.slice(0, 200) || ""}`
      ).join("\n\n");
      prompt = `请基于以下文献生成一份结构化的AI综述报告，按照以下结构撰写（使用 Markdown 二级标题）：\n${sectionsText}\n\n${paperSummaries}`;
    } else {
      setReviewContent("请选择数据源：搜索结果、知识库文献，或粘贴自定义数据。");
      setReviewing(false);
      return;
    }

    let fullContent = "";
    try {
      const session = await chatApi.createSession("文献综述");
      await chatApi.addMessage(session.id, prompt);
      const modelId = models[0]?.id;
      for await (const chunk of chatApi.stream(session.id, modelId)) {
        if (chunk.type === "content") {
          fullContent += chunk.data;
          setReviewContent(fullContent);
        }
      }
      historyApi.create({
        query: `AI综述: ${reviewSource === "kb" ? "知识库文献" : reviewSource === "custom" ? "自定义数据" : "搜索结果"}`,
        type: "review",
        result_count: reviewSource === "kb" ? selectedKbCards.length : reviewSource === "search" ? results.length : 0,
        data: JSON.stringify({ content: fullContent }),
      }).catch(console.error);
    } catch (err) {
      setReviewContent(`生成失败: ${err}`);
    }
    setReviewing(false);
  };

  // 选题讨论
  const handleDiscuss = async () => {
    if (!topicInput.trim()) return;
    setDiscussing(true);
    setTopicContent("");

    const prompt = `你是一位资深的科研导师。请针对以下研究方向进行深入的选题讨论，提供：1) 3-5个具体选题建议；2) 每个选题的研究价值和创新点；3) 可能的研究方法；4) 预期难度和周期评估。\n\n研究方向：${topicInput}`;

    let fullContent = "";
    try {
      const session = await chatApi.createSession("选题讨论");
      await chatApi.addMessage(session.id, prompt);
      const modelId = models[0]?.id;
      for await (const chunk of chatApi.stream(session.id, modelId)) {
        if (chunk.type === "content") {
          fullContent += chunk.data;
          setTopicContent(fullContent);
        }
      }
      historyApi.create({
        query: `选题讨论: ${topicInput.slice(0, 100)}`,
        type: "topic",
        result_count: 0,
        data: JSON.stringify({ content: fullContent, topic: topicInput }),
      }).catch(console.error);
    } catch (err) {
      setTopicContent(`生成失败: ${err}`);
    }
    setDiscussing(false);
  };

  const parseHistoryData = (data: unknown): Paper[] => {
    if (Array.isArray(data)) return data as Paper[];
    if (typeof data === "string" && data.length > 2) {
      try { return JSON.parse(data); } catch {
        try {
          let fixed = data.trim();
          const lastComplete = fixed.lastIndexOf('}');
          if (lastComplete > 0) {
            fixed = fixed.substring(0, lastComplete + 1) + ']';
            if (!fixed.startsWith('[')) fixed = '[' + fixed;
            return JSON.parse(fixed);
          }
        } catch {}
        return [];
      }
    }
    return [];
  };

  const parseRecordContent = (data: unknown): { content: string; topic?: string } => {
    try {
      const raw = data;
      if (typeof raw === "string") {
        try {
          const parsed = JSON.parse(raw);
          return { content: parsed.content || parsed.text || "", topic: parsed.topic };
        } catch {
          return { content: raw };
        }
      } else if (raw && typeof raw === "object") {
        const obj = raw as any;
        return { content: obj.content || obj.text || JSON.stringify(raw), topic: obj.topic };
      }
    } catch {}
    return { content: String(data || "") };
  };

  const loadHistoryResults = (record: HistoryRecord) => {
    const parsed = parseRecordContent(record.data);
    if (record.type === "review") {
      setPendingReview(parsed.content);
      setTab("review");
    } else if (record.type === "topic") {
      setPendingTopic({ content: parsed.content, topic: parsed.topic || "" });
      setTab("topic");
    } else {
      const papers = parseHistoryData(record.data);
      setResults(papers);
      setKeywords(record.query.split(" OR ").map(s => s.trim()));
      setStats(`已加载历史记录: "${record.query}" — ${papers.length} 篇文献 (${new Date(record.created_at).toLocaleDateString("zh-CN")})`);
      setTab("search");
    }
  };

  const toggleKbCard = (id: string) => {
    setSelectedKbCards(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  };

  const handleImportPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
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
        }
      } catch (err) {
        alert(`导入失败: ${err}`);
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const renderStreamingContent = (content: string, endRef: React.RefObject<HTMLDivElement | null>) => (
    <div className="glass-card p-5 overflow-y-auto" style={{ maxHeight: "calc(100vh - 320px)" }}>
      <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(content) }} />
      <div ref={endRef} />
    </div>
  );

  // 统计数据
  const totalPapers = results.length;
  const abstractCount = results.filter(p => p.abstract).length;
  const coveragePercent = totalPapers > 0 ? Math.round((abstractCount / totalPapers) * 100) : 0;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>文献管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1" style={{ borderBottom: "1px solid var(--border-color)" }}>
        {(["search", "review", "topic", "history"] as const).map(t => {
          const labels = { search: "关键词检索", review: "AI 综述", topic: "选题讨论", history: "历史记录" };
          const isActive = tab === t;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer relative"
              style={isActive
                ? { color: "var(--accent-blue)" }
                : { color: "var(--text-secondary)" }
              }
            >
              {labels[t]}
              {isActive && (
                <span className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full" style={{ background: "var(--accent-blue)" }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ─── 关键词检索 ─── */}
      {tab === "search" && (
        <div className="space-y-4">
          {/* 统一搜索条 */}
          <div className="glass-card p-4 space-y-3">
            {/* 搜索行：输入框 + 筛选 + 按钮 */}
            <div className="flex gap-2 items-center">
              <div className="relative flex-1">
                <IconSearch size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
                <input
                  className="input-glass pl-9 w-full"
                  placeholder="输入关键词搜索学术文献（组内 AND，组间用 OR 分隔）..."
                  value={keywords[0] || ""}
                  onChange={e => {
                    const next = [...keywords];
                    next[0] = e.target.value;
                    setKeywords(next);
                  }}
                  onKeyDown={e => { if (e.key === "Enter") handleSearch(); }}
                />
              </div>
              <button
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-150"
                style={showFilters
                  ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)", border: "1px solid rgba(59,130,246,0.3)" }
                  : { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" }
                }
                onClick={() => setShowFilters(f => !f)}
              >
                <IconFilter size={13} />
                筛选
              </button>
              <button className="btn-gradient btn-click flex items-center gap-1.5" onClick={handleSearch} disabled={searching}>
                <IconSearch size={13} />
                {searching ? "搜索中..." : "搜索"}
              </button>
            </div>

            {/* Boolean mode toggle */}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-[10px] cursor-pointer" style={{ color: "var(--text-muted)" }}>
                <input type="checkbox" checked={useBoolean} onChange={e => setUseBoolean(e.target.checked)} />
                布尔检索模式 (AND/OR/NOT)
              </label>
            </div>

            {/* 多关键词行 */}
            {keywords.length > 1 && (
              <div className="space-y-2">
                {keywords.slice(1).map((kw, i) => (
                  <div key={i + 1} className="flex gap-2 items-center">
                    {useBoolean ? (
                      <select className="input-glass text-xs w-16 py-1"
                        value={operators[i] || "OR"}
                        onChange={e => {
                          const next = [...operators];
                          next[i] = e.target.value;
                          setOperators(next);
                        }}>
                        <option value="AND">AND</option>
                        <option value="OR">OR</option>
                        <option value="NOT">NOT</option>
                      </select>
                    ) : (
                      <span className="text-xs font-bold px-2" style={{ color: "var(--accent-blue)" }}>OR</span>
                    )}
                    <input
                      className="input-glass flex-1"
                      placeholder={`关键词 ${i + 2}`}
                      value={kw}
                      onChange={e => {
                        const next = [...keywords];
                        next[i + 1] = e.target.value;
                        setKeywords(next);
                      }}
                    />
                    <button onClick={() => setKeywords(keywords.filter((_, j) => j !== i + 1))} className="text-sm transition-colors cursor-pointer"
                      style={{ color: "var(--text-muted)" }}
                      onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                      onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                    ><IconX size={14} /></button>
                  </div>
                ))}
              </div>
            )}

            {/* 筛选面板（可折叠） */}
            {showFilters && (
              <div className="space-y-3 pt-2 animate-fade-in" style={{ borderTop: "1px solid var(--border-color)" }}>
                {/* 学术源 */}
                <div>
                  <p className="text-xs font-medium mb-2" style={{ color: "var(--text-secondary)" }}>学术数据源</p>
                  <div className="flex gap-2 flex-wrap">
                    {SOURCES.map(s => {
                      const active = selectedSources.includes(s.key);
                      return (
                        <button key={s.key} onClick={() => toggleSource(s.key)}
                          className="px-2.5 py-1 rounded-lg text-[11px] font-medium cursor-pointer transition-all duration-150"
                          style={active
                            ? { background: "rgba(59,130,246,0.12)", color: "var(--accent-blue)", border: "1px solid rgba(59,130,246,0.3)" }
                            : { background: "var(--hover-bg)", color: "var(--text-muted)", border: "1px solid transparent" }
                          }
                        >{s.label}</button>
                      );
                    })}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setKeywords([...keywords, ""])} className="text-xs cursor-pointer flex items-center gap-1" style={{ color: "var(--accent-blue)" }}>
                    + 添加关键词
                  </button>
                </div>
              </div>
            )}

            {/* 操作行：次要按钮 + 视图切换 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button className="btn-ghost text-xs flex items-center gap-1.5" onClick={() => fileInputRef.current?.click()}>
                  <IconUpload size={12} /> 导入 PDF
                </button>
                <input ref={fileInputRef} type="file" accept=".pdf" multiple className="hidden" onChange={handleImportPdf} />
                {results.length > 0 && (
                  <button className="btn-ghost text-xs flex items-center gap-1.5" onClick={handleBatchImport} disabled={batchImporting}>
                    <IconUpload size={12} /> {batchImporting ? "导入中..." : `批量导入到文献库${reviewPool.size > 0 ? ` (${reviewPool.size})` : ""}`}
                  </button>
                )}
                <button className="text-xs cursor-pointer flex items-center gap-1 transition-colors"
                  style={{ color: "var(--text-muted)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                >
                  <IconGlobe size={12} /> 在线检索
                </button>
              </div>
              <div className="flex items-center gap-1 p-0.5 rounded-lg" style={{ background: "var(--hover-bg)" }}>
                <button className="p-1.5 rounded-md cursor-pointer transition-all"
                  style={viewMode === "list" ? { background: "var(--glass-bg)", boxShadow: "var(--shadow-sm)" } : {}}
                  onClick={() => setViewMode("list")}
                ><IconList size={14} style={{ color: viewMode === "list" ? "var(--accent-blue)" : "var(--text-muted)" }} /></button>
                <button className="p-1.5 rounded-md cursor-pointer transition-all"
                  style={viewMode === "grid" ? { background: "var(--glass-bg)", boxShadow: "var(--shadow-sm)" } : {}}
                  onClick={() => setViewMode("grid")}
                ><IconGrid size={14} style={{ color: viewMode === "grid" ? "var(--accent-blue)" : "var(--text-muted)" }} /></button>
              </div>
            </div>
          </div>

          {/* 统计看板 */}
          {results.length > 0 && (
            <div className="glass-card p-3 flex items-center gap-4">
              <div className="flex items-center gap-2 flex-1">
                <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>共 {totalPapers} 篇</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>·</span>
                <div className="flex items-center gap-2 flex-1 max-w-xs">
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border-color)" }}>
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${coveragePercent}%`, background: "linear-gradient(90deg, var(--accent-blue), var(--accent-green))" }} />
                  </div>
                  <span className="text-[11px] font-medium" style={{ color: "var(--accent-blue)" }}>{coveragePercent}% 有摘要</span>
                </div>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>·</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {reviewPool.size > 0 ? `已选 ${reviewPool.size} 篇加入综述池` : "点击文献右侧图标加入综述池"}
                </span>
              </div>
              {stats && <span className="text-[11px]" style={{ color: "var(--accent-green)" }}>{stats}</span>}
            </div>
          )}

          {/* 结果列表 */}
          {results.length > 0 ? (
            <div className={viewMode === "grid"
              ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
              : "space-y-2"
            }>
              {results.map((p, i) => {
                const isExpanded = expandedAbstracts.has(i);
                const inPool = reviewPool.has(i);
                const isHovered = hoveredIdx === i;
                const sourceColor = SOURCE_COLORS[p.source || ""] || { bg: "rgba(107,114,128,0.1)", text: "var(--text-muted)" };

                return (
                  <div
                    key={i}
                    className="glass-card relative group cursor-pointer transition-all duration-200"
                    style={{
                      ...(viewMode === "grid" ? { padding: "16px" } : {}),
                      ...(inPool ? { borderLeft: "3px solid var(--accent-green)" } : {}),
                    }}
                    onMouseEnter={() => setHoveredIdx(i)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  >
                    {/* 列表视图 */}
                    {viewMode === "list" ? (
                      <div className="flex items-stretch">
                        {/* 左侧状态条 */}
                        <div className="w-1 flex-shrink-0 rounded-l-2xl" style={{
                          background: p.abstract
                            ? "linear-gradient(180deg, var(--accent-green), rgba(16,185,129,0.3))"
                            : "var(--border-color)"
                        }} />

                        <div className="flex-1 p-4 min-w-0">
                          <div className="flex items-start gap-3">
                            <div className="flex-1 min-w-0">
                              {/* 第一行：标题 + 来源标签 + 入库时间 */}
                              <div className="flex items-start gap-2">
                                <h3 className="text-sm font-semibold leading-snug flex-1 min-w-0" style={{ color: "var(--accent-blue)" }}>
                                  {p.title}
                                </h3>
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 mt-0.5"
                                  style={{ background: sourceColor.bg, color: sourceColor.text }}>
                                  {p.source?.replace(/_/g, " ") || "unknown"}
                                </span>
                              </div>

                              {/* 第二行：作者 · 年份 */}
                              <p className="text-xs mt-1.5" style={{ color: "var(--text-secondary)" }}>
                                {p.authors?.slice(0, 3).join(", ")}{p.authors && p.authors.length > 3 ? " 等" : ""}
                                {p.year ? ` · ${p.year}` : ""}
                                {p.journal ? ` · ${p.journal}` : ""}
                              </p>

                              {/* 第三行：摘要（1行，可展开） */}
                              {p.abstract && (
                                <p
                                  className="text-xs mt-1.5 cursor-pointer transition-all"
                                  style={{
                                    color: "var(--text-muted)",
                                    display: isExpanded ? "block" : "-webkit-box",
                                    WebkitLineClamp: isExpanded ? undefined : 1,
                                    WebkitBoxOrient: "vertical",
                                    overflow: isExpanded ? "visible" : "hidden",
                                  }}
                                  onClick={(e) => { e.stopPropagation(); toggleExpandAbstract(i); }}
                                >
                                  {p.abstract.slice(0, 300)}
                                  {!isExpanded && p.abstract.length > 150 && (
                                    <span className="ml-1 text-[11px] font-medium" style={{
                                      background: "linear-gradient(90deg, var(--accent-blue), var(--accent-green))",
                                      WebkitBackgroundClip: "text",
                                      WebkitTextFillColor: "transparent",
                                    }}>展开全文 ▶</span>
                                  )}
                                </p>
                              )}
                            </div>

                            {/* 右侧悬停 AI 操作 */}
                            <div className="flex flex-col gap-1.5 flex-shrink-0 transition-opacity duration-200"
                              style={{ opacity: isHovered ? 1 : 0 }}>
                              <button
                                className="p-1.5 rounded-lg cursor-pointer transition-all duration-150"
                                style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}
                                onMouseEnter={e => (e.currentTarget.style.background = "rgba(59,130,246,0.2)")}
                                onMouseLeave={e => (e.currentTarget.style.background = "rgba(59,130,246,0.1)")}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  papersApi.fromSearch(p as unknown as Record<string, unknown>).then(() => alert("已入库")).catch(err => alert("入库失败: " + err));
                                }}
                                title="入库"
                              >
                                <IconSparkle size={14} />
                              </button>
                              <button
                                className="p-1.5 rounded-lg cursor-pointer transition-all duration-150"
                                style={{
                                  background: inPool ? "rgba(16,185,129,0.15)" : "rgba(16,185,129,0.08)",
                                  color: inPool ? "var(--accent-green)" : "var(--text-muted)",
                                }}
                                onMouseEnter={e => (e.currentTarget.style.background = "rgba(16,185,129,0.2)")}
                                onMouseLeave={e => (e.currentTarget.style.background = inPool ? "rgba(16,185,129,0.15)" : "rgba(16,185,129,0.08)")}
                                onClick={(e) => toggleReviewPool(i, e)}
                                title={inPool ? "从综述池移除" : "加入综述池"}
                              >
                                <IconBookmark size={14} />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* 网格视图 */
                      <div className="flex flex-col gap-2">
                        <div className="flex items-start justify-between gap-2">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0"
                            style={{ background: sourceColor.bg, color: sourceColor.text }}>
                            {p.source?.replace(/_/g, " ") || "unknown"}
                          </span>
                          <div className="flex gap-1">
                            <button className="p-1 rounded cursor-pointer" style={{ color: inPool ? "var(--accent-green)" : "var(--text-muted)" }}
                              onClick={(e) => toggleReviewPool(i, e)} title={inPool ? "从综述池移除" : "加入综述池"}>
                              <IconBookmark size={12} />
                            </button>
                          </div>
                        </div>
                        <h3 className="text-sm font-semibold leading-snug line-clamp-2" style={{ color: "var(--text-primary)" }}>{p.title}</h3>
                        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                          {p.authors?.slice(0, 2).join(", ")}{p.year ? ` · ${p.year}` : ""}
                        </p>
                        {p.abstract && (
                          <p className="text-[11px] line-clamp-3" style={{ color: "var(--text-muted)" }}>{p.abstract.slice(0, 150)}</p>
                        )}
                        <div className="flex gap-1.5 mt-auto pt-1">
                          <button className="btn-ghost text-[10px] py-1 flex-1" onClick={async () => {
                            try { await papersApi.fromSearch(p as unknown as Record<string, unknown>); alert("已入库"); } catch (err) { alert("入库失败: " + err); }
                          }}>入库</button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            stats && !searching && (
              <div className="glass-card p-8 text-center">
                <IconSearch size={32} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
                <p className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>输入关键词开始搜索学术文献</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>支持 OpenAlex、arXiv、Semantic Scholar 等 7 大数据源</p>
              </div>
            )
          )}

          {/* 综述池浮动按钮 (FAB) */}
          {reviewPool.size > 0 && (
            <div className="fixed bottom-8 right-8 z-40 animate-fade-in">
              <button
                className="flex items-center gap-2.5 px-5 py-3 rounded-2xl text-sm font-semibold cursor-pointer transition-all duration-200 shadow-lg btn-click"
                style={{
                  background: "linear-gradient(135deg, var(--accent-blue), var(--accent-green))",
                  color: "#fff",
                  boxShadow: "0 8px 24px rgba(59,130,246,0.3)",
                }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 12px 32px rgba(59,130,246,0.4)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 8px 24px rgba(59,130,246,0.3)"; }}
                onClick={() => { setReviewSource("search"); setTab("review"); }}
              >
                <IconSparkle size={16} />
                <span>生成综述</span>
                <span className="px-2 py-0.5 rounded-full text-[11px] font-bold" style={{ background: "rgba(255,255,255,0.25)" }}>
                  {reviewPool.size}
                </span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ─── AI 综述 ─── */}
      {tab === "review" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-4">
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>选择综述数据源</p>

            <div className="flex gap-2">
              {[
                { key: "search", label: `搜索结果 (${reviewPool.size > 0 ? reviewPool.size + "篇已选" : results.length + "篇"})` },
                { key: "kb", label: "知识库文献" },
                { key: "custom", label: "自定义输入" },
              ].map(opt => (
                <button key={opt.key}
                  onClick={() => setReviewSource(opt.key as any)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors"
                  style={reviewSource === opt.key
                    ? { background: "var(--accent-blue)", color: "#fff" }
                    : { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" }
                  }
                >{opt.label}</button>
              ))}
            </div>

            {reviewSource === "kb" && (
              <div className="space-y-2 max-h-48 overflow-y-auto rounded-lg p-3" style={{ border: "1px solid var(--border-color)" }}>
                {kbCards.length === 0 ? (
                  <p className="text-xs text-center py-2" style={{ color: "var(--text-muted)" }}>知识库中暂无文献卡片</p>
                ) : kbCards.map(card => (
                  <label key={card.id} className="flex items-start gap-2 cursor-pointer py-1">
                    <input type="checkbox" checked={selectedKbCards.includes(card.id)} onChange={() => toggleKbCard(card.id)} className="mt-1 rounded" />
                    <span className="text-xs" style={{ color: "var(--text-primary)" }}>{card.title}</span>
                  </label>
                ))}
                {selectedKbCards.length > 0 && (
                  <p className="text-xs pt-1" style={{ color: "var(--accent-blue)" }}>已选 {selectedKbCards.length} 篇</p>
                )}
              </div>
            )}

            {reviewSource === "custom" && (
              <textarea
                className="input-glass"
                rows={4}
                placeholder="粘贴 ai-literature JSON 数据或文献摘要..."
                value={reviewInput}
                onChange={e => setReviewInput(e.target.value)}
              />
            )}

            {reviewSource === "search" && (
              <p className="text-xs" style={{ color: results.length > 0 ? "var(--text-secondary)" : "#ef4444" }}>
                {results.length > 0
                  ? reviewPool.size > 0
                    ? `将基于综述池中 ${reviewPool.size} 篇文献生成综述`
                    : `将基于全部 ${results.length} 篇搜索结果生成综述`
                  : "请先在「关键词检索」tab 中搜索文献"}
              </p>
            )}

            {/* Custom Sections Editor */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>综述结构</p>
                <button className="text-[10px] cursor-pointer" style={{ color: "var(--accent-blue)" }}
                  onClick={() => setShowSectionEditor(!showSectionEditor)}>
                  {showSectionEditor ? "收起" : "自定义"}
                </button>
              </div>
              {showSectionEditor ? (
                <div className="space-y-1.5">
                  {customSections.map((section, i) => (
                    <div key={i} className="flex gap-1.5 items-center">
                      <span className="text-[10px] w-4 text-center" style={{ color: "var(--text-muted)" }}>{i + 1}</span>
                      <input className="input-glass flex-1 text-xs py-1"
                        value={section}
                        onChange={e => {
                          const next = [...customSections];
                          next[i] = e.target.value;
                          setCustomSections(next);
                        }} />
                      <button className="text-[10px] cursor-pointer" style={{ color: "var(--text-muted)" }}
                        onClick={() => setCustomSections(customSections.filter((_, j) => j !== i))}>
                        <IconX size={12} />
                      </button>
                    </div>
                  ))}
                  <button className="text-[10px] cursor-pointer" style={{ color: "var(--accent-blue)" }}
                    onClick={() => setCustomSections([...customSections, "新章节"])}>
                    + 添加章节
                  </button>
                </div>
              ) : (
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                  {customSections.join(" → ")}
                </p>
              )}
            </div>

            <button className="btn-gradient btn-click" onClick={handleReview} disabled={reviewing}>
              {reviewing ? "生成中..." : "生成综述"}
            </button>
          </div>
          {reviewContent && (
            <div className="space-y-2">
              {renderStreamingContent(reviewContent, reviewEndRef)}
              <div className="flex justify-end">
                <button className="btn-ghost text-xs" onClick={() => {
                  historyApi.create({
                    query: `AI综述: ${reviewSource === "kb" ? "知识库文献" : reviewSource === "custom" ? "自定义数据" : "搜索结果"}`,
                    type: "review",
                    result_count: reviewSource === "kb" ? selectedKbCards.length : reviewSource === "search" ? results.length : 0,
                    data: JSON.stringify({ content: reviewContent }),
                  }).then(() => alert("已保存到历史记录")).catch(err => alert("保存失败: " + err));
                }}>保存到历史</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── 选题讨论 ─── */}
      {tab === "topic" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-3">
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>输入研究方向，AI 将生成选题建议</p>
            <textarea
              className="input-glass"
              rows={3}
              placeholder="例如：航天器姿态控制中的自适应鲁棒方法研究..."
              value={topicInput}
              onChange={e => setTopicInput(e.target.value)}
            />
            <button className="btn-gradient btn-click" onClick={handleDiscuss} disabled={discussing}>
              {discussing ? "讨论中..." : "开始讨论"}
            </button>
          </div>
          {topicContent && (
            <div className="space-y-2">
              {renderStreamingContent(topicContent, topicEndRef)}
              <div className="flex justify-end">
                <button className="btn-ghost text-xs" onClick={() => {
                  historyApi.create({
                    query: `选题讨论: ${topicInput.slice(0, 100)}`,
                    type: "topic",
                    result_count: 0,
                    data: JSON.stringify({ content: topicContent, topic: topicInput }),
                  }).then(() => alert("已保存到历史记录")).catch(err => alert("保存失败: " + err));
                }}>保存到历史</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── 历史记录 ─── */}
      {tab === "history" && (
        <div className="space-y-2">
          {history.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>暂无搜索历史</p>
            </div>
          ) : history.map(record => {
            const isExpanded = expandedHistory === record.id;
            const papers = parseHistoryData(record.data);
            return (
              <div key={record.id} className="glass-card overflow-hidden">
                <div className="p-4 flex items-center gap-3 cursor-pointer"
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  onClick={() => loadHistoryResults(record)}
                >
                  <span className="flex-shrink-0 transition-transform duration-200"
                    style={{ color: "var(--text-muted)", transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}>
                    <IconChevronRight size={14} />
                  </span>
                  <span className="flex-shrink-0" style={{ color: record.type === "review" ? "#8b5cf6" : record.type === "topic" ? "#10b981" : "var(--text-muted)" }}>
                    {record.type === "review" ? <IconSparkle size={14} /> : record.type === "topic" ? <IconSearch size={14} /> : <IconSearch size={14} />}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{record.query}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {papers.length || record.result_count} 篇结果 · {new Date(record.created_at).toLocaleString("zh-CN")}
                    </p>
                  </div>
                  <button className="text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-colors flex-shrink-0"
                    style={{ background: "var(--accent-blue)", color: "#fff" }}
                    onClick={e => { e.stopPropagation(); loadHistoryResults(record); }}
                  >加载到检索</button>
                  <button className="text-xs px-2 py-1.5 rounded-lg cursor-pointer transition-colors flex-shrink-0"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                    onClick={e => {
                      e.stopPropagation();
                      if (!window.confirm('确定删除此历史记录？')) return;
                      historyApi.delete(record.id).then(() => {
                        setHistory(prev => prev.filter(h => h.id !== record.id));
                        if (expandedHistory === record.id) setExpandedHistory(null);
                      }).catch(err => { alert('删除失败: ' + err.message); });
                    }}
                  >删除</button>
                </div>

                {isExpanded && (
                  <div style={{ borderTop: "1px solid var(--border-color)" }}>
                    {papers.length === 0 ? (
                      <div className="px-4 py-3 text-xs text-center" style={{ color: "var(--text-muted)" }}>
                        无详细数据（该记录可能在旧版本中创建）
                      </div>
                    ) : (
                      <div className="px-4 py-2 space-y-0 max-h-64 overflow-y-auto">
                        {papers.map((p: Paper, i: number) => (
                          <div key={i} className="flex items-start gap-3 py-2.5"
                            style={{ borderBottom: i < papers.length - 1 ? "1px solid var(--border-color)" : "none" }}>
                            <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: "var(--accent-blue)" }}>[{i + 1}]</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium break-words leading-relaxed" style={{ color: "var(--text-primary)" }}>{p.title}</p>
                              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                                {p.authors?.length > 0 && (
                                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                                    {p.authors.slice(0, 3).join(", ")}{p.authors.length > 3 ? " 等" : ""}
                                  </span>
                                )}
                                {p.year && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{p.year}</span>}
                                {p.journal && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{p.journal}</span>}
                                {p.source && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{p.source}</span>}
                              </div>
                              {p.abstract && (
                                <p className="text-xs mt-1 line-clamp-2" style={{ color: "var(--text-muted)" }}>{p.abstract}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="px-4 py-2 flex justify-end" style={{ borderTop: "1px solid var(--border-color)" }}>
                      <button className="text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
                        style={{ background: "var(--accent-blue)", color: "#fff" }}
                        onClick={() => loadHistoryResults(record)}
                      >加载全部到检索页面</button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
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
