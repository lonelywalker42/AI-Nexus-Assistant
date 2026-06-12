export default function LiteraturePage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">文献管理</h2>

      {/* 搜索栏 */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex gap-3">
          <input className="input-glass flex-1" placeholder="输入关键词..." />
          <button className="btn-gradient btn-click">搜索</button>
        </div>
        <div className="flex gap-4 text-sm">
          {["OpenAlex", "arXiv", "Semantic Scholar", "CrossRef", "PubMed"].map(s => (
            <label key={s} className="flex items-center gap-1.5 text-slate-600 cursor-pointer">
              <input type="checkbox" defaultChecked={["OpenAlex","arXiv","Semantic Scholar"].includes(s)} className="rounded" />
              {s}
            </label>
          ))}
        </div>
      </div>

      {/* 结果 */}
      <div className="space-y-3">
        <p className="text-sm text-slate-500">找到 23 篇文献</p>
        <PaperCard index={1} title="Physics-Informed Neural Networks for Flight Control" authors="Raissi et al." year={2019} journal="J. Comput. Physics" />
        <PaperCard index={2} title="Deep Learning for Aerodynamic Parameter Identification" authors="Wang et al." year={2023} journal="AIAA Journal" />
      </div>
    </div>
  );
}

function PaperCard({ index, title, authors, year, journal }: { index: number; title: string; authors: string; year: number; journal: string }) {
  return (
    <div className="glass-card p-5 space-y-2">
      <div className="flex items-start gap-3">
        <span className="text-sm font-bold text-primary-500">[{index}]</span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          <p className="text-xs text-slate-500 mt-1">{authors} | {year} | {journal}</p>
        </div>
        <span className="px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 text-[10px] font-medium">arXiv</span>
      </div>
      <div className="flex gap-2 mt-2">
        <button className="text-xs text-slate-500 hover:text-primary-500 transition-colors">详情</button>
        <button className="text-xs text-slate-500 hover:text-primary-500 transition-colors">引用</button>
        <button className="text-xs text-slate-500 hover:text-primary-500 transition-colors">AI 总结</button>
      </div>
    </div>
  );
}
