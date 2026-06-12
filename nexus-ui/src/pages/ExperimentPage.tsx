import { useEffect, useState } from "react";
import { experimentsApi, type Experiment } from "../api/client";

const STATUS_COLORS: Record<string, string> = {
  planning: "bg-blue-500", running: "bg-amber-500",
  completed: "bg-emerald-500", suspended: "bg-slate-400",
};
const STATUS_LABELS: Record<string, string> = {
  planning: "规划中", running: "进行中", completed: "已完成", suspended: "已暂停",
};

export default function ExperimentPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const loadExperiments = () => experimentsApi.list(search).then(setExperiments).catch(console.error);
  useEffect(() => { loadExperiments(); }, [search]);

  const active = experiments.find(e => e.id === activeId);

  const handleCreate = async () => {
    const title = prompt("试验名称:");
    if (!title) return;
    const res = await experimentsApi.create({ title });
    await loadExperiments();
    setActiveId(res.id);
  };

  const handleDelete = async () => {
    if (!activeId) return;
    if (!confirm("确定删除此试验？")) return;
    await experimentsApi.delete(activeId);
    setActiveId(null);
    loadExperiments();
  };

  return (
    <div className="flex gap-6 h-full">
      {/* 左侧列表 */}
      <div className="w-72 flex-shrink-0 space-y-3">
        <input className="input-glass" placeholder="搜索试验..." value={search} onChange={e => setSearch(e.target.value)} />
        <div className="space-y-2 overflow-y-auto flex-1">
          {experiments.map(exp => (
            <div
              key={exp.id}
              onClick={() => setActiveId(exp.id)}
              className={`glass-card p-3 flex items-center gap-3 cursor-pointer transition-all ${
                activeId === exp.id ? "ring-2 ring-primary-400" : ""
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[exp.status] || "bg-slate-300"}`} />
              <span className="text-sm text-slate-700 truncate">{exp.title}</span>
            </div>
          ))}
        </div>
        <button className="btn-gradient btn-click w-full" onClick={handleCreate}>新建试验</button>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 space-y-4">
        {active ? (
          <>
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-800">{active.title}</h2>
                <div className="flex gap-2">
                  <span className={`px-3 py-1 rounded-full text-white text-xs font-medium ${STATUS_COLORS[active.status]}`}>
                    {STATUS_LABELS[active.status] || active.status}
                  </span>
                  <button onClick={handleDelete} className="text-xs text-red-400 hover:text-red-600">删除</button>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><p className="text-slate-400">背景</p><p className="text-slate-700 mt-1">{active.background || "未填写"}</p></div>
                <div><p className="text-slate-400">目标</p><p className="text-slate-700 mt-1">{active.objective || "未填写"}</p></div>
                <div><p className="text-slate-400">设置</p><p className="text-slate-700 mt-1">{active.setup || "未填写"}</p></div>
              </div>
            </div>

            {/* 试验结果 */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-slate-700 mb-4">试验结果 ({active.results.length})</h3>
              <div className="space-y-3">
                {active.results.map(r => (
                  <div key={r.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-primary-500">v{r.version}</span>
                      <span className="text-sm text-slate-700">{r.description}</span>
                      <span className="text-xs text-slate-400 ml-auto">{new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                    {r.conclusion && <p className="text-xs text-slate-500">结论: {r.conclusion}</p>}
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="glass-card p-12 text-center">
            <p className="text-slate-400">选择或新建一个试验</p>
          </div>
        )}
      </div>
    </div>
  );
}
