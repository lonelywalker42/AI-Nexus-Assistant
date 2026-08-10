import { useEffect, useState, useRef } from "react";
import { knowledgeApi, importGroupApi, knowledgeImportApi, type KnowledgeCard, type ImportGroup } from "../api/client";
import { IconFile, IconChat, IconArrowLeft, IconStar, IconLightbulb, IconX, IconGlobe, IconChart, IconBrain, IconFolder, IconList, IconGrid } from "../components/Icons";
import { getTagColor } from "../utils/tagColors";

const CATEGORIES = [
  { key: "literature", label: "文献导入", iconKey: "file", color: "#3b82f6" },
  { key: "deepseek", label: "AI 对话", iconKey: "chat", color: "#8b5cf6" },
  { key: "note", label: "随手记", iconKey: "lightbulb", color: "#f59e0b" },
  { key: "web", label: "网页抓取", iconKey: "globe", color: "#06b6d4" },
];

const CATEGORY_ICONS: Record<string, React.FC<{ size?: number }>> = {
  file: IconFile, chat: IconChat, edit: IconFile, lightbulb: IconLightbulb, globe: IconGlobe,
};

export default function KnowledgePage() {
  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [allCards, setAllCards] = useState<KnowledgeCard[]>([]);
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importStatus, setImportStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // 视图状态
  const [view, setView] = useState<"categories" | "list" | "detail" | "importGroups" | "importGroupDetail">("categories");
  const [activeCategory, setActiveCategory] = useState("");
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null);

  // 导入分组
  const [importGroups, setImportGroups] = useState<ImportGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<ImportGroup | null>(null);
  const [groupCards, setGroupCards] = useState<KnowledgeCard[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 随手记
  const [showQuickNote, setShowQuickNote] = useState(false);
  const [quickTitle, setQuickTitle] = useState("");
  const [quickContent, setQuickContent] = useState("");

  // 增强搜索
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [starMin, setStarMin] = useState(0);
  const [tagFilter, setTagFilter] = useState("");
  const [allTags, setAllTags] = useState<{ name: string; usage_count: number }[]>([]);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");

  // 摘要重新生成
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  // 随手记编辑
  const [editingNote, setEditingNote] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");

  // 知识图谱
  const [showGraph, setShowGraph] = useState(false);
  const [graphNodes, setGraphNodes] = useState<{ id: string; label: string; x: number; y: number; size: number; color: string }[]>([]);
  const [graphEdges, setGraphEdges] = useState<{ from: string; to: string }[]>([]);

  const buildGraph = () => {
    const nodes: typeof graphNodes = [];
    const edges: typeof graphEdges = [];
    const tagMap = new Map<string, string[]>();
    cards.forEach(card => {
      (card.tags || []).forEach(tag => {
        if (!tagMap.has(tag)) tagMap.set(tag, []);
        tagMap.get(tag)!.push(card.id);
      });
    });
    cards.forEach((card, i) => {
      const angle = (i / cards.length) * Math.PI * 2;
      const radius = 150;
      nodes.push({
        id: card.id,
        label: card.title.slice(0, 15),
        x: 200 + Math.cos(angle) * radius + (Math.random() - 0.5) * 50,
        y: 200 + Math.sin(angle) * radius + (Math.random() - 0.5) * 50,
        size: Math.max(8, Math.min(20, (card.star_rating || 1) * 4)),
        color: CATEGORIES.find(c => c.key === card.source_type)?.color || "#64748b",
      });
    });
    tagMap.forEach((cardIds, _tag) => {
      for (let i = 0; i < cardIds.length; i++) {
        for (let j = i + 1; j < cardIds.length; j++) {
          edges.push({ from: cardIds[i], to: cardIds[j] });
        }
      }
    });
    setGraphNodes(nodes);
    setGraphEdges(edges);
    setShowGraph(true);
  };

  // 批量操作
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchMode, setBatchMode] = useState(false);

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === cards.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(cards.map(c => c.id)));
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确定删除选中的 ${selectedIds.size} 张卡片？`)) return;
    try {
      for (const id of selectedIds) await knowledgeApi.deleteCard(id);
      setSelectedIds(new Set());
      setBatchMode(false);
      loadCards();
    } catch (err) { alert("批量删除失败: " + err); }
  };

  const handleBatchExport = () => {
    if (selectedIds.size === 0) return;
    const selected = cards.filter(c => selectedIds.has(c.id));
    const data = JSON.stringify(selected, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `knowledge_cards_${new Date().toISOString().slice(0, 10)}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  // 防抖搜索
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // 带重试的请求包装（最多重试 3 次，指数退避）
  const fetchWithRetry = async <T,>(fn: () => Promise<T>, maxRetries = 3): Promise<T> => {
    let lastError: unknown;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await fn();
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") throw err;
        lastError = err;
        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, 500 * Math.pow(2, attempt)));
        }
      }
    }
    throw lastError;
  };

  const loadCards = (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError(null);
    fetchWithRetry(() => knowledgeApi.listCards({
      search: debouncedSearch,
      tag: tagFilter,
      star_min: starMin,
      sort_by: sortBy,
      sort_order: sortOrder,
    }, signal)).then(data => {
      const filtered = Array.isArray(data) ? data : [];
      if (!debouncedSearch && !tagFilter && !starMin) setAllCards(filtered);
      setCards(filtered);
      setLoadError(null);
      setLoading(false);
    }).catch(err => {
      if (err instanceof DOMException && err.name === "AbortError") return;
      console.error("加载卡片失败:", err);
      const msg = err?.message || "";
      const name = err?.name || "";
      if (msg.includes("not ready") || msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("Load failed")) {
        setLoadError("网络连接失败，请检查后端服务是否运行 (python server.py)");
      } else if (name === "TimeoutError" || name === "AbortError" || msg.includes("timed out") || msg.includes("timeout") || msg.includes("aborted")) {
        setLoadError("请求超时，后端响应过慢，请稍后重试");
      } else if (msg.includes("API Error")) {
        setLoadError("服务返回错误: " + msg);
      } else {
        setLoadError("加载卡片失败: " + msg);
      }
      setLoading(false);
    });
  };
  useEffect(() => {
    const controller = new AbortController();
    void loadCards(controller.signal);
    return () => controller.abort();
  }, [debouncedSearch, sortBy, sortOrder, starMin, tagFilter]);

  // 加载标签（首次加载时自动清理孤立标签）
  useEffect(() => {
    knowledgeApi.cleanupTags().catch(() => {}).finally(() => {
      knowledgeApi.listTags().then(setAllTags).catch(() => {});
    });
  }, []);

  // 加载导入分组
  const loadImportGroups = () => importGroupApi.list().then(setImportGroups).catch(console.error);

  const categoryCounts = CATEGORIES.map(cat => ({
    ...cat,
    count: allCards.filter(c => c.source_type === cat.key).length,
  }));

  const filteredCards = activeCategory ? cards.filter(c => c.source_type === activeCategory) : cards;

  const handleCreate = async () => {
    const title = prompt("卡片标题:");
    if (!title) return;
    await knowledgeApi.createCard({ title, source_type: "manual" });
    loadCards();
  };

  const handleQuickNote = async () => {
    if (!quickTitle.trim()) return;
    await knowledgeApi.createCard({ title: quickTitle.trim(), summary: quickContent.trim(), source_type: "note" });
    setQuickTitle(""); setQuickContent(""); setShowQuickNote(false);
    loadCards();
  };

  const handleDelete = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!confirm("确定删除？")) return;
    await knowledgeApi.deleteCard(id);
    loadCards();
    if (selectedCard?.id === id) { setSelectedCard(null); setView(activeCategory ? "list" : "categories"); }
  };

  const handleRegenerateSummary = async (cardId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (regeneratingId) return;
    setRegeneratingId(cardId);
    try {
      const result = await knowledgeApi.regenerateSummary(cardId);
      // 更新卡片列表中的对应卡片
      setCards(prev => prev.map(c => c.id === cardId ? { ...c, title: result.title, summary: result.summary } : c));
      if (selectedCard?.id === cardId) {
        setSelectedCard(prev => prev ? { ...prev, title: result.title, summary: result.summary } : prev);
      }
    } catch (err) {
      alert("重新生成摘要失败: " + err);
    } finally {
      setRegeneratingId(null);
    }
  };

  const handleCardClick = async (card: KnowledgeCard) => {
    try { const full = await knowledgeApi.getCard(card.id); setSelectedCard(full); }
    catch { setSelectedCard(card); }
    setView("detail");
  };

  const handleBackFromDetail = () => {
    setSelectedCard(null);
    setEditingNote(false);
    if (selectedGroup) setView("importGroupDetail");
    else setView(activeCategory ? "list" : "categories");
  };

  const handleCategoryClick = (key: string) => {
    setActiveCategory(key); setView("list");
  };

  const handleBackFromList = () => { setActiveCategory(""); setView("categories"); };


  // ── DeepSeek 智能导入 ──────────────────────────────────────

  const handleDeepSeekImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true);
      setImportStatus(`正在解析: ${file.name}...`);
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        setImportStatus(`解析完成，正在启动 AI 处理 pipeline...`);
        const result = await importGroupApi.importDeepseek(data, file.name);
        setImportStatus(`已启动处理: ${result.conversations} 个对话, ${result.total_messages} 条消息\n正在通过 LLM 生成知识卡片，请等待...`);

        // 开始轮询进度
        startProgressPolling(result.group_id);
      } catch (err) {
        setImportStatus(`导入失败: ${err}`);
        setImporting(false);
      }
    };
    input.click();
  };

  const startProgressPolling = (groupId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    let pollFailCount = 0;
    pollingRef.current = setInterval(async () => {
      try {
        const progress = await importGroupApi.getProgress(groupId);
        pollFailCount = 0; // 成功则重置失败计数
        setImportStatus(`[${progress.status}] ${progress.progress}\n已生成 ${progress.card_count} 张卡片`);
        if (progress.status === "completed" || progress.status === "failed") {
          if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
          setImporting(false);
          if (progress.status === "completed") {
            setImportStatus(`✅ ${progress.progress}`);
            // 重置所有筛选条件（包括分类），确保导入后能看到所有卡片
            setSearch(""); setStarMin(0); setTagFilter(""); setActiveCategory("");
            setView("categories");
            loadImportGroups();
            // 显式调用 loadCards() 刷新卡片列表（useEffect 依赖可能不会全部触发）
            loadCards();
          } else {
            setImportStatus(`❌ 导入失败: ${progress.error}`);
          }
        }
      } catch (pollErr) {
        console.error("轮询进度失败:", pollErr);
        // 连续失败超过 5 次则停止轮询并提示用户
        if (!pollFailCount) pollFailCount = 0;
        pollFailCount++;
        if (pollFailCount > 5) {
          if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
          setImportStatus(`⚠️ 进度查询失败，请刷新页面查看结果`);
          setImporting(false);
        }
      }
    }, 2000);
  };

  // 清理轮询
  useEffect(() => {
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, []);

  // ── 导入分组详情 ──────────────────────────────────────────

  const handleGroupClick = async (group: ImportGroup) => {
    try {
      const detail = await importGroupApi.get(group.id);
      setSelectedGroup(detail);
      setGroupCards(detail.cards || []);
      setView("importGroupDetail");
    } catch (err) {
      alert("加载分组详情失败: " + err);
    }
  };

  const handleDeleteGroup = async (groupId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!confirm("确定删除该导入分组及其所有卡片和关联对话？")) return;
    try {
      await importGroupApi.delete(groupId);
      loadImportGroups();
      if (selectedGroup?.id === groupId) { setSelectedGroup(null); setView("importGroups"); }
      loadCards();
    } catch (err) { alert("删除失败: " + err); }
  };

  // ── 普通 JSON 导入 ──────────────────────────────────────

  const handleImportJSON = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true); setImportStatus(`正在解析: ${file.name}...`);
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        const isAiLiterature = !!(data.kbPapers || data.papers);
        const format = isAiLiterature ? "ai-literature" : "未知";
        setImportStatus(`检测到 ${format} 格式，正在导入...`);
        const result = await knowledgeImportApi.fromJson(data);
        setImportStatus(`导入完成: ${result.imported} 条记录 (${format} 格式)`);
        loadCards();
      } catch (err) { setImportStatus(`导入失败: ${err}`); }
      setImporting(false);
    };
    input.click();
  };

  const handleImportMD = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".md,.txt";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true); setImportStatus("正在导入 Markdown...");
      try {
        const text = await file.text();
        const result = await knowledgeImportApi.fromMarkdown(text, file.name);
        setImportStatus(`导入完成: ${result.imported} 条记录`);
        loadCards();
      } catch (err) { setImportStatus(`导入失败: ${err}`); }
      setImporting(false);
    };
    input.click();
  };

  const handleImportPDF = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".pdf"; input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length === 0) return;
      setImporting(true);
      let successCount = 0, failCount = 0;
      const results: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setImportStatus(`[${i + 1}/${files.length}] 正在处理: ${file.name}...`);
        try {
          const result = await knowledgeImportApi.fromPdf(file);
          if (result.error) { failCount++; results.push(`❌ ${file.name}: ${result.error}`); }
          else { successCount++; results.push(`✅ ${file.name}: ${result.title}`); }
        } catch (err) { failCount++; results.push(`❌ ${file.name}: ${err}`); }
      }
      setImportStatus(`处理完成: ${successCount} 成功, ${failCount} 失败\n${results.join("\n")}`);
      setImporting(false); loadCards();
    };
    input.click();
  };

  const handleImportUrl = async () => {
    if (!importUrl.trim()) return;
    setImporting(true); setImportStatus(`正在抓取: ${importUrl}...`);
    try {
      const result = await knowledgeImportApi.fromUrl(importUrl);
      if (result.error) setImportStatus(`❌ 导入失败: ${result.error}`);
      else { setImportStatus(`✅ 导入完成: ${result.title}`); setImportUrl(""); loadCards(); }
    } catch (err) { setImportStatus(`❌ 导入失败: ${err}`); }
    setImporting(false);
  };

  return (
    <div className="space-y-5">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {(view === "detail" || view === "list" || view === "importGroups" || view === "importGroupDetail") && (
            <button onClick={() => {
              if (view === "detail") handleBackFromDetail();
              else if (view === "importGroupDetail") { setSelectedGroup(null); setView("importGroups"); }
              else if (view === "importGroups") { setActiveCategory(""); setView("categories"); }
              else handleBackFromList();
            }}
              className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors cursor-pointer"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            ><IconArrowLeft size={16} /></button>
          )}
          <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            {view === "detail" ? selectedCard?.title || "卡片详情" :
             view === "importGroupDetail" ? selectedGroup?.title || "导入详情" :
             view === "importGroups" ? "AI 对话导入" :
             view === "list" ? (CATEGORIES.find(c => c.key === activeCategory)?.label || "全部卡片") :
             "IDEA"}
          </h2>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost text-xs py-2 flex items-center gap-1" onClick={() => setShowQuickNote(v => !v)}>
            <IconLightbulb size={13} /> 随手记
          </button>
          <button className="btn-ghost text-xs py-2 flex items-center gap-1" onClick={buildGraph}>
            <IconChart size={13} /> 知识图谱
          </button>
          <button className="btn-gradient btn-click text-xs py-2 px-3" onClick={handleCreate}>新建卡片</button>
        </div>
      </div>

      {/* 随手记输入框 */}
      {showQuickNote && (
        <div className="glass-card p-4 space-y-3 animate-fade-in">
          <div className="flex items-center gap-2">
            <IconLightbulb size={15} style={{ color: "#f59e0b" }} />
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>随手记</span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>— 记录一闪而过的想法</span>
            <div className="flex-1" />
            <button className="cursor-pointer" style={{ color: "var(--text-muted)" }}
              onClick={() => setShowQuickNote(false)}><IconX size={14} /></button>
          </div>
          <input className="input-glass text-sm" placeholder="想法标题..." value={quickTitle}
            onChange={e => setQuickTitle(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) handleQuickNote(); }} />
          <textarea className="input-glass text-sm" rows={3} placeholder="详细描述你的想法..."
            value={quickContent} onChange={e => setQuickContent(e.target.value)} />
          <div className="flex justify-end gap-2">
            <button className="btn-ghost text-xs py-1.5" onClick={() => setShowQuickNote(false)}>取消</button>
            <button className="btn-gradient btn-click text-xs py-1.5 px-4" onClick={handleQuickNote}>保存</button>
          </div>
        </div>
      )}

      {/* 导入工具栏 */}
      {view === "categories" && (
        <div className="glass-card p-4 space-y-3">
          <div className="flex gap-3 items-center flex-wrap">
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>导入:</span>
            <button onClick={handleDeepSeekImport} disabled={importing}
              className="btn-gradient btn-click text-xs py-1.5 whitespace-nowrap disabled:opacity-50">
              <IconBrain size={13} /> DeepSeek 智能导入
            </button>
            <button onClick={() => { loadImportGroups(); setView("importGroups"); }}
              className="btn-ghost text-xs py-1.5 disabled:opacity-50">
              导入记录
            </button>
            <button onClick={handleImportJSON} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">JSON 文件</button>
            <button onClick={handleImportMD} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">Markdown 文件</button>
            <button onClick={handleImportPDF} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">PDF 文献</button>
          </div>
          <div className="flex gap-2 items-center">
            <input className="input-glass flex-1 text-xs py-1.5" placeholder="粘贴网页链接导入知识卡片..."
              value={importUrl} onChange={e => setImportUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleImportUrl()} />
            <button onClick={handleImportUrl} disabled={importing || !importUrl.trim()}
              className="btn-ghost text-xs py-1.5 disabled:opacity-50">
              {importing ? "导入中..." : "抓取导入"}
            </button>
          </div>
          {importStatus && (
            <pre className="text-xs whitespace-pre-wrap rounded-lg p-3" style={{
              color: importStatus.includes("失败") || importStatus.includes("❌") ? "#ef4444" :
                     importStatus.includes("✅") ? "var(--accent-green)" : "var(--text-secondary)",
              background: "var(--hover-bg)", fontFamily: "inherit",
            }}>
              {importStatus}
            </pre>
          )}
        </div>
      )}

      {/* 搜索 + 筛选 */}
      {(view === "list" || view === "detail") && (
        <div className="space-y-2">
          <div className="flex gap-2 items-center">
            <input className="input-glass flex-1 text-sm" placeholder="搜索知识卡片..." value={search} onChange={e => setSearch(e.target.value)} />
            <select className="input-glass text-xs py-1.5" value={sortBy} onChange={e => setSortBy(e.target.value)}>
              <option value="updated_at">最近更新</option>
              <option value="created_at">创建时间</option>
              <option value="title">标题</option>
              <option value="star_rating">评分</option>
            </select>
            <select className="input-glass text-xs py-1.5" value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
              <option value="desc">降序</option>
              <option value="asc">升序</option>
            </select>
            <select className="input-glass text-xs py-1.5" value={starMin} onChange={e => setStarMin(Number(e.target.value))}>
              <option value={0}>全部评分</option>
              <option value={1}>≥1星</option>
              <option value={3}>≥3星</option>
              <option value={5}>5星</option>
            </select>
            <div className="flex gap-0.5 p-0.5 rounded-lg" style={{ background: "var(--hover-bg)" }}>
              <button className="p-1.5 rounded-md cursor-pointer transition-all"
                style={viewMode === "list" ? { background: "var(--glass-bg)" } : {}}
                onClick={() => setViewMode("list")}>
                <IconList size={14} style={{ color: viewMode === "list" ? "var(--accent-blue)" : "var(--text-muted)" }} />
              </button>
              <button className="p-1.5 rounded-md cursor-pointer transition-all"
                style={viewMode === "grid" ? { background: "var(--glass-bg)" } : {}}
                onClick={() => setViewMode("grid")}>
                <IconGrid size={14} style={{ color: viewMode === "grid" ? "var(--accent-blue)" : "var(--text-muted)" }} />
              </button>
            </div>
            <button className="px-2 py-1.5 rounded-lg text-xs cursor-pointer transition-all"
              style={batchMode ? { background: "rgba(59,130,246,0.15)", color: "var(--accent-blue)" } : { background: "var(--hover-bg)", color: "var(--text-muted)" }}
              onClick={() => { setBatchMode(!batchMode); setSelectedIds(new Set()); }}>
              {batchMode ? "取消" : "批量"}
            </button>
          </div>
          {batchMode && (
            <div className="flex gap-2 items-center px-2 py-1.5 rounded-lg" style={{ background: "rgba(59,130,246,0.06)" }}>
              <button className="text-xs cursor-pointer" style={{ color: "var(--accent-blue)" }} onClick={selectAll}>
                {selectedIds.size === cards.length ? "取消全选" : "全选"}
              </button>
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>已选 {selectedIds.size} 项</span>
              {selectedIds.size > 0 && (
                <>
                  <button className="text-xs cursor-pointer" style={{ color: "var(--accent-green)" }} onClick={handleBatchExport}>导出</button>
                  <button className="text-xs cursor-pointer" style={{ color: "#ef4444" }} onClick={handleBatchDelete}>删除</button>
                </>
              )}
            </div>
          )}
          {allTags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              <button className="px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors"
                style={!tagFilter ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" } : { color: "var(--text-muted)" }}
                onClick={() => setTagFilter("")}>全部</button>
              {allTags.slice(0, 15).map(t => {
                const tc = getTagColor(t.name);
                return (
                  <button key={t.name} className="px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors"
                    style={tagFilter === t.name ? { background: tc.bg, color: tc.color } : { color: "var(--text-muted)" }}
                    onClick={() => setTagFilter(tagFilter === t.name ? "" : t.name)}>
                    {t.name} ({t.usage_count})
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 分类视图 */}
      {view === "categories" && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {categoryCounts.map(cat => {
            const CatIcon = CATEGORY_ICONS[cat.iconKey] || IconFile;
            // 该类型最近 3 张卡片
            const recentCards = allCards.filter(c => c.source_type === cat.key).slice(0, 3);
            return (
            <div key={cat.key} className="glass-card p-5 cursor-pointer glass-card-hover flex flex-col gap-3"
              onClick={() => handleCategoryClick(cat.key)}>
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: `${cat.color}15`, color: cat.color }}><CatIcon size={18} /></span>
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{cat.label}</h3>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cat.count} 张卡片</p>
                </div>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border-color)" }}>
                <div className="h-full rounded-full" style={{ background: cat.color, width: `${Math.min(100, cat.count * 10)}%` }} />
              </div>
              {/* 最近卡片简略 */}
              {recentCards.length > 0 ? (
                <div className="space-y-1.5 pt-1 border-t" style={{ borderColor: "var(--border-color)" }}>
                  {recentCards.map(c => (
                    <div key={c.id} className="flex items-center gap-2" onClick={e => { e.stopPropagation(); handleCardClick(c); }}>
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: cat.color }} />
                      <span className="text-xs truncate cursor-pointer hover:underline" style={{ color: "var(--text-secondary)" }}>
                        {c.title}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] pt-1 border-t" style={{ borderColor: "var(--border-color)", color: "var(--text-muted)" }}>
                  暂无卡片
                </p>
              )}
            </div>
            );
          })}
        </div>
      )}

      {/* ═══ 导入分组列表 ═══ */}
      {view === "importGroups" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
              DeepSeek 对话导入记录（{importGroups.length} 个分组）
            </span>
            <button onClick={handleDeepSeekImport} disabled={importing}
              className="btn-gradient btn-click text-xs py-1.5 whitespace-nowrap disabled:opacity-50">
              + 新增导入
            </button>
          </div>

          {importGroups.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无导入记录</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                点击「新增导入」上传 DeepSeek 对话 JSON，AI 将自动分析生成知识卡片
              </p>
            </div>
          ) : importGroups.map(group => (
            <div key={group.id}
              className="glass-card p-4 cursor-pointer glass-card-hover group"
              onClick={() => handleGroupClick(group)}>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                      style={{
                        background: group.status === "completed" ? "rgba(16,185,129,0.1)" :
                                   group.status === "failed" ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.1)",
                        color: group.status === "completed" ? "var(--accent-green)" :
                               group.status === "failed" ? "#ef4444" : "var(--accent-blue)",
                      }}>
                      {group.status === "completed" ? "完成" : group.status === "failed" ? "失败" : "处理中"}
                    </span>
                    <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{group.title}</h3>
                  </div>

                  {group.status === "processing" && (
                    <p className="text-xs mb-1" style={{ color: "var(--accent-blue)" }}>{group.progress}</p>
                  )}

                  {group.summary && (
                    <p className="text-xs line-clamp-2 mb-1" style={{ color: "var(--text-secondary)" }}>{group.summary}</p>
                  )}

                  <div className="flex gap-3 text-[10px]" style={{ color: "var(--text-muted)" }}>
                    <span>{group.message_count} 条消息</span>
                    <span>{group.card_count} 张卡片</span>
                    <span>{new Date(group.created_at).toLocaleString("zh-CN")}</span>
                    {group.original_filename && <span className="flex items-center gap-1"><IconFolder size={13} /> {group.original_filename}</span>}
                  </div>

                  {group.knowledge_domain && group.knowledge_domain.length > 0 && (
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {group.knowledge_domain.map(d => (
                        <span key={d} className="text-[9px] px-1.5 py-0.5 rounded"
                          style={{ background: "rgba(139,92,246,0.08)", color: "#8b5cf6" }}>{d}</span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={(e) => handleDeleteGroup(group.id, e)}
                    className="text-xs px-2 py-1 rounded-lg cursor-pointer"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}>
                    删除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ═══ 导入分组详情 ═══ */}
      {view === "importGroupDetail" && selectedGroup && (
        <div className="space-y-4">
          {/* 分组信息 */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                style={{
                  background: selectedGroup.status === "completed" ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
                  color: selectedGroup.status === "completed" ? "var(--accent-green)" : "#ef4444",
                }}>
                {selectedGroup.status === "completed" ? "处理完成" : "处理失败"}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {selectedGroup.message_count} 条消息 → {selectedGroup.card_count} 张知识卡片
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {new Date(selectedGroup.created_at).toLocaleString("zh-CN")}
              </span>
              <div className="flex-1" />
              <button onClick={(e) => handleDeleteGroup(selectedGroup.id, e)}
                className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ color: "#ef4444" }}>
                删除分组
              </button>
            </div>

            {selectedGroup.summary && (
              <div>
                <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>分组概览</p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{selectedGroup.summary}</p>
              </div>
            )}

            {selectedGroup.knowledge_domain && selectedGroup.knowledge_domain.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {selectedGroup.knowledge_domain.map(d => (
                  <span key={d} className="text-[10px] px-2 py-0.5 rounded-full"
                    style={{ background: "rgba(139,92,246,0.08)", color: "#8b5cf6" }}>{d}</span>
                ))}
              </div>
            )}

            {selectedGroup.error && (
              <p className="text-xs" style={{ color: "#ef4444" }}>错误: {selectedGroup.error}</p>
            )}
          </div>

          {/* 话题卡片列表 */}
          <div className="space-y-2">
            <p className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>
              会话知识卡片（{groupCards.length} 张）
            </p>
            {groupCards.map(card => (
              <div key={card.id}
                className="glass-card p-4 cursor-pointer glass-card-hover group"
                onClick={() => { setSelectedCard(card); setView("detail"); }}>
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>{card.title}</h3>
                    <p className="text-xs line-clamp-2 mb-1" style={{ color: "var(--text-secondary)" }}>{card.summary || "无摘要"}</p>
                    {card.tags && card.tags.length > 0 && (
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {card.tags.map(t => (
                          <span key={t} className="text-[9px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(139,92,246,0.08)", color: "#8b5cf6" }}>{t}</span>
                        ))}
                      </div>
                    )}
                    {card.category_path && (
                      <span className="text-[9px] mt-1 inline-flex items-center gap-0.5" style={{ color: "var(--text-muted)" }}>
                        <IconFolder size={10} /> {card.category_path}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1 flex-shrink-0">
                    {card.chat_session_id && (
                      <button onClick={(e) => { e.stopPropagation(); window.location.hash = `chat-${card.chat_session_id}`; }}
                        className="text-xs px-2 py-1 rounded-lg cursor-pointer"
                        style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}
                        title="查看完整对话">
                        <IconChat size={12} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 卡片列表 / 网格 */}
      {view === "list" && viewMode === "list" && (
        <div className="space-y-2">
          {loading && (
            <div className="glass-card p-4 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>加载中...</p>
            </div>
          )}
          {loadError && (
            <div className="glass-card p-4 text-center">
              <p className="text-sm" style={{ color: "#ef4444" }}>{loadError}</p>
              <button className="text-xs mt-2 cursor-pointer" style={{ color: "var(--accent-blue)" }} onClick={() => loadCards()}>重试</button>
            </div>
          )}
          {!loading && !loadError && filteredCards.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>该分类下暂无卡片</p>
              <button className="text-xs mt-2 cursor-pointer" style={{ color: "var(--accent-blue)" }} onClick={() => loadCards()}>刷新</button>
            </div>
          ) : filteredCards.map(card => (
            <div key={card.id}
              className="glass-card p-4 flex items-start gap-4 cursor-pointer glass-card-hover group"
              onClick={() => batchMode ? toggleSelect(card.id) : handleCardClick(card)}>
              {batchMode && (
                <input type="checkbox" checked={selectedIds.has(card.id)}
                  onChange={() => toggleSelect(card.id)} className="mt-1 flex-shrink-0"
                  onClick={e => e.stopPropagation()} />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{card.title}</h3>
                  <span className="flex-shrink-0 flex gap-0.5" style={{ color: "#fbbf24" }}>
                    {Array.from({length: 5}, (_, i) => <IconStar key={i} size={12} filled={i < card.star_rating} />)}
                  </span>
                  {card.import_group_id && (
                    <span className="text-[9px] px-1 py-0.5 rounded" style={{ background: "rgba(139,92,246,0.08)", color: "#8b5cf6" }}>导入</span>
                  )}
                </div>
                <p className="text-xs line-clamp-2" style={{ color: "var(--text-secondary)" }}>{card.summary || "无摘要"}</p>
                {card.tags && card.tags.length > 0 && (
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {card.tags.slice(0, 5).map(t => {
                      const tc = getTagColor(t);
                      return (
                        <span key={t} className="text-[9px] px-1.5 py-0.5 rounded cursor-pointer hover:opacity-80 transition-opacity"
                          style={{ background: tc.bg, color: tc.color }}
                          onClick={(e) => { e.stopPropagation(); setTagFilter(tagFilter === t ? "" : t); }}>{t}</span>
                      );
                    })}
                  </div>
                )}
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{new Date(card.updated_at || card.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex flex-col gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                {card.chat_session_id && (
                  <button onClick={(e) => { e.stopPropagation(); window.location.hash = `chat-${card.chat_session_id}`; }}
                    className="text-xs px-2 py-1 rounded-lg cursor-pointer"
                    style={{ color: "var(--accent-blue)" }}
                    title="查看关联对话">
                    <IconChat size={14} />
                  </button>
                )}
                {card.source_type === "deepseek" && card.chat_session_id && (!card.summary || card.summary.includes("摘要生成失败")) && (
                  <button onClick={(e) => handleRegenerateSummary(card.id, e)}
                    className="text-xs px-2 py-1 rounded-lg cursor-pointer transition-colors"
                    style={{ color: regeneratingId === card.id ? "var(--text-muted)" : "#8b5cf6" }}
                    disabled={regeneratingId === card.id}
                    title="重新生成摘要">
                    {regeneratingId === card.id ? "生成中..." : "生成摘要"}
                  </button>
                )}
                <button onClick={(e) => handleDelete(card.id, e)}
                  className="text-xs px-2 py-1 rounded-lg cursor-pointer transition-colors"
                  style={{ color: "var(--text-muted)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}>删除</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 网格视图 */}
      {view === "list" && viewMode === "grid" && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {loading && (
            <div className="col-span-full glass-card p-4 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>加载中...</p>
            </div>
          )}
          {loadError && (
            <div className="col-span-full glass-card p-4 text-center">
              <p className="text-sm" style={{ color: "#ef4444" }}>{loadError}</p>
              <button className="text-xs mt-2 cursor-pointer" style={{ color: "var(--accent-blue)" }} onClick={() => loadCards()}>重试</button>
            </div>
          )}
          {!loading && !loadError && filteredCards.length === 0 ? (
            <div className="col-span-full glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>该分类下暂无卡片</p>
              <button className="text-xs mt-2 cursor-pointer" style={{ color: "var(--accent-blue)" }} onClick={() => loadCards()}>刷新</button>
            </div>
          ) : filteredCards.map(card => (
            <div key={card.id} className="glass-card p-3 cursor-pointer glass-card-hover group flex flex-col gap-2"
              onClick={() => handleCardClick(card)}>
              <h3 className="text-sm font-semibold line-clamp-2" style={{ color: "var(--text-primary)" }}>{card.title}</h3>
              <p className="text-xs line-clamp-3 flex-1" style={{ color: "var(--text-secondary)" }}>{card.summary || "无摘要"}</p>
              {card.tags && card.tags.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {card.tags.slice(0, 3).map(t => {
                    const tc = getTagColor(t);
                    return (
                      <span key={t} className="text-[9px] px-1 py-0.5 rounded cursor-pointer hover:opacity-80 transition-opacity"
                        style={{ background: tc.bg, color: tc.color }}
                        onClick={(e) => { e.stopPropagation(); setTagFilter(tagFilter === t ? "" : t); }}>{t}</span>
                    );
                  })}
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="flex gap-0.5" style={{ color: "#fbbf24" }}>
                  {Array.from({length: 5}, (_, i) => <IconStar key={i} size={10} filled={i < card.star_rating} />)}
                </span>
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{new Date(card.updated_at || card.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {card.chat_session_id && (
                  <button onClick={(e) => { e.stopPropagation(); window.location.hash = `chat-${card.chat_session_id}`; }}
                    className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer"
                    style={{ color: "var(--accent-blue)" }}
                    title="查看关联对话">
                    <IconChat size={12} />
                  </button>
                )}
                {card.source_type === "deepseek" && card.chat_session_id && (!card.summary || card.summary.includes("摘要生成失败")) && (
                  <button onClick={(e) => { e.stopPropagation(); handleRegenerateSummary(card.id, e); }}
                    className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer"
                    style={{ color: regeneratingId === card.id ? "var(--text-muted)" : "#8b5cf6" }}
                    disabled={regeneratingId === card.id}>
                    {regeneratingId === card.id ? "..." : "生成摘要"}
                  </button>
                )}
                <button onClick={(e) => handleDelete(card.id, e)}
                  className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer"
                  style={{ color: "var(--text-muted)" }}>删除</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 卡片详情 */}
      {view === "detail" && selectedCard && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
              {selectedCard.source_type === "literature" ? "文献" :
               selectedCard.source_type === "deepseek" ? "AI" :
               selectedCard.source_type === "note" ? "随手记" : "手动"}
            </span>
            <span className="flex gap-0.5" style={{ color: "#fbbf24" }}>
              {Array.from({length: 5}, (_, i) => <IconStar key={i} size={14} filled={i < selectedCard.star_rating} />)}
            </span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              {new Date(selectedCard.created_at).toLocaleString("zh-CN")}
            </span>
            <div className="flex-1" />
            {(selectedCard as any).import_group_id && (
              <button className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(139,92,246,0.1)", color: "#8b5cf6" }}
                onClick={async () => {
                  try {
                    const detail = await importGroupApi.get((selectedCard as any).import_group_id);
                    setSelectedGroup(detail);
                    setGroupCards(detail.cards || []);
                    setView("importGroupDetail");
                  } catch (err) { alert("加载导入分组失败: " + err); }
                }}>
                查看导入对话
              </button>
            )}
            {selectedCard.source_type === "deepseek" && (selectedCard as any).chat_session_id && (!selectedCard.summary || selectedCard.summary.includes("摘要生成失败")) && (
              <button className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(139,92,246,0.1)", color: "#8b5cf6" }}
                disabled={regeneratingId === selectedCard.id}
                onClick={() => handleRegenerateSummary(selectedCard.id)}>
                {regeneratingId === selectedCard.id ? "生成中..." : "重新生成摘要"}
              </button>
            )}
            {(selectedCard as any).chat_session_id && !(selectedCard as any).import_group_id && (
              <button className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}
                onClick={() => { window.location.hash = `chat-${(selectedCard as any).chat_session_id}`; }}>
                查看关联对话
              </button>
            )}
            {/* v4.6.1: 随手记编辑按钮 */}
            {selectedCard.source_type === "note" && !editingNote && (
              <button className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b" }}
                onClick={() => { setEditingNote(true); setEditTitle(selectedCard.title); setEditSummary(selectedCard.summary || ""); }}>
                编辑
              </button>
            )}
          </div>

          {/* 标题：编辑模式 vs 只读模式 */}
          {editingNote ? (
            <input className="input-glass text-lg font-semibold w-full" value={editTitle}
              onChange={e => setEditTitle(e.target.value)} placeholder="想法标题..." />
          ) : (
            <div><h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{selectedCard.title}</h3></div>
          )}

          {/* 摘要/想法内容：编辑模式 vs 只读模式 */}
          {editingNote ? (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>想法内容</p>
              <textarea className="input-glass text-sm w-full" rows={6} value={editSummary}
                onChange={e => setEditSummary(e.target.value)} placeholder="记录你的想法..." />
              <div className="flex justify-end gap-2 mt-2">
                <button className="btn-ghost text-xs py-1.5" onClick={() => setEditingNote(false)}>取消</button>
                <button className="btn-gradient btn-click text-xs py-1.5 px-4" onClick={async () => {
                  if (!editTitle.trim()) { alert("标题不能为空"); return; }
                  try {
                    await knowledgeApi.updateCard(selectedCard.id, { title: editTitle.trim(), summary: editSummary.trim() });
                    const updated = { ...selectedCard, title: editTitle.trim(), summary: editSummary.trim() };
                    setSelectedCard(updated);
                    setCards(prev => prev.map(c => c.id === selectedCard.id ? updated : c));
                    setAllCards(prev => prev.map(c => c.id === selectedCard.id ? updated : c));
                    setEditingNote(false);
                  } catch (err) { alert("保存失败: " + err); }
                }}>保存</button>
              </div>
            </div>
          ) : selectedCard.summary && (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                {selectedCard.source_type === "note" ? "想法内容" : "摘要"}
              </p>
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>{selectedCard.summary}</p>
            </div>
          )}

          {selectedCard.key_points && selectedCard.key_points.length > 0 && (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>要点</p>
              <ul className="space-y-1">
                {selectedCard.key_points.map((kp, i) => (
                  <li key={i} className="text-sm flex items-start gap-2" style={{ color: "var(--text-secondary)" }}>
                    <span className="flex-shrink-0" style={{ color: "var(--accent-blue)" }}>•</span>{kp}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selectedCard.user_notes && !selectedCard.user_notes.startsWith("chat_session:") && (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>笔记</p>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{selectedCard.user_notes}</p>
            </div>
          )}

          <div className="flex gap-2 pt-2" style={{ borderTop: "1px solid var(--border-color)" }}>
            <button className="btn-ghost text-xs" onClick={() => handleDelete(selectedCard.id)}>删除卡片</button>
          </div>
        </div>
      )}

      {/* 知识图谱弹窗 */}
      {showGraph && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}
          onClick={() => setShowGraph(false)}>
          <div className="glass-card p-6 max-w-3xl w-full mx-4 max-h-[80vh] overflow-hidden animate-fade-in"
            style={{ background: "var(--glass-bg)", backdropFilter: "blur(20px)" }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>知识图谱</h3>
              <button className="btn-ghost text-xs" onClick={() => setShowGraph(false)}>关闭</button>
            </div>
            <div className="relative" style={{ height: "400px", background: "var(--hover-bg)", borderRadius: "12px" }}>
              <svg width="100%" height="100%" viewBox="0 0 400 400">
                {graphEdges.map((edge, i) => {
                  const from = graphNodes.find(n => n.id === edge.from);
                  const to = graphNodes.find(n => n.id === edge.to);
                  if (!from || !to) return null;
                  return <line key={i} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="var(--border-color)" strokeWidth="1" opacity="0.5" />;
                })}
                {graphNodes.map(node => (
                  <g key={node.id} onClick={() => { const card = cards.find(c => c.id === node.id); if (card) { setSelectedCard(card); setShowGraph(false); setView("detail"); } }}
                    style={{ cursor: "pointer" }}>
                    <circle cx={node.x} cy={node.y} r={node.size} fill={node.color} opacity="0.8" />
                    <text x={node.x} y={node.y + node.size + 12} textAnchor="middle" fontSize="10"
                      fill="var(--text-secondary)">{node.label}</text>
                  </g>
                ))}
              </svg>
            </div>
            <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
              节点大小表示评分，颜色表示来源分类，连线表示共同标签。点击节点查看详情。
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
