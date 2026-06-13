import { useEffect, useState } from "react";
import { experimentsApi, type Experiment } from "../api/client";

const STATUS_COLORS: Record<string, string> = {
  planning: "#3b82f6", running: "#f59e0b",
  completed: "#10b981", suspended: "#94a3b8",
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
    <div className="flex gap-5 h-full">
      {/* 左侧列表 */}
      <div className="w-64 flex-shrink-0 space-y-3">
        <input className="input-glass" placeholder="搜索试验..." value={search} onChange={e => setSearch(e.target.value)} />
        <div className="space-y-1.5 overflow-y-auto flex-1">
          {experiments.map(exp => (
            <div
              key={exp.id}
              onClick={() => setActiveId(exp.id)}
              className="glass-card px-3 py-2.5 flex items-center gap-3 cursor-pointer transition-all"
              style={activeId === exp.id
                ? { borderLeft: "3px solid var(--accent-blue)" }
                : {}
              }
            >
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: STATUS_COLORS[exp.status] || "#94a3b8" }} />
              <span className="text-sm truncate" style={{ color: "var(--text-primary)" }}>{exp.title}</span>
            </div>
          ))}
        </div>
        <button className="btn-gradient btn-click w-full" onClick={handleCreate}>新建试验</button>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 space-y-4">
        {active ? (
          <>
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{active.title}</h2>
                <div className="flex gap-2 items-center">
                  <span className="px-3 py-1 rounded-full text-white text-xs font-medium"
                    style={{ background: STATUS_COLORS[active.status] }}>
                    {STATUS_LABELS[active.status] || active.status}
                  </span>
                  <button onClick={handleDelete} className="text-xs transition-colors"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                  >删除</button>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>背景</p>
                  <p className="mt-1" style={{ color: "var(--text-secondary)" }}>{active.background || "未填写"}</p>
                </div>
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>目标</p>
                  <p className="mt-1" style={{ color: "var(--text-secondary)" }}>{active.objective || "未填写"}</p>
                </div>
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>设置</p>
                  <p className="mt-1" style={{ color: "var(--text-secondary)" }}>{active.setup || "未填写"}</p>
                </div>
              </div>
            </div>

            {/* 试验结果 */}
            <div className="glass-card p-5">
              <h3 className="text-base font-semibold mb-3" style={{ color: "var(--text-primary)" }}>试验结果 ({active.results.length})</h3>
              <div className="space-y-2">
                {active.results.map(r => (
                  <div key={r.id} className="p-3 rounded-xl space-y-1.5"
                    style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold" style={{ color: "var(--accent-blue)" }}>v{r.version}</span>
                      <span className="text-sm" style={{ color: "var(--text-primary)" }}>{r.description}</span>
                      <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>{new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                    {r.conclusion && <p className="text-xs" style={{ color: "var(--text-secondary)" }}>结论: {r.conclusion}</p>}
                  </div>
                ))}
                {active.results.length === 0 && (
                  <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>暂无结果</p>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="glass-card p-12 text-center">
            <p style={{ color: "var(--text-muted)" }}>选择或新建一个试验</p>
          </div>
        )}
      </div>
    </div>
  );
}
