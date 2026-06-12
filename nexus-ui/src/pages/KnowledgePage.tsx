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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">知识库</h2>
        <button className="btn-gradient btn-click" onClick={handleCreate}>新建卡片</button>
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
          <p className="text-slate-400">暂无知识卡片，点击"新建卡片"开始</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {cards.map(card => {
            const badge = SOURCE_BADGES[card.source_type] || SOURCE_BADGES.manual;
            return (
              <div key={card.id} className="glass-card p-5 space-y-3 cursor-pointer" onClick={() => alert(`详情: ${card.title}`)}>
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${badge.color}`}>{badge.text}</span>
                  <span className="text-amber-400 text-xs">
                    {"★".repeat(card.star_rating)}{"☆".repeat(5 - card.star_rating)}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-slate-800">{card.title}</h3>
                <p className="text-xs text-slate-500 line-clamp-2">{card.summary || "无摘要"}</p>
                <button onClick={e => { e.stopPropagation(); handleDelete(card.id); }}
                  className="text-xs text-slate-400 hover:text-red-500">删除</button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
