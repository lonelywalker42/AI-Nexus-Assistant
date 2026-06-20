import { useEffect, useState } from "react";
import { knowledgeApi, chatApi, type KnowledgeCard } from "../api/client";
import { IconFile, IconChat, IconArrowLeft, IconStar, IconLightbulb, IconX } from "../components/Icons";

const CATEGORIES = [
  { key: "literature", label: "文献导入", iconKey: "file", color: "#3b82f6" },
  { key: "deepseek", label: "AI 对话", iconKey: "chat", color: "#8b5cf6" },
  { key: "note", label: "随手记", iconKey: "lightbulb", color: "#f59e0b" },
  { key: "manual", label: "手动创建", iconKey: "edit", color: "#10b981" },
];

const CATEGORY_ICONS: Record<string, React.FC<{ size?: number }>> = {
  file: IconFile, chat: IconChat, edit: IconFile, lightbulb: IconLightbulb,
};

export default function KnowledgePage() {
  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importStatus, setImportStatus] = useState("");

  // 视图状态
  const [view, setView] = useState<"categories" | "list" | "detail">("categories");
  const [activeCategory, setActiveCategory] = useState("");
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null);

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

  // 防抖搜索
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadCards = () => knowledgeApi.listCards({
    search: debouncedSearch, sort_by: sortBy, sort_order: sortOrder,
    star_min: starMin || undefined, tag: tagFilter || undefined,
  }).then(setCards).catch(console.error);
  useEffect(() => { loadCards(); }, [debouncedSearch, sortBy, sortOrder, starMin, tagFilter]);

  // 加载标签
  useEffect(() => {
    knowledgeApi.listTags().then(setAllTags).catch(() => {});
  }, []);

  const categoryCounts = CATEGORIES.map(cat => ({
    ...cat,
    count: cards.filter(c => c.source_type === cat.key).length,
  }));

  const filteredCards = activeCategory
    ? cards.filter(c => c.source_type === activeCategory)
    : cards;

  const handleCreate = async () => {
    const title = prompt("卡片标题:");
    if (!title) return;
    await knowledgeApi.createCard({ title, source_type: "manual" });
    loadCards();
  };

  // 随手记快速创建
  const handleQuickNote = async () => {
    if (!quickTitle.trim()) return;
    await knowledgeApi.createCard({
      title: quickTitle.trim(),
      summary: quickContent.trim(),
      source_type: "note",
    });
    setQuickTitle("");
    setQuickContent("");
    setShowQuickNote(false);
    loadCards();
  };

  const handleDelete = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!confirm("确定删除？")) return;
    await knowledgeApi.deleteCard(id);
    loadCards();
    if (selectedCard?.id === id) {
      setSelectedCard(null);
      setView(activeCategory ? "list" : "categories");
    }
  };

  const handleCardClick = async (card: KnowledgeCard) => {
    try {
      const full = await knowledgeApi.getCard(card.id);
      setSelectedCard(full);
    } catch {
      setSelectedCard(card);
    }
    setView("detail");
  };

  const handleBackFromDetail = () => {
    setSelectedCard(null);
    setView(activeCategory ? "list" : "categories");
  };

  const handleCategoryClick = (key: string) => {
    setActiveCategory(key);
    setView("list");
  };

  const handleBackFromList = () => {
    setActiveCategory("");
    setView("categories");
  };

  // 从随手记卡片创建 AI 对话
  const handleChatFromCard = async (card: KnowledgeCard) => {
    try {
      const res = await chatApi.createSession(`IDEA: ${card.title.slice(0, 30)}`, "idea");
      await chatApi.addMessage(res.id,
        `请帮我分析和拓展以下想法：\n\n标题：${card.title}\n内容：${card.summary || "无"}\n\n请提供：1) 这个想法的可行性分析 2) 可能的研究方向 3) 建议的下一步行动`
      );
      // 更新卡片，关联对话 session
      await knowledgeApi.updateCard(card.id, { user_notes: `chat_session:${res.id}` });
      // 跳转到对话页面（通过 hash 标记 session id）
      window.location.hash = `chat-${res.id}`;
      alert(`已创建 AI 对话「IDEA: ${card.title.slice(0, 30)}」，请前往 AI 对话页面查看`);
    } catch (err) {
      alert("创建对话失败: " + err);
    }
  };

  // JSON 导入
  const handleImportJSON = () => {
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
        const isAiLiterature = !!(data.kbPapers || data.papers);
        const isDeepSeek = !!(data.topics);
        const isChatGPT = !!(data.messages) && Array.isArray(data.messages);
        const isMimo = !!(data.conversations) || !!(data.data?.conversation);
        const format = isAiLiterature ? "ai-literature" : isDeepSeek ? "DeepSeek" : isChatGPT ? "ChatGPT" : isMimo ? "mimo" : "未知";
        setImportStatus(`检测到 ${format} 格式，正在导入...`);
        const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/json", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const result = await res.json();
        setImportStatus(`导入完成: ${result.imported} 条记录 (${format} 格式)`);
        loadCards();
      } catch (err) {
        setImportStatus(`导入失败: ${err}`);
      }
      setImporting(false);
    };
    input.click();
  };

  const handleImportMD = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".md,.txt";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true);
      setImportStatus("正在导入 Markdown...");
      try {
        const text = await file.text();
        const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/md", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: text, filename: file.name }),
        });
        const result = await res.json();
        setImportStatus(`导入完成: ${result.imported} 条记录`);
        loadCards();
      } catch (err) {
        setImportStatus(`导入失败: ${err}`);
      }
      setImporting(false);
    };
    input.click();
  };

  const handleImportPDF = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf";
    input.multiple = true;
    input.onchange = async (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length === 0) return;
      setImporting(true);
      let successCount = 0;
      let failCount = 0;
      const results: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setImportStatus(`[${i + 1}/${files.length}] 正在处理: ${file.name}...`);
        try {
          const arrayBuffer = await file.arrayBuffer();
          const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/pdf", {
            method: "POST",
            headers: {
              "Content-Type": "application/octet-stream",
              "X-Filename": encodeURIComponent(file.name),
            },
            body: arrayBuffer,
          });
          const result = await res.json();
          if (result.error) {
            failCount++;
            results.push(`❌ ${file.name}: ${result.error}`);
          } else {
            successCount++;
            results.push(`✅ ${file.name}: ${result.title}`);
          }
        } catch (err) {
          failCount++;
          results.push(`❌ ${file.name}: ${err}`);
        }
      }
      setImportStatus(`处理完成: ${successCount} 成功, ${failCount} 失败\n${results.join("\n")}`);
      setImporting(false);
      loadCards();
    };
    input.click();
  };

  // URL 导入
  const handleImportUrl = async () => {
    if (!importUrl.trim()) return;
    setImporting(true);
    setImportStatus(`正在抓取: ${importUrl}...`);
    try {
      const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: importUrl }),
      });
      const result = await res.json();
      if (result.error) {
        setImportStatus(`❌ 导入失败: ${result.error}`);
      } else {
        setImportStatus(`✅ 导入完成: ${result.title}`);
        setImportUrl("");
        loadCards();
      }
    } catch (err) {
      setImportStatus(`❌ 导入失败: ${err}`);
    }
    setImporting(false);
  };

  return (
    <div className="space-y-5">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {view !== "categories" && (
            <button onClick={view === "detail" ? handleBackFromDetail : handleBackFromList}
              className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors cursor-pointer"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            ><IconArrowLeft size={16} /></button>
          )}
          <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            {view === "detail" ? selectedCard?.title || "卡片详情" :
             view === "list" ? (CATEGORIES.find(c => c.key === activeCategory)?.label || "全部卡片") :
             "IDEA"}
          </h2>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost text-xs py-2 flex items-center gap-1" onClick={() => setShowQuickNote(v => !v)}>
            <IconLightbulb size={13} /> 随手记
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
          <input
            className="input-glass text-sm"
            placeholder="想法标题..."
            value={quickTitle}
            onChange={e => setQuickTitle(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) handleQuickNote(); }}
          />
          <textarea
            className="input-glass text-sm"
            rows={3}
            placeholder="详细描述你的想法..."
            value={quickContent}
            onChange={e => setQuickContent(e.target.value)}
          />
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
            <button onClick={handleImportJSON} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">JSON 文件</button>
            <button onClick={handleImportMD} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">Markdown 文件</button>
            <button onClick={handleImportPDF} disabled={importing} className="btn-ghost text-xs py-1.5 disabled:opacity-50">PDF 文献</button>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              支持 ai-literature/DeepSeek/ChatGPT/mimo JSON、Markdown、PDF
            </span>
          </div>
          {/* URL 导入 */}
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
              color: importStatus.includes("失败") || importStatus.includes("❌") ? "#ef4444" : "#10b981",
              background: "var(--hover-bg)",
              fontFamily: "inherit",
            }}>
              {importStatus}
            </pre>
          )}
        </div>
      )}

      {/* 搜索 + 筛选 */}
      {view !== "categories" && (
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
                <span className="text-xs" style={{ color: viewMode === "list" ? "var(--accent-blue)" : "var(--text-muted)" }}>☰</span>
              </button>
              <button className="p-1.5 rounded-md cursor-pointer transition-all"
                style={viewMode === "grid" ? { background: "var(--glass-bg)" } : {}}
                onClick={() => setViewMode("grid")}>
                <span className="text-xs" style={{ color: viewMode === "grid" ? "var(--accent-blue)" : "var(--text-muted)" }}>⊞</span>
              </button>
            </div>
          </div>
          {/* 标签筛选 */}
          {allTags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              <button className="px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors"
                style={!tagFilter ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" } : { color: "var(--text-muted)" }}
                onClick={() => setTagFilter("")}>全部</button>
              {allTags.slice(0, 15).map(t => (
                <button key={t.name} className="px-2 py-0.5 rounded text-[10px] cursor-pointer transition-colors"
                  style={tagFilter === t.name ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" } : { color: "var(--text-muted)" }}
                  onClick={() => setTagFilter(tagFilter === t.name ? "" : t.name)}>
                  {t.name} ({t.usage_count})
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 分类视图 */}
      {view === "categories" && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {categoryCounts.map(cat => {
            const CatIcon = CATEGORY_ICONS[cat.iconKey] || IconFile;
            return (
            <div
              key={cat.key}
              className="glass-card p-5 cursor-pointer glass-card-hover"
              onClick={() => handleCategoryClick(cat.key)}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${cat.color}15`, color: cat.color }}><CatIcon size={18} /></span>
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{cat.label}</h3>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{cat.count} 张卡片</p>
                </div>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border-color)" }}>
                <div className="h-full rounded-full" style={{ background: cat.color, width: `${Math.min(100, cat.count * 10)}%` }} />
              </div>
            </div>
            );
          })}
        </div>
      )}

      {/* 卡片列表 / 网格 */}
      {view === "list" && viewMode === "list" && (
        <div className="space-y-2">
          {filteredCards.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>该分类下暂无卡片</p>
            </div>
          ) : filteredCards.map(card => (
            <div
              key={card.id}
              className="glass-card p-4 flex items-start gap-4 cursor-pointer glass-card-hover group"
              onClick={() => handleCardClick(card)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{card.title}</h3>
                  <span className="flex-shrink-0 flex gap-0.5" style={{ color: "#fbbf24" }}>
                    {Array.from({length: 5}, (_, i) => <IconStar key={i} size={12} filled={i < card.star_rating} />)}
                  </span>
                </div>
                <p className="text-xs line-clamp-2" style={{ color: "var(--text-secondary)" }}>{card.summary || "无摘要"}</p>
                {card.tags && card.tags.length > 0 && (
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {card.tags.slice(0, 5).map(t => (
                      <span key={t} className="text-[9px] px-1.5 py-0.5 rounded"
                        style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{t}</span>
                    ))}
                  </div>
                )}
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{new Date(card.updated_at || card.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex flex-col gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={(e) => { e.stopPropagation(); handleChatFromCard(card); }}
                  className="text-xs px-2 py-1 rounded-lg cursor-pointer transition-colors"
                  style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}
                  title="AI 对话分析"
                ><IconChat size={12} /></button>
                <button onClick={(e) => handleDelete(card.id, e)}
                  className="text-xs px-2 py-1 rounded-lg cursor-pointer transition-colors"
                  style={{ color: "var(--text-muted)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                >删除</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 网格视图 */}
      {view === "list" && viewMode === "grid" && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {filteredCards.length === 0 ? (
            <div className="col-span-full glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>该分类下暂无卡片</p>
            </div>
          ) : filteredCards.map(card => (
            <div key={card.id}
              className="glass-card p-3 cursor-pointer glass-card-hover group flex flex-col gap-2"
              onClick={() => handleCardClick(card)}>
              <h3 className="text-sm font-semibold line-clamp-2" style={{ color: "var(--text-primary)" }}>{card.title}</h3>
              <p className="text-xs line-clamp-3 flex-1" style={{ color: "var(--text-secondary)" }}>{card.summary || "无摘要"}</p>
              {card.tags && card.tags.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {card.tags.slice(0, 3).map(t => (
                    <span key={t} className="text-[9px] px-1 py-0.5 rounded"
                      style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{t}</span>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="flex gap-0.5" style={{ color: "#fbbf24" }}>
                  {Array.from({length: 5}, (_, i) => <IconStar key={i} size={10} filled={i < card.star_rating} />)}
                </span>
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{new Date(card.updated_at || card.created_at).toLocaleDateString()}</span>
              </div>
              {/* Hover actions */}
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={(e) => { e.stopPropagation(); handleChatFromCard(card); }}
                  className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer"
                  style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>AI</button>
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
            {/* AI 对话按钮 */}
            <button
              className="btn-ghost text-xs py-1.5 flex items-center gap-1.5"
              onClick={() => handleChatFromCard(selectedCard)}
            >
              <IconChat size={13} /> AI 对话分析
            </button>
            {/* 如果有关联对话，显示链接 */}
            {selectedCard.user_notes?.startsWith("chat_session:") && (
              <button
                className="text-xs px-2 py-1.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(139,92,246,0.1)", color: "#8b5cf6" }}
                onClick={() => {
                  const sid = selectedCard.user_notes.replace("chat_session:", "");
                  window.location.hash = `chat-${sid}`;
                  alert("请前往 AI 对话页面查看关联对话");
                }}
              >查看关联对话</button>
            )}
          </div>

          <div>
            <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{selectedCard.title}</h3>
          </div>

          {selectedCard.summary && (
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
                    <span className="flex-shrink-0" style={{ color: "var(--accent-blue)" }}>•</span>
                    {kp}
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
    </div>
  );
}
