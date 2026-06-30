import { useState, useEffect, useRef } from "react";
import { tasksApi, dashboardApi, chatApi, modelsApi, type Task, type DashboardData } from "../api/client";
import { IconPlus, IconCheck, IconSun, IconEdit, IconChevronRight, IconLightbulb, IconWarning, IconClipboard, IconChart, IconSparkle } from "../components/Icons";
import { PRIORITIES, CATEGORIES, getPriority, getCategory, isOverdue } from "../constants/task";

/* ── 结构化工作笔记数据模型 (5.1.1) ── */
interface StructuredWorkNote {
  rawInput: string;
  completed: string[];
  issues: string[];
  plans: string[];
  timestamp: string;
}

/* ── 活跃度热力图组件 (5.1.3) ── */
function ActivityHeatmap({ taskDates }: { taskDates: Map<string, number> }) {
  const today = new Date();
  const weeks: { date: Date; count: number }[][] = [];
  let currentWeek: { date: Date; count: number }[] = [];

  // 生成过去 20 周的数据
  for (let i = 139; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const count = taskDates.get(key) || 0;
    currentWeek.push({ date: d, count });
    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }
  if (currentWeek.length > 0) weeks.push(currentWeek);

  const getColor = (count: number) => {
    if (count === 0) return "var(--border-color)";
    if (count <= 2) return "#DCFCE7";
    if (count <= 4) return "#BBF7D0";
    if (count <= 6) return "#86EFAC";
    return "#4ADE80";
  };

  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  return (
    <div className="relative">
      <div className="flex gap-[3px]">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day, di) => (
              <div
                key={di}
                className="rounded-[2px] cursor-pointer transition-transform hover:scale-110"
                style={{
                  width: 13, height: 13,
                  background: getColor(day.count),
                  animationDelay: `${(wi * 7 + di) * 4}ms`,
                }}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({
                    x: rect.left + rect.width / 2,
                    y: rect.top - 8,
                    text: `${day.date.toLocaleDateString("zh-CN")} · ${day.count} 项完成`,
                  });
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            ))}
          </div>
        ))}
      </div>
      {tooltip && (
        <div className="fixed z-[999] px-2 py-1 rounded text-[10px] font-medium pointer-events-none"
          style={{
            left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)",
            background: "var(--text-primary)", color: "var(--glass-bg)",
            boxShadow: "0 4px 30px rgba(0,0,0,0.015)",
          }}>
          {tooltip.text}
        </div>
      )}
      <div className="flex items-center gap-1 mt-2">
        <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>少</span>
        {[0, 2, 4, 6, 8].map(c => (
          <div key={c} className="rounded-[2px]" style={{ width: 11, height: 11, background: getColor(c) }} />
        ))}
        <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>多</span>
      </div>
    </div>
  );
}

/* ── 结构化概览卡片 (5.1.4) ── */
function StructuredOverview({ note }: { note: StructuredWorkNote | null }) {
  if (!note || (note.completed.length === 0 && note.issues.length === 0 && note.plans.length === 0)) {
    return null;
  }

  const sections = [
    { iconName: "check", label: "完成事项", items: note.completed, color: "var(--accent-green)" },
    { iconName: "warning", label: "问题记录", items: note.issues, color: "#f59e0b" },
    { iconName: "clipboard", label: "明日计划", items: note.plans, color: "var(--accent-blue)" },
  ];

  const SECTION_ICONS: Record<string, React.ComponentType<any>> = {
    check: IconCheck, warning: IconWarning, clipboard: IconClipboard,
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {sections.map(s => (
        <div key={s.label} className="glass-card p-3 space-y-1.5">
          <p className="text-xs font-semibold flex items-center gap-1" style={{ color: s.color }}>{(() => { const Icon = SECTION_ICONS[s.iconName]; return Icon ? <Icon size={12} /> : null; })()} {s.label}</p>
          {s.items.length > 0 ? (
            <ul className="space-y-1">
              {s.items.map((item, i) => (
                <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: "var(--text-secondary)" }}>
                  <span style={{ color: s.color, flexShrink: 0 }}>·</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>暂无</p>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── 周报摘要 (5.1.2) ── */
function WeeklyReport({ dailyNotes }: { dailyNotes: Map<string, StructuredWorkNote> }) {
  const today = new Date();
  const dayOfWeek = today.getDay() === 0 ? 6 : today.getDay() - 1; // 0=周一
  const weekNotes: StructuredWorkNote[] = [];

  for (let i = 0; i <= dayOfWeek; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const note = dailyNotes.get(key);
    if (note) weekNotes.push(note);
  }

  if (weekNotes.length === 0) return null;

  const allCompleted = weekNotes.flatMap(n => n.completed);
  const allIssues = weekNotes.flatMap(n => n.issues);
  const reportDays = weekNotes.length;

  return (
    <div className="glass-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold flex items-center gap-1" style={{ color: "var(--text-primary)" }}><IconChart size={12} /> 本周周报摘要</p>
        <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>
          {reportDays} 天有记录
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] font-medium" style={{ color: "var(--accent-green)" }}>本周完成 ({allCompleted.length})</p>
          <ul className="mt-0.5">
            {allCompleted.slice(0, 4).map((item, i) => (
              <li key={i} className="text-[10px] truncate" style={{ color: "var(--text-secondary)" }} title={item}>· {item}</li>
            ))}
            {allCompleted.length > 4 && <li className="text-[10px]" style={{ color: "var(--text-muted)" }}>...还有 {allCompleted.length - 4} 项</li>}
          </ul>
        </div>
        <div>
          <p className="text-[10px] font-medium" style={{ color: "#f59e0b" }}>遗留问题 ({allIssues.length})</p>
          <ul className="mt-0.5">
            {allIssues.slice(0, 3).map((item, i) => (
              <li key={i} className="text-[10px] truncate" style={{ color: "var(--text-secondary)" }} title={item}>· {item}</li>
            ))}
            {allIssues.length > 3 && <li className="text-[10px]" style={{ color: "var(--text-muted)" }}>...还有 {allIssues.length - 3} 项</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function TodayPage({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const today = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; })();
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

  // AI 结构化日报 (5.1.1)
  const [rawInput, setRawInput] = useState("");
  const [isStructuring, setIsStructuring] = useState(false);
  const [structuredNote, setStructuredNote] = useState<StructuredWorkNote | null>(null);
  const [allDailyNotes, setAllDailyNotes] = useState<Map<string, StructuredWorkNote>>(new Map());

  // 活跃度数据
  const [taskDates, setTaskDates] = useState<Map<string, number>>(new Map());

  useEffect(() => {
    const saved = localStorage.getItem(`nexus-worklog-${today}`);
    if (saved) setWorkLog(saved);
    // 加载今日结构化笔记
    const noteSaved = localStorage.getItem(`nexus-structured-note-${today}`);
    if (noteSaved) {
      try { setStructuredNote(JSON.parse(noteSaved)); } catch {}
    }
    // 加载原始输入
    const rawSaved = localStorage.getItem(`nexus-raw-input-${today}`);
    if (rawSaved) setRawInput(rawSaved);
    // 加载所有日报（用于周报）
    loadAllDailyNotes();
    // 加载任务完成日期数据（用于热力图）
    loadTaskDateStats();
  }, [today]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const loadAllDailyNotes = () => {
    const notes = new Map<string, StructuredWorkNote>();
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith("nexus-structured-note-")) {
        const date = key.replace("nexus-structured-note-", "");
        try {
          const note = JSON.parse(localStorage.getItem(key) || "");
          if (note && note.completed) notes.set(date, note);
        } catch {}
      }
    }
    setAllDailyNotes(notes);
  };

  const loadTaskDateStats = () => {
    // 从已完成任务中统计每天完成数
    tasksApi.list("").then(allTasks => {
      const dates = new Map<string, number>();
      allTasks.filter(t => t.completed && t.completed_at).forEach(t => {
        const d = t.completed_at!.split("T")[0];
        dates.set(d, (dates.get(d) || 0) + 1);
      });
      setTaskDates(dates);
    }).catch(() => {});
  };

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

  // AI 结构化日报处理 (5.1.1)
  const handleAiStructure = async () => {
    if (!rawInput.trim()) return;
    setIsStructuring(true);

    const prompt = `请将以下工作日志整理为结构化内容，严格按 JSON 格式返回（不要返回其他内容）：
{
  "completed": ["完成事项1", "完成事项2"],
  "issues": ["问题1", "问题2"],
  "plans": ["计划1", "计划2"]
}

如果某个分类没有内容，返回空数组。从文本中提取关键信息，保持简洁。

工作日志：
${rawInput}`;

    try {
      const models = await modelsApi.list();
      const modelId = models[0]?.id;
      const session = await chatApi.createSession("日报整理");
      await chatApi.addMessage(session.id, prompt);

      let fullContent = "";
      for await (const chunk of chatApi.stream(session.id, modelId)) {
        if (chunk.type === "content") fullContent += chunk.data;
      }

      // 提取 JSON
      const jsonMatch = fullContent.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        const note: StructuredWorkNote = {
          rawInput,
          completed: parsed.completed || [],
          issues: parsed.issues || [],
          plans: parsed.plans || [],
          timestamp: new Date().toISOString(),
        };
        setStructuredNote(note);
        localStorage.setItem(`nexus-structured-note-${today}`, JSON.stringify(note));
        loadAllDailyNotes();
      }
    } catch (err) {
      console.error("AI 整理失败:", err);
    }
    setIsStructuring(false);
  };

  const handleRawInputChange = (v: string) => {
    setRawInput(v);
    localStorage.setItem(`nexus-raw-input-${today}`, v);
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
    if (!task.completed) {
      setConfirmTaskId(id);
      setConfirmDate(today);
      return;
    }
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
            <div className="text-2xl font-bold tabular-nums" style={{ color: "var(--text-primary)", fontFeatureSettings: "'tnum' on" }}>{timeStr}</div>
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

      {/* 任务总览卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="待完成" value={incompleteTasks.length} color="var(--accent-blue)" />
        <StatCard label="已完成" value={doneCount} color="var(--accent-green)" />
        <StatCard label="紧急/高优" value={tasks.filter(t => !t.completed && (t.priority === "urgent" || t.priority === "high")).length} color="#f59e0b" />
        <StatCard label="总任务" value={dashboard?.tasks.total ?? "—"} color="var(--text-primary)" />
      </div>

      {/* 结构化概览卡片 (5.1.4) */}
      <StructuredOverview note={structuredNote} />

      {/* 周报摘要 (5.1.2) */}
      <WeeklyReport dailyNotes={allDailyNotes} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 左侧：任务列表 */}
        <div className="lg:col-span-2 space-y-4">
          {/* AI 快速想法输入 (5.1.1) */}
          <div className="glass-card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <IconLightbulb size={15} style={{ color: "#f59e0b" }} />
              <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>快速想法</span>
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>AI 自动整理为结构化日报</span>
            </div>
            <textarea
              className="input-glass text-sm"
              rows={3}
              placeholder="随意记录今天的工作内容，例如：今天完成了文献检索功能的前端对接，遇到了 WebSocket 超时的问题，明天计划修复并加入自动重连..."
              value={rawInput}
              onChange={e => handleRawInputChange(e.target.value)}
              style={{ resize: "vertical", minHeight: "72px" }}
            />
            <div className="flex items-center justify-between">
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                {structuredNote ? `上次整理: ${new Date(structuredNote.timestamp).toLocaleTimeString("zh-CN")}` : "输入后点击 AI 整理，自动生成结构化日报"}
              </p>
              <div className="flex gap-2">
                {structuredNote && (
                  <button className="btn-ghost text-xs py-1.5"
                    onClick={() => { setStructuredNote(null); localStorage.removeItem(`nexus-structured-note-${today}`); }}>
                    清除
                  </button>
                )}
                <button className="btn-gradient btn-click text-xs py-1.5 whitespace-nowrap"
                  onClick={handleAiStructure}
                  disabled={isStructuring || !rawInput.trim()}>
                  {isStructuring ? "整理中..." : <span className="flex items-center gap-1"><IconSparkle size={12} /> AI 整理</span>}
                </button>
              </div>
            </div>
          </div>

          {/* 快速添加任务 */}
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
              <select className="input-glass text-xs py-2 px-2" value={newPriority} onChange={e => setNewPriority(e.target.value)}>
                {PRIORITIES.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
              </select>
              <select className="input-glass text-xs py-2 px-2" value={newCategory} onChange={e => setNewCategory(e.target.value)}>
                {CATEGORIES.map(c => <option key={c.key} value={c.key}>{c.icon} {c.label}</option>)}
              </select>
              <span className="flex-1" />
              <button className="btn-gradient btn-click text-xs py-1.5 whitespace-nowrap" onClick={handleAddTask}>
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

        {/* 右侧：快捷入口 + 热力图 */}
        <div className="space-y-4">
          {/* 活跃度热力图 (5.1.3) */}
          <div className="glass-card p-4 space-y-3">
            <p className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>活跃度</p>
            <ActivityHeatmap taskDates={taskDates} />
          </div>

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
              <button className="btn-primary btn-click text-xs" onClick={handleConfirmComplete}>确认完成</button>
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
          <button className="btn-icon" style={{ width: 24, height: 24, fontSize: 12 }}
            onClick={e => { e.stopPropagation(); onStartEdit(task.id, task.content); }}>✎</button>
          <button className="btn-icon" style={{ width: 24, height: 24, fontSize: 12, color: "#ef4444" }}
            onClick={e => { e.stopPropagation(); onDelete(task.id); }}>✕</button>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div className="glass-card p-3 text-center">
      <div className="text-lg font-bold" style={{ color, fontFeatureSettings: "'tnum' on" }}>{value}</div>
      <div className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>{label}</div>
    </div>
  );
}
