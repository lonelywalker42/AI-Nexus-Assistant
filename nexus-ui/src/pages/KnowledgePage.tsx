import { useEffect, useState } from "react";
import { knowledgeApi, type KnowledgeCard } from "../api/client";
import { IconFile, IconChat, IconArrowLeft, IconStar } from "../components/Icons";

const CATEGORIES = [
  { key: "literature", label: "文献导入", iconKey: "file", color: "#3b82f6" },
  { key: "deepseek", label: "AI 对话", iconKey: "chat", color: "#8b5cf6" },
  { key: "manual", label: "手动创建", iconKey: "edit", color: "#10b981" },
];

const CATEGORY_ICONS: Record<string, React.FC<{ size?: number }>> = {
  file: IconFile, chat: IconChat, edit: IconFile,
};

export default function KnowledgePage() {
  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState("");

  // 视图状态: "categories" | "list" | "detail"
  const [view, setView] = useState<"categories" | "list" | "detail">("categories");
  const [activeCategory, setActiveCategory] = useState("");
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null);

  const loadCards = () => knowledgeApi.listCards({ search }).then(setCards).catch(console.error);
  useEffect(() => { loadCards(); }, [search]);

  // 按来源分类统计
  const categoryCounts = CATEGORIES.map(cat => ({
    ...cat,
    count: cards.filter(c => c.source_type === cat.key).length,
  }));

  // 当前分类下的卡片
  const filteredCards = activeCategory
    ? cards.filter(c => c.source_type === activeCategory)
    : cards;

  const handleCreate = async () => {
    const title = prompt("卡片标题:");
    if (!title) return;
    await knowledgeApi.createCard({ title, source_type: "manual" });
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
    // 尝试获取完整卡片数据
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

  // JSON 导入 - 支持 ai-literature 和 DeepSeek 格式
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

        // 检测格式
        const isAiLiterature = !!(data.kbPapers || data.papers);
        const isDeepSeek = !!(data.topics);
        const format = isAiLiterature ? "ai-literature" : isDeepSeek ? "DeepSeek" : "未知";
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

  // Markdown 导入
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

  // PDF 导入 - 增强处理流程反馈
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
        setImportStatus(`[${i + 1}/${files.length}] 正在处理: ${file.name}\n提取文本 → AI 分析 → 生成卡片...`);
        try {
          const formData = new FormData();
          formData.append("file", file);
          const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/pdf", {
            method: "POST",
            body: formData,
          });
          const result = await res.json();
          if (result.error) {
            failCount++;
            results.push(`❌ ${file.name}: ${result.error}`);
          } else {
            successCount++;
            results.push(`✅ ${file.name}: ${result.title}${result.tags?.length ? ` [${result.tags.join(", ")}]` : ""}`);
          }
        } catch (err) {
          failCount++;
          results.push(`❌ ${file.name}: ${err}`);
        }
      }

      setImportStatus(
        `处理完成: ${successCount} 成功, ${failCount} 失败\n` +
        results.join("\n")
      );
      setImporting(false);
      loadCards();
    };
    input.click();
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
             "知识库"}
          </h2>
        </div>
        <div className="flex gap-2">
          <button className="btn-gradient btn-click" onClick={handleCreate}>新建卡片</button>
        </div>
      </div>

      {/* 导入工具栏 */}
      {view === "categories" && (
        <div className="glass-card p-4 space-y-3">
          <div className="flex gap-3 items-center flex-wrap">
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>导入:</span>
            <button onClick={handleImportJSON} disabled={importing} className="btn-ghost disabled:opacity-50">
              {importing ? "导入中..." : "JSON 文件"}
            </button>
            <button onClick={handleImportMD} disabled={importing} className="btn-ghost disabled:opacity-50">
              Markdown 文件
            </button>
            <button onClick={handleImportPDF} disabled={importing} className="btn-ghost disabled:opacity-50">
              PDF 文献
            </button>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              支持 ai-literature JSON、DeepSeek 对话 JSON、Markdown、PDF
            </span>
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

      {/* 搜索 */}
      {view !== "categories" && (
        <div className="flex gap-3">
          <input className="input-glass flex-1" placeholder="搜索知识卡片..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      )}

      {/* 分类视图 - Issue 5 */}
      {view === "categories" && (
        <div className="grid grid-cols-3 gap-4">
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

      {/* 卡片列表 - Issue 5/6 */}
      {view === "list" && (
        <div className="space-y-2">
          {filteredCards.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>该分类下暂无卡片</p>
            </div>
          ) : filteredCards.map(card => (
            <div
              key={card.id}
              className="glass-card p-4 flex items-start gap-4 cursor-pointer glass-card-hover"
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
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{new Date(card.created_at).toLocaleDateString()}</span>
              </div>
              <button onClick={(e) => handleDelete(card.id, e)} className="text-xs flex-shrink-0 transition-colors"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
              >删除</button>
            </div>
          ))}
        </div>
      )}

      {/* 卡片详情 - Issue 6 */}
      {view === "detail" && selectedCard && (
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
              {selectedCard.source_type === "literature" ? "文献" : selectedCard.source_type === "deepseek" ? "AI" : "手动"}
            </span>
            <span className="flex gap-0.5" style={{ color: "#fbbf24" }}>
              {Array.from({length: 5}, (_, i) => <IconStar key={i} size={14} filled={i < selectedCard.star_rating} />)}
            </span>
            <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>
              {new Date(selectedCard.created_at).toLocaleString("zh-CN")}
            </span>
          </div>

          <div>
            <h3 className="text-lg font-semibold" style={{ color: "var(--text-primary)" }}>{selectedCard.title}</h3>
          </div>

          {selectedCard.summary && (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>摘要</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{selectedCard.summary}</p>
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

          {selectedCard.user_notes && (
            <div>
              <p className="text-xs font-semibold mb-1" style={{ color: "var(--text-muted)" }}>笔记</p>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{selectedCard.user_notes}</p>
            </div>
          )}

          <div className="flex gap-2 pt-2" style={{ borderTop: "1px solid var(--border-color)" }}>
            <button className="btn-ghost" onClick={() => handleDelete(selectedCard.id)}>删除卡片</button>
          </div>
        </div>
      )}
    </div>
  );
}
