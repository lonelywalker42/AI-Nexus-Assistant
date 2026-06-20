import { useEffect, useState } from "react";
import { experimentsApi, type Experiment, type ExperimentResult } from "../api/client";

const STATUS_COLORS: Record<string, string> = {
  planning: "#3b82f6", running: "#f59e0b",
  completed: "#10b981", suspended: "#94a3b8",
};
const STATUS_LABELS: Record<string, string> = {
  planning: "规划中", running: "进行中", completed: "已完成", suspended: "已暂停",
};
const STATUS_LIST = ["planning", "running", "completed", "suspended"] as const;

export default function ExperimentPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // 编辑模式
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: "", background: "", objective: "", setup: "", status: "" });

  // 结果表单
  const [showResultForm, setShowResultForm] = useState(false);
  const [resultForm, setResultForm] = useState({ description: "", parameters: "{}", result_data: "", conclusion: "" });
  const [editingResultId, setEditingResultId] = useState<string | null>(null);

  // 参数表格
  const [showParamTable, setShowParamTable] = useState(false);
  const [paramTable, setParamTable] = useState<{ param_keys: string[]; rows: Array<{ result_id: string; version: number; description: string; params: Record<string, unknown>; result_data: string; conclusion: string }> } | null>(null);

  // 项目信息
  const [showProjectInfo, setShowProjectInfo] = useState(false);
  const [projectForm, setProjectForm] = useState({ local_path: "", repo_url: "", readme_content: "" });

  // AI 分析
  const [analyzing, setAnalyzing] = useState(false);

  // Git 状态
  const [gitStatus, setGitStatus] = useState<{ has_git: boolean; branch?: string; commit_short?: string;
    commit_message?: string; commit_date?: string; dirty_files?: number } | null>(null);
  const [snapshotting, setSnapshotting] = useState(false);

  // 结构化参数编辑
  const [paramEntries, setParamEntries] = useState<{ key: string; value: string }[]>([{ key: "", value: "" }]);

  const loadExperiments = () => experimentsApi.list(search, statusFilter).then(setExperiments).catch(console.error);
  useEffect(() => { loadExperiments(); }, [search, statusFilter]);

  const active = experiments.find(e => e.id === activeId);

  // 同步编辑表单
  useEffect(() => {
    if (active) {
      setEditForm({
        title: active.title,
        background: active.background,
        objective: active.objective,
        setup: active.setup,
        status: active.status,
      });
      setProjectForm({
        local_path: active.local_path || "",
        repo_url: active.repo_url || "",
        readme_content: active.readme_content || "",
      });
    }
    setEditing(false);
    setShowResultForm(false);
    setShowParamTable(false);
    setShowProjectInfo(false);
    setGitStatus(null);
    // Load Git status
    if (activeId) {
      experimentsApi.gitStatus(activeId).then(s => {
        if (s.has_git) setGitStatus(s as any);
      }).catch(() => {});
    }
  }, [activeId]);

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

  const handleSaveEdit = async () => {
    if (!activeId) return;
    await experimentsApi.update(activeId, editForm);
    setEditing(false);
    loadExperiments();
  };

  const handleStatusChange = async (status: string) => {
    if (!activeId) return;
    await experimentsApi.update(activeId, { status });
    loadExperiments();
  };

  // 结果操作
  const handleAddResult = async () => {
    if (!activeId) return;
    // Convert paramEntries to JSON if available
    let params = {};
    const validEntries = paramEntries.filter(e => e.key.trim());
    if (validEntries.length > 0 && resultForm.parameters === "{}") {
      params = Object.fromEntries(validEntries.map(e => [e.key.trim(), e.value]));
    } else {
      try { params = JSON.parse(resultForm.parameters); } catch { alert("参数格式错误（需为 JSON）"); return; }
    }
    if (editingResultId) {
      await experimentsApi.updateResult(editingResultId, {
        description: resultForm.description,
        parameters: params,
        result_data: resultForm.result_data,
        conclusion: resultForm.conclusion,
      });
    } else {
      await experimentsApi.addResult(activeId, {
        description: resultForm.description,
        parameters: params,
        result_data: resultForm.result_data,
        conclusion: resultForm.conclusion,
      });
    }
    setShowResultForm(false);
    setEditingResultId(null);
    setResultForm({ description: "", parameters: "{}", result_data: "", conclusion: "" });
    loadExperiments();
  };

  const handleEditResult = (r: ExperimentResult) => {
    setEditingResultId(r.id);
    setResultForm({
      description: r.description,
      parameters: JSON.stringify(r.parameters, null, 2),
      result_data: r.result_data,
      conclusion: r.conclusion,
    });
    setShowResultForm(true);
  };

  const handleDeleteResult = async (resultId: string) => {
    if (!confirm("确定删除此结果？")) return;
    await experimentsApi.deleteResult(resultId);
    loadExperiments();
  };

  const handleSnapshot = async (resultId: string) => {
    if (!activeId) return;
    setSnapshotting(true);
    try {
      const res = await experimentsApi.gitSnapshot(activeId, resultId);
      if (res.error) {
        alert("快照失败: " + res.error);
      } else {
        loadExperiments();
      }
    } catch (err) {
      alert("快照失败: " + err);
    }
    setSnapshotting(false);
  };

  // 参数表格
  const loadParamTable = async () => {
    if (!activeId) return;
    try {
      const data = await experimentsApi.paramsTable(activeId);
      setParamTable(data);
      setShowParamTable(true);
    } catch (err) { alert("加载失败: " + err); }
  };

  // AI 分析
  const handleAiAnalysis = async () => {
    if (!activeId) return;
    setAnalyzing(true);
    try {
      const res = await experimentsApi.aiAnalysis(activeId);
      // 更新本地状态
      setExperiments(prev => prev.map(e => e.id === activeId ? { ...e, ai_analysis: res.analysis } : e));
    } catch (err) { alert("分析失败: " + err); }
    setAnalyzing(false);
  };

  // 项目信息保存
  const handleSaveProject = async () => {
    if (!activeId) return;
    await experimentsApi.update(activeId, projectForm);
    setShowProjectInfo(false);
    loadExperiments();
  };

  // 打开本地目录
  const handleOpenPath = async (path: string) => {
    try {
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(path);
    } catch {
      alert("无法打开目录（仅 Tauri 环境支持）");
    }
  };

  return (
    <div className="flex gap-5 h-full">
      {/* 左侧列表 */}
      <div className="w-64 flex-shrink-0 space-y-3">
        <input className="input-glass" placeholder="搜索试验..." value={search} onChange={e => setSearch(e.target.value)} />
        <div className="flex gap-1 flex-wrap">
          <button className={`text-xs px-2 py-1 rounded-lg cursor-pointer ${!statusFilter ? "font-bold" : ""}`}
            style={{ background: !statusFilter ? "var(--accent-blue)" : "var(--hover-bg)", color: !statusFilter ? "#fff" : "var(--text-secondary)" }}
            onClick={() => setStatusFilter("")}>全部</button>
          {STATUS_LIST.map(s => (
            <button key={s} className="text-xs px-2 py-1 rounded-lg cursor-pointer"
              style={{ background: statusFilter === s ? STATUS_COLORS[s] : "var(--hover-bg)", color: statusFilter === s ? "#fff" : "var(--text-secondary)" }}
              onClick={() => setStatusFilter(s === statusFilter ? "" : s)}>
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
        <div className="space-y-1.5 overflow-y-auto flex-1">
          {experiments.map(exp => (
            <div key={exp.id} onClick={() => setActiveId(exp.id)}
              className="glass-card px-3 py-2.5 flex items-center gap-3 cursor-pointer transition-all"
              style={activeId === exp.id ? { borderLeft: "3px solid var(--accent-blue)" } : {}}>
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: STATUS_COLORS[exp.status] || "#94a3b8" }} />
              <span className="text-sm truncate" style={{ color: "var(--text-primary)" }}>{exp.title}</span>
            </div>
          ))}
        </div>
        <button className="btn-gradient btn-click w-full" onClick={handleCreate}>新建试验</button>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        {active ? (
          <>
            {/* 头部 */}
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                {editing ? (
                  <input className="input-glass flex-1 mr-3" value={editForm.title}
                    onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))} />
                ) : (
                  <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{active.title}</h2>
                )}
                <div className="flex gap-2 items-center">
                  {/* 状态切换 */}
                  <select className="input-glass text-xs" value={editing ? editForm.status : active.status}
                    onChange={e => editing ? setEditForm(f => ({ ...f, status: e.target.value })) : handleStatusChange(e.target.value)}>
                    {STATUS_LIST.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
                  </select>
                  {editing ? (
                    <div className="flex gap-1">
                      <button className="btn-ghost text-xs" onClick={handleSaveEdit}>保存</button>
                      <button className="btn-ghost text-xs" onClick={() => setEditing(false)}>取消</button>
                    </div>
                  ) : (
                    <button className="btn-ghost text-xs" onClick={() => setEditing(true)}>编辑</button>
                  )}
                  <button onClick={handleDelete} className="text-xs transition-colors"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                  >删除</button>
                </div>
              </div>

              {/* 背景/目标/设置 */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                {(["background", "objective", "setup"] as const).map(field => {
                  const labels = { background: "背景", objective: "目标", setup: "设置" };
                  return (
                    <div key={field}>
                      <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{labels[field]}</p>
                      {editing ? (
                        <textarea className="input-glass mt-1" rows={3} value={editForm[field]}
                          onChange={e => setEditForm(f => ({ ...f, [field]: e.target.value }))} />
                      ) : (
                        <p className="mt-1" style={{ color: "var(--text-secondary)" }}>{active[field] || "未填写"}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 项目信息 */}
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>项目信息</h3>
                <div className="flex gap-2">
                  <button className="btn-ghost text-xs" onClick={() => setShowProjectInfo(!showProjectInfo)}>
                    {showProjectInfo ? "收起" : "编辑"}
                  </button>
                </div>
              </div>

              {showProjectInfo ? (
                <div className="space-y-3">
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>本地目录</label>
                    <input className="input-glass mt-1" placeholder="/path/to/project"
                      value={projectForm.local_path} onChange={e => setProjectForm(f => ({ ...f, local_path: e.target.value }))} />
                  </div>
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>GitHub 仓库</label>
                    <input className="input-glass mt-1" placeholder="https://github.com/user/repo"
                      value={projectForm.repo_url} onChange={e => setProjectForm(f => ({ ...f, repo_url: e.target.value }))} />
                  </div>
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>README.md</label>
                    <textarea className="input-glass mt-1 font-mono text-xs" rows={6} placeholder="# Project Name..."
                      value={projectForm.readme_content} onChange={e => setProjectForm(f => ({ ...f, readme_content: e.target.value }))} />
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-ghost text-xs" onClick={handleSaveProject}>保存</button>
                    <button className="btn-ghost text-xs" onClick={() => setShowProjectInfo(false)}>取消</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {active.local_path ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>本地:</span>
                      <span className="text-xs font-mono" style={{ color: "var(--text-secondary)" }}>{active.local_path}</span>
                      <button className="btn-ghost text-xs" onClick={() => handleOpenPath(active.local_path)}>打开</button>
                    </div>
                  ) : null}
                  {active.repo_url ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>仓库:</span>
                      <a href={active.repo_url} target="_blank" rel="noopener" className="text-xs" style={{ color: "var(--accent-blue)" }}>{active.repo_url}</a>
                    </div>
                  ) : null}
                  {!active.local_path && !active.repo_url && (
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>未配置项目信息</p>
                  )}
                </div>
              )}

              {/* Git 状态 */}
              {gitStatus && (
                <div className="flex items-center gap-3 pt-2 mt-2" style={{ borderTop: "1px solid var(--border-color)" }}>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-mono"
                    style={{ background: "rgba(16,185,129,0.1)", color: "#10b981" }}>
                    {gitStatus.branch}
                  </span>
                  {gitStatus.commit_short && (
                    <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
                      {gitStatus.commit_short} — {gitStatus.commit_message}
                    </span>
                  )}
                  {(gitStatus.dirty_files ?? 0) > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b" }}>
                      {gitStatus.dirty_files} 未提交
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* 试验结果 */}
            <div className="glass-card p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>试验结果 ({active.results.length})</h3>
                <div className="flex gap-2">
                  <button className="btn-ghost text-xs" onClick={loadParamTable} disabled={active.results.length === 0}>
                    参数对比
                  </button>
                  <button className="btn-gradient btn-click text-xs" onClick={() => {
                    setEditingResultId(null);
                    setResultForm({ description: "", parameters: "{}", result_data: "", conclusion: "" });
                    setShowResultForm(true);
                  }}>
                    添加结果
                  </button>
                </div>
              </div>

              {/* 结果表单 */}
              {showResultForm && (
                <div className="p-4 rounded-xl mb-3 space-y-3" style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
                  <h4 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    {editingResultId ? "编辑结果" : "添加结果"}
                  </h4>
                  <input className="input-glass" placeholder="描述" value={resultForm.description}
                    onChange={e => setResultForm(f => ({ ...f, description: e.target.value }))} />
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>参数</label>
                    {/* 结构化参数编辑器 */}
                    <div className="mt-1 space-y-1.5">
                      {paramEntries.map((entry, i) => (
                        <div key={i} className="flex gap-1.5 items-center">
                          <input className="input-glass flex-1 text-xs py-1" placeholder="参数名"
                            value={entry.key}
                            onChange={e => {
                              const next = [...paramEntries];
                              next[i] = { ...next[i], key: e.target.value };
                              setParamEntries(next);
                            }} />
                          <input className="input-glass flex-1 text-xs py-1" placeholder="值"
                            value={entry.value}
                            onChange={e => {
                              const next = [...paramEntries];
                              next[i] = { ...next[i], value: e.target.value };
                              setParamEntries(next);
                            }} />
                          {paramEntries.length > 1 && (
                            <button className="text-[10px] cursor-pointer" style={{ color: "var(--text-muted)" }}
                              onClick={() => setParamEntries(paramEntries.filter((_, j) => j !== i))}>✕</button>
                          )}
                        </div>
                      ))}
                      <button className="text-[10px] cursor-pointer" style={{ color: "var(--accent-blue)" }}
                        onClick={() => setParamEntries([...paramEntries, { key: "", value: "" }])}>
                        + 添加参数
                      </button>
                    </div>
                    {/* JSON 预览 */}
                    <details className="mt-1">
                      <summary className="text-[10px] cursor-pointer" style={{ color: "var(--text-muted)" }}>JSON 预览</summary>
                      <textarea className="input-glass mt-1 font-mono text-xs" rows={2}
                        placeholder='{"learning_rate": 0.001}'
                        value={resultForm.parameters}
                        onChange={e => setResultForm(f => ({ ...f, parameters: e.target.value }))} />
                    </details>
                  </div>
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>结果数据</label>
                    <textarea className="input-glass mt-1" rows={3} placeholder="试验结果数据..."
                      value={resultForm.result_data}
                      onChange={e => setResultForm(f => ({ ...f, result_data: e.target.value }))} />
                  </div>
                  <div>
                    <label className="text-xs" style={{ color: "var(--text-muted)" }}>结论</label>
                    <textarea className="input-glass mt-1" rows={2} placeholder="试验结论..."
                      value={resultForm.conclusion}
                      onChange={e => setResultForm(f => ({ ...f, conclusion: e.target.value }))} />
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-ghost text-xs" onClick={handleAddResult}>
                      {editingResultId ? "保存修改" : "添加"}
                    </button>
                    <button className="btn-ghost text-xs" onClick={() => { setShowResultForm(false); setEditingResultId(null); }}>取消</button>
                  </div>
                </div>
              )}

              {/* 结果列表 */}
              <div className="space-y-2">
                {active.results.map(r => (
                  <div key={r.id} className="p-3 rounded-xl space-y-1.5"
                    style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold" style={{ color: "var(--accent-blue)" }}>v{r.version}</span>
                      <span className="text-sm flex-1" style={{ color: "var(--text-primary)" }}>{r.description}</span>
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>{new Date(r.created_at).toLocaleDateString()}</span>
                      {/* Git 快照 */}
                      {gitStatus?.has_git && (
                        <button className="text-[10px] px-1.5 py-0.5 rounded transition-colors cursor-pointer"
                          style={{ background: "rgba(16,185,129,0.08)", color: "#10b981" }}
                          onClick={() => handleSnapshot(r.id)}
                          disabled={snapshotting}
                          title="关联当前Git commit">
                          {snapshotting ? "..." : "快照"}
                        </button>
                      )}
                      <button className="text-xs transition-colors" style={{ color: "var(--text-muted)" }}
                        onClick={() => handleEditResult(r)}
                        onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
                        onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                      >编辑</button>
                      <button className="text-xs transition-colors" style={{ color: "var(--text-muted)" }}
                        onClick={() => handleDeleteResult(r.id)}
                        onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                        onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                      >删除</button>
                    </div>
                    {Object.keys(r.parameters).length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(r.parameters).map(([k, v]) => (
                          <span key={k} className="text-[10px] px-1.5 py-0.5 rounded"
                            style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                    {r.result_data && <p className="text-xs" style={{ color: "var(--text-secondary)" }}>数据: {r.result_data.slice(0, 200)}</p>}
                    {r.conclusion && <p className="text-xs" style={{ color: "var(--text-secondary)" }}>结论: {r.conclusion}</p>}
                    {/* Git 快照信息 */}
                    {(() => {
                      const snippets = (r as any).code_snippets;
                      if (!snippets) return null;
                      try {
                        const parsed = typeof snippets === 'string' ? JSON.parse(snippets) : snippets;
                        const snapshot = parsed.find((s: any) => s.type === 'git_snapshot');
                        if (!snapshot) return null;
                        return (
                          <div className="flex items-center gap-2 pt-1 mt-1" style={{ borderTop: "1px solid var(--border-color)" }}>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                              style={{ background: "rgba(16,185,129,0.08)", color: "#10b981" }}>
                              {snapshot.commit_short}
                            </span>
                            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{snapshot.commit_message}</span>
                          </div>
                        );
                      } catch { return null; }
                    })()}
                  </div>
                ))}
                {active.results.length === 0 && (
                  <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>暂无结果</p>
                )}
              </div>
            </div>

            {/* 参数对比表格 */}
            {showParamTable && paramTable && (
              <div className="glass-card p-5 overflow-x-auto">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>参数对比</h3>
                  <button className="btn-ghost text-xs" onClick={() => setShowParamTable(false)}>关闭</button>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-color)" }}>
                      <th className="text-left p-2" style={{ color: "var(--text-muted)" }}>版本</th>
                      {paramTable.param_keys.map(k => (
                        <th key={k} className="text-left p-2" style={{ color: "var(--text-muted)" }}>{k}</th>
                      ))}
                      <th className="text-left p-2" style={{ color: "var(--text-muted)" }}>结论</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paramTable.rows.map(row => (
                      <tr key={row.result_id} style={{ borderBottom: "1px solid var(--border-color)" }}>
                        <td className="p-2 font-bold" style={{ color: "var(--accent-blue)" }}>v{row.version}</td>
                        {paramTable.param_keys.map(k => (
                          <td key={k} className="p-2" style={{ color: "var(--text-secondary)" }}>
                            {row.params[k] !== undefined ? String(row.params[k]) : "—"}
                          </td>
                        ))}
                        <td className="p-2" style={{ color: "var(--text-secondary)" }}>{row.conclusion || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* AI 分析 */}
            <div className="glass-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>AI 分析</h3>
                <button className="btn-gradient btn-click text-xs" onClick={handleAiAnalysis}
                  disabled={analyzing || active.results.length === 0}>
                  {analyzing ? "分析中..." : "生成分析"}
                </button>
              </div>
              {active.ai_analysis ? (
                <div className="text-sm markdown-body" style={{ color: "var(--text-secondary)" }}
                  dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(active.ai_analysis) }} />
              ) : (
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>暂无分析（需先添加试验结果）</p>
              )}
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
