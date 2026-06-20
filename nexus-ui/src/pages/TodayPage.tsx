import { useState, useEffect, useRef } from "react";
import { tasksApi, dashboardApi, type Task, type DashboardData } from "../api/client";
import { IconPlus, IconCheck, IconSun, IconEdit, IconChevronRight } from "../components/Icons";
import { PRIORITIES, CATEGORIES, getPriority, getCategory, isOverdue } from "../constants/task";

export default function TodayPage({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const today = new Date().toISOString().split("T")[0];
  const [tasks, setTasks] = useState<Task[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [newTask, setNewTask] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [newCategory, setNewCategory] = useState("general");
  const [loading, setLoading] = useState(true);
  const [workLog, setWorkLog] = useState("");
  const [logSaved, setLogSaved] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [confirmDate, setConfirmDate] = useState<string | null>(null);
  const [confirmTaskId, setConfirmTaskId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const saved = localStorage.getItem(`nexus-worklog-${today}`);
    if (saved) setWorkLog(saved);
  }, [today]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [taskList, dash] = await Promise.all([
        tasksApi.list(today),
        dashboardApi.get(),
      ]);
      setTasks(taskList);
      setDashboard(dash);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleAddTask = async () => {
    if (!newTask.trim()) return;
    try {
      const task = await tasksApi.create({
        date: today,
        content: newTask.trim(),
        priority: newPriority,
        category: newCategory,
      });
      setTasks(prev => [...prev, task]);
      setNewTask("");
      inputRef.current?.focus();
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggle = async (id: string) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    // If completing (not undoing), show date confirmation dialog
    if (!task.completed) {
      setConfirmTaskId(id);
      setConfirmDate(today);
      return;
    }
    // Undo completion
    try {
      const updated = await tasksApi.toggle(id);
      setTasks(prev => prev.map(t => t.id === id ? updated : t));
    } catch (err) {
      console.error(err);
    }
  };

  const handleConfirmComplete = async () => {
    if (!confirmTaskId || !confirmDate) return;
    try {
      const task = tasks.find(t => t.id === confirmTaskId);
      const updated = await tasksApi.completeWithDate(confirmTaskId, confirmDate);
      setTasks(prev => prev.map(t => t.id === confirmTaskId ? { ...t, completed: true, completed_at: updated.completed_at } : t));
      // Task-to-worklog bridge
      if (task) {
        const cat = getCategory(task.category);
        const entry = `\n- [x] ${task.content} (${cat.label})`;
        setWorkLog(prev => prev ? prev + entry : `## 今日完成${entry}`);
      }
    } catch (err) {
      console.error(err);
    }
    setConfirmTaskId(null);
    setConfirmDate(null);
  };

  const handleDelete = async (id: string) => {
    try {
      await tasksApi.delete(id);
      setTasks(prev => prev.filter(t => t.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const handleEditTask = async (id: string) => {
    if (!editContent.trim()) return;
    try {
      await tasksApi.update(id, { content: editContent.trim() });
      setTasks(prev => prev.map(t => t.id === id ? { ...t, content: editContent.trim() } : t));
      setEditingId(null);
      setEditContent("");
    } catch (err) {
      console.error(err);
    }
  };

  const saveWorkLog = () => {
    localStorage.setItem(`nexus-worklog-${today}`, workLog);
    setLogSaved(true);
    setTimeout(() => setLogSaved(false), 2000);
  };

  const doneCount = tasks.filter(t => t.completed).length;
  const totalCount = tasks.length;
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;
  const incompleteTasks = tasks.filter(t => !t.completed);
  const completedTasks = tasks.filter(t => t.completed);

  const dateObj = new Date(today + "T00:00:00");
  const weekDays = ["日", "一", "二", "三", "四", "五", "六"];
  const dateStr = `${dateObj.getFullYear()}年${dateObj.getMonth() + 1}月${dateObj.getDate()}日 星期${weekDays[dateObj.getDay()]}`;

  const hour = now.getHours();
  const greeting = hour < 6 ? "夜深了" : hour < 12 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好";
  const timeStr = now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

  return (
    <div className="space-y-5">
      {/* 头部：问候 + 日期 + 时钟 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <IconSun size={22} style={{ color: "var(--accent-blue)" }} />
          <div>
            <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{greeting}</h2>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>{dateStr}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>{timeStr}</div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold" style={{ color: "var(--accent-blue)" }}>{progress}%</div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>今日进度</p>
          </div>
        </div>
      </div>

      {/* 进度条 */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
            已完成 {doneCount}/{totalCount} 项任务
          </span>
          <div className="flex-1" />
          {incompleteTasks.length > 0 && (
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              还有 {incompleteTasks.length} 项待完成
            </span>
          )}
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--border-color)" }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress}%`,
              background: progress === 100
                ? "linear-gradient(90deg, var(--accent-green), #34d399)"
                : "linear-gradient(90deg, var(--accent-blue), var(--accent-green))",
            }}
          />
        </div>
      </div>

      {/* 任务总览卡片 — 紧跟进度条下方 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="待完成" value={incompleteTasks.length} color="var(--accent-blue)" />
        <StatCard label="已完成" value={doneCount} color="var(--accent-green)" />
        <StatCard label="紧急/高优" value={tasks.filter(t => !t.completed && (t.priority === "urgent" || t.priority === "high")).length} color="#f59e0b" />
        <StatCard label="总任务" value={dashboard?.tasks.total ?? "—"} color="var(--text-primary)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 左侧：任务列表 */}
        <div className="lg:col-span-2 space-y-4">
          {/* 快速添加 */}
          <div className="glass-card p-4 space-y-2">
            <input
              ref={inputRef}
              className="input-glass flex-1 text-sm w-full py-2.5"
              placeholder="添加今日任务..."
                value={newTask}
                onChange={e => setNewTask(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") handleAddTask(); }}
            />
            <div className="flex gap-2 items-center">
              <select
                className="input-glass text-xs py-2 px-2"
                value={newPriority}
                onChange={e => setNewPriority(e.target.value)}
              >
                {PRIORITIES.map(p => (
                  <option key={p.key} value={p.key}>{p.label}</option>
                ))}
              </select>
              <select
                className="input-glass text-xs py-2 px-2"
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
              >
                {CATEGORIES.map(c => (
                  <option key={c.key} value={c.key}>{c.icon} {c.label}</option>
                ))}
              </select>
              <span className="flex-1" />
              <button
                className="btn-gradient btn-click text-xs py-2 px-3 flex items-center gap-1"
                onClick={handleAddTask}
              >
                <IconPlus size={13} /> 添加
              </button>
            </div>
          </div>

          {/* 未完成任务 */}
          {incompleteTasks.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider px-1" style={{ color: "var(--text-muted)" }}>
                待完成 · {incompleteTasks.length}
              </p>
              {incompleteTasks.map(task => (
                <TaskItem key={task.id} task={task} onToggle={handleToggle} onDelete={handleDelete} onStartEdit={(id, content) => { setEditingId(id); setEditContent(content); }} />
              ))}
            </div>
          )}

          {/* 已完成任务 */}
          {completedTasks.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wider px-1" style={{ color: "var(--text-muted)" }}>
                已完成 · {completedTasks.length}
              </p>
              {completedTasks.map(task => (
                <TaskItem key={task.id} task={task} onToggle={handleToggle} onDelete={handleDelete} onStartEdit={(id, content) => { setEditingId(id); setEditContent(content); }} />
              ))}
            </div>
          )}

          {/* 空状态 */}
          {tasks.length === 0 && !loading && (
            <div className="glass-card p-8 text-center">
              <IconCheck size={32} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
              <p className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>今天还没有任务</p>
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>在上方添加任务，或前往「任务与日程」安排日程</p>
            </div>
          )}

          {/* 逾期任务提醒 */}
          {(() => {
            const overdueTasks = tasks.filter(t => isOverdue(t.date, t.completed));
            if (overdueTasks.length === 0) return null;
            return (
              <div className="glass-card p-3 flex items-center gap-3" style={{ borderLeft: "3px solid #ef4444" }}>
                <span className="text-sm" style={{ color: "#ef4444" }}>⚠️</span>
                <div className="flex-1">
                  <p className="text-xs font-semibold" style={{ color: "#ef4444" }}>
                    {overdueTasks.length} 项任务已逾期
                  </p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                    {overdueTasks.slice(0, 3).map(t => t.content).join("、")}
                    {overdueTasks.length > 3 ? "..." : ""}
                  </p>
                </div>
              </div>
            );
          })()}

          {/* 内联编辑 */}
          {editingId && (
            <div className="glass-card p-3 space-y-2 animate-fade-in">
              <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>编辑任务</p>
              <div className="flex gap-2">
                <input className="input-glass flex-1 text-sm" value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") handleEditTask(editingId); if (e.key === "Escape") { setEditingId(null); setEditContent(""); } }}
                  autoFocus />
                <button className="btn-ghost text-xs" onClick={() => handleEditTask(editingId)}>保存</button>
                <button className="btn-ghost text-xs" onClick={() => { setEditingId(null); setEditContent(""); }}>取消</button>
              </div>
            </div>
          )}

          {/* 今日工作日志 */}
          <div className="glass-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <IconEdit size={15} style={{ color: "var(--accent-blue)" }} />
                <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>今日工作日志</span>
              </div>
              <div className="flex items-center gap-2">
                {logSaved && <span className="text-xs animate-fade-in" style={{ color: "var(--accent-green)" }}>已保存</span>}
                <button className="btn-ghost text-xs py-1" onClick={saveWorkLog}>保存</button>
              </div>
            </div>
            <textarea
              className="input-glass text-sm"
              rows={5}
              placeholder="记录今天的工作内容、遇到的问题、明日计划...&#10;&#10;提示：完成任务后会自动追加到日志中"
              value={workLog}
              onChange={e => setWorkLog(e.target.value)}
              onBlur={saveWorkLog}
              style={{ resize: "vertical", minHeight: "100px" }}
            />
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>日志保存在本地浏览器，按日期自动归档 · 完成任务自动追加</p>
          </div>
        </div>

        {/* 右侧：快捷入口 */}
        <div className="space-y-4">
          <div className="glass-card p-4 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>快捷入口</p>
            {[
              { id: "literature", label: "文献检索", desc: "搜索学术文献" },
              { id: "experiments", label: "试验管理", desc: "查看试验记录" },
              { id: "chat", label: "AI 对话", desc: "智能助手" },
              { id: "paper-library", label: "文献库", desc: "管理已入库文献" },
            ].map(item => (
              <button
                key={item.id}
                className="w-full flex items-center gap-3 p-2.5 rounded-xl cursor-pointer transition-all duration-150 text-left"
                style={{ color: "var(--text-secondary)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                onClick={() => onNavigate?.(item.id)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{item.label}</p>
                  <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>{item.desc}</p>
                </div>
                <IconChevronRight size={14} style={{ color: "var(--text-muted)" }} />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 完成日期确认对话框 */}
      {confirmTaskId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}
          onClick={() => { setConfirmTaskId(null); setConfirmDate(null); }}>
          <div className="glass-card p-5 space-y-3 max-w-sm animate-fade-in" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>确认完成日期</h3>
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              选择此任务的实际完成日期：
            </p>
            <input type="date" className="input-glass text-sm w-full" value={confirmDate || today}
              onChange={e => setConfirmDate(e.target.value)} />
            <div className="flex gap-2 justify-end">
              <button className="btn-ghost text-xs" onClick={() => { setConfirmTaskId(null); setConfirmDate(null); }}>取消</button>
              <button className="btn-gradient btn-click text-xs" onClick={handleConfirmComplete}>确认完成</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TaskItem({ task, onToggle, onDelete, onStartEdit }: {
  task: Task; onToggle: (id: string) => void; onDelete: (id: string) => void; onStartEdit: (id: string, content: string) => void
}) {
  const [hovered, setHovered] = useState(false);
  const pri = getPriority(task.priority);
  const cat = getCategory(task.category);
  const overdue = isOverdue(task.date, task.completed);

  return (
    <div
      className="glass-card flex items-center gap-3 px-4 py-3 cursor-pointer transition-all duration-150"
      style={{
        ...(task.completed ? { opacity: 0.6 } : {}),
        ...(overdue ? { borderLeft: `3px solid #ef4444` } : {}),
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onToggle(task.id)}
    >
      <div
        className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-200"
        style={task.completed
          ? { background: "var(--accent-green)", border: "2px solid var(--accent-green)" }
          : { border: `2px solid ${overdue ? "#ef4444" : "var(--border-color)"}` }
        }
      >
        {task.completed && <IconCheck size={12} style={{ color: "#fff" }} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm" style={{
          color: task.completed ? "var(--text-muted)" : overdue ? "#ef4444" : "var(--text-primary)",
          textDecoration: task.completed ? "line-through" : "none",
          fontWeight: overdue ? 600 : 400,
        }}>
          {task.content}
        </p>
        {overdue && !task.completed && (
          <p className="text-[10px] mt-0.5" style={{ color: "#ef4444" }}>已逾期</p>
        )}
      </div>
      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0" style={{ background: pri.bg, color: pri.color }}>{pri.shortLabel}</span>
      <span className="px-1.5 py-0.5 rounded text-[10px] flex-shrink-0" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{cat.icon} {cat.label}</span>
      {hovered && (
        <div className="flex gap-1 flex-shrink-0">
          <button className="text-xs cursor-pointer transition-colors" style={{ color: "var(--text-muted)" }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
            onClick={e => { e.stopPropagation(); onStartEdit(task.id, task.content); }}
          >✎</button>
          <button className="text-xs cursor-pointer transition-colors" style={{ color: "var(--text-muted)" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
            onClick={e => { e.stopPropagation(); onDelete(task.id); }}
          >✕</button>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="glass-card p-3 text-center">
      <div className="text-lg font-bold" style={{ color }}>{value}</div>
      <div className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>{label}</div>
    </div>
  );
}
