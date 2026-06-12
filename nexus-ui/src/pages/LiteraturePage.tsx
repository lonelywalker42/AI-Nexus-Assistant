import { useState } from "react";
import { searchApi, type Paper } from "../api/client";

const SOURCES = [
  { key: "openalex", label: "OpenAlex", default: true },
  { key: "arxiv", label: "arXiv", default: true },
  { key: "semantic_scholar", label: "Semantic Scholar", default: true },
  { key: "crossref", label: "CrossRef", default: false },
  { key: "pubmed", label: "PubMed", default: false },
  { key: "google_scholar", label: "Google Scholar", default: false },
  { key: "scopus", label: "Scopus", default: false },
];

export default function LiteraturePage() {
  const [tab, setTab] = useState<"search" | "review" | "topic" | "history">("search");
  const [keywords, setKeywords] = useState([""]);
  const [selectedSources, setSelectedSources] = useState(SOURCES.filter(s => s.default).map(s => s.key));
  const [results, setResults] = useState<Paper[]>([]);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState("");

  const handleSearch = async () => {
    const query = keywords.filter(k => k.trim()).join(" ");
    if (!query.trim()) return;
    setSearching(true);
    setStats("搜索中...");
    try {
      const res = await searchApi.search(query, selectedSources);
      setResults(res.papers);
      setStats(`找到 ${res.count} 篇文献`);
    } catch (err) {
      setStats(`搜索失败: ${err}`);
    }
    setSearching(false);
  };

  const toggleSource = (key: string) => {
    setSelectedSources(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">文献管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1 border-b border-slate-200">
        {(["search", "review", "topic", "history"] as const).map(t => {
          const labels = { search: "关键词检索", review: "AI 综述", topic: "选题讨论", history: "历史记录" };
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${
                tab === t ? "border-primary-500 text-primary-600" : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {labels[t]}
            </button>
          );
        })}
      </div>

      {/* 关键词检索 */}
      {tab === "search" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-4">
            <p className="text-sm font-semibold text-slate-700">关键词组（组内 AND，组间 OR）</p>
            {keywords.map((kw, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  className="input-glass flex-1"
                  placeholder={`关键词 ${i + 1}`}
                  value={kw}
                  onChange={e => {
                    const next = [...keywords];
                    next[i] = e.target.value;
                    setKeywords(next);
                  }}
                />
                {i < keywords.length - 1 && <span className="text-primary-500 font-bold text-sm">OR</span>}
                {keywords.length > 1 && (
                  <button onClick={() => setKeywords(keywords.filter((_, j) => j !== i))} className="text-slate-400 hover:text-red-500">✕</button>
                )}
              </div>
            ))}
            <button onClick={() => setKeywords([...keywords, ""])} className="text-sm text-primary-500 hover:underline">+ 添加关键词</button>

            <div className="flex gap-3 flex-wrap text-sm">
              {SOURCES.map(s => (
                <label key={s.key} className="flex items-center gap-1.5 cursor-pointer text-slate-600">
                  <input type="checkbox" checked={selectedSources.includes(s.key)} onChange={() => toggleSource(s.key)} className="rounded" />
                  {s.label}
                </label>
              ))}
            </div>

            <button className="btn-gradient btn-click" onClick={handleSearch} disabled={searching}>
              {searching ? "搜索中..." : "搜索"}
            </button>
            {stats && <p className="text-sm text-slate-500">{stats}</p>}
          </div>

          {/* 结果 */}
          <div className="space-y-3">
            {results.map((p, i) => (
              <div key={i} className="glass-card p-5 space-y-2">
                <div className="flex items-start gap-3">
                  <span className="text-sm font-bold text-primary-500">[{i + 1}]</span>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-slate-800">{p.title}</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      {p.authors?.slice(0, 3).join(", ")} | {p.year} | {p.journal}
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 text-[10px] font-medium">{p.source}</span>
                </div>
                {p.abstract && <p className="text-xs text-slate-500 line-clamp-2">{p.abstract.slice(0, 200)}</p>}
                <div className="flex gap-2">
                  <button className="text-xs text-slate-500 hover:text-primary-500">详情</button>
                  <button className="text-xs text-slate-500 hover:text-primary-500">引用</button>
                  <button className="text-xs text-slate-500 hover:text-primary-500">AI 总结</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "review" && (
        <div className="glass-card p-6">
          <p className="text-slate-500">请先搜索文献，然后在此生成 AI 综述。</p>
        </div>
      )}

      {tab === "topic" && (
        <div className="glass-card p-6">
          <p className="text-slate-500">输入研究方向，AI 将生成选题建议。</p>
        </div>
      )}

      {tab === "history" && (
        <div className="glass-card p-6">
          <p className="text-slate-500">搜索历史将在此显示。</p>
        </div>
      )}
    </div>
  );
}
