import { useEffect, useState } from "react";
import { knowledgeApi, type KnowledgeCard } from "../api/client";

const SOURCE_BADGES: Record<string, { text: string; color: string }> = {
  manual: { text: "手动", color: "bg-slate-100 text-slate-600" },
  literature: { text: "文献", color: "bg-blue-50 text-blue-600" },
  deepseek: { text: "AI", color: "bg-purple-50 text-purple-600" },
};

export default function KnowledgePage() {
  const [cards, setCards] = useState<KnowledgeCard[]>([]);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [importing, setImporting] = useState(false);

  const loadCards = () => knowledgeApi.listCards({ search, source_type: sourceFilter }).then(setCards).catch(console.error);
  useEffect(() => { loadCards(); }, [search, sourceFilter]);

  const handleCreate = async () => {
    const title = prompt("卡片标题:");
    if (!title) return;
    await knowledgeApi.createCard({ title, source_type: "manual" });
    loadCards();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除？")) return;
    await knowledgeApi.deleteCard(id);
    loadCards();
  };

  const handleImportJSON = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true);
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/json", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const result = await res.json();
        alert(`导入完成: ${result.imported} 条记录`);
        loadCards();
      } catch (err) {
        alert(`导入失败: ${err}`);
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
      try {
        const text = await file.text();
        const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/md", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: text, filename: file.name }),
        });
        const result = await res.json();
        alert(`导入完成: ${result.imported} 条记录`);
        loadCards();
      } catch (err) {
        alert(`导入失败: ${err}`);
      }
      setImporting(false);
    };
    input.click();
  };

  const handleImportPDF = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/pdf", {
          method: "POST",
          body: formData,
        });
        const result = await res.json();
        if (result.error) {
          alert(`导入失败: ${result.error}`);
        } else {
          alert(`导入完成: ${result.title}`);
          loadCards();
        }
      } catch (err) {
        alert(`导入失败: ${err}`);
      }
      setImporting(false);
    };
    input.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">知识库</h2>
        <div className="flex gap-2">
          <button className="btn-gradient btn-click" onClick={handleCreate}>新建卡片</button>
        </div>
      </div>

      {/* 导入工具栏 */}
      <div className="glass-card p-4 flex gap-3 items-center">
        <span className="text-sm text-slate-500">导入:</span>
        <button
          onClick={handleImportJSON}
          disabled={importing}
          className="px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >{importing ? "导入中..." : "JSON 文件"}</button>
        <button
          onClick={handleImportMD}
          disabled={importing}
          className="px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >Markdown 文件</button>
        <button
          onClick={handleImportPDF}
          disabled={importing}
          className="px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >PDF 文献</button>
        <span className="text-xs text-slate-400 ml-2">支持 ai-literature JSON、DeepSeek 对话 JSON、Markdown、PDF</span>
      </div>

      <div className="flex gap-3">
        <input className="input-glass flex-1" placeholder="搜索知识卡片..." value={search} onChange={e => setSearch(e.target.value)} />
        <select className="input-glass w-40" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
          <option value="">全部来源</option>
          <option value="manual">手动创建</option>
          <option value="literature">文献导入</option>
          <option value="deepseek">AI 对话</option>
        </select>
      </div>

      {cards.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <p className="text-slate-400">暂无知识卡片</p>
          <p className="text-xs text-slate-300 mt-2">点击"新建卡片"或导入 JSON/Markdown/PDF 文件</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {cards.map(card => {
            const badge = SOURCE_BADGES[card.source_type] || SOURCE_BADGES.manual;
            return (
              <div key={card.id} className="glass-card p-5 space-y-3 cursor-pointer hover:border-primary-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${badge.color}`}>{badge.text}</span>
                  <span className="text-amber-400 text-xs">
                    {"★".repeat(card.star_rating)}{"☆".repeat(5 - card.star_rating)}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-slate-800">{card.title}</h3>
                <p className="text-xs text-slate-500 line-clamp-3">{card.summary || "无摘要"}</p>
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-slate-400">{new Date(card.created_at).toLocaleDateString()}</span>
                  <button onClick={(e) => { e.stopPropagation(); handleDelete(card.id); }}
                    className="text-xs text-slate-400 hover:text-red-500">删除</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
