import { useState, useEffect, useRef } from "react";
import { tasksApi, dashboardApi, type Task, type DashboardData } from "../api/client";
import { IconPlus, IconCheck, IconSun, IconEdit, IconChevronRight } from "../components/Icons";

const PRIORITY_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  urgent: { bg: "rgba(239,68,68,0.12)", text: "#ef4444", label: "紧急" },
  high: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b", label: "高" },
  normal: { bg: "rgba(59,130,246,0.08)", text: "var(--text-secondary)", label: "普通" },
  low: { bg: "rgba(148,163,184,0.1)", text: "var(--text-muted)", label: "低" },
};

const CATEGORY_LABELS: Record<string, string> = {
  general: "日常",
  main: "核心",
  literature: "文献",
  experiment: "试验",
};

export default function TodayPage({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const today = new Date().toISOString().split("T")[0];
  const [tasks, setTasks] = useState<Task[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [newTask, setNewTask] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [loading, setLoading] = useState(true);
  const [workLog, setWorkLog] = useState("");
  const [logSaved, setLogSaved] = useState(false);
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
        category: "general",
      });
      setTasks(prev => [...prev, task]);
      setNewTask("");
      inputRef.current?.focus();
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await tasksApi.toggle(id);
      setTasks(prev => prev.map(t => t.id === id ? updated : t));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await tasksApi.delete(id);
      setTasks(prev => prev.filter(t => t.id !== id));
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
          <div className="glass-card p-4">
            <div className="flex gap-2 items-center">
              <input
                ref={inputRef}
                className="input-glass flex-1 text-sm"
                placeholder="添加今日任务..."
                value={newTask}
                onChange={e => setNewTask(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") handleAddTask(); }}
              />
              <select
                className="input-glass text-xs py-2 px-2"
                value={newPriority}
                onChange={e => setNewPriority(e.target.value)}
              >
                {Object.entries(PRIORITY_COLORS).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
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
                <TaskItem key={task.id} task={task} onToggle={handleToggle} onDelete={handleDelete} />
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
                <TaskItem key={task.id} task={task} onToggle={handleToggle} onDelete={handleDelete} />
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
              placeholder="记录今天的工作内容、遇到的问题、明日计划..."
              value={workLog}
              onChange={e => setWorkLog(e.target.value)}
              style={{ resize: "vertical", minHeight: "100px" }}
            />
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>日志保存在本地浏览器，按日期自动归档</p>
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
    </div>
  );
}

function TaskItem({ task, onToggle, onDelete }: { task: Task; onToggle: (id: string) => void; onDelete: (id: string) => void }) {
  const [hovered, setHovered] = useState(false);
  const pri = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.normal;
  const cat = CATEGORY_LABELS[task.category] || task.category;

  return (
    <div
      className="glass-card flex items-center gap-3 px-4 py-3 cursor-pointer transition-all duration-150"
      style={task.completed ? { opacity: 0.6 } : {}}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onToggle(task.id)}
    >
      <div
        className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-200"
        style={task.completed
          ? { background: "var(--accent-green)", border: "2px solid var(--accent-green)" }
          : { border: "2px solid var(--border-color)" }
        }
      >
        {task.completed && <IconCheck size={12} style={{ color: "#fff" }} />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm" style={{
          color: task.completed ? "var(--text-muted)" : "var(--text-primary)",
          textDecoration: task.completed ? "line-through" : "none",
        }}>
          {task.content}
        </p>
      </div>
      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0" style={{ background: pri.bg, color: pri.text }}>{pri.label}</span>
      <span className="px-1.5 py-0.5 rounded text-[10px] flex-shrink-0" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{cat}</span>
      {hovered && (
        <button className="text-xs flex-shrink-0 cursor-pointer transition-colors" style={{ color: "var(--text-muted)" }}
          onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
          onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
          onClick={e => { e.stopPropagation(); onDelete(task.id); }}
        >✕</button>
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
