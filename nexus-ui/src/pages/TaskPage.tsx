import { useEffect, useState } from "react";
import { tasksApi, type Task } from "../api/client";
import { getPriority, isOverdue } from "../constants/task";


export default function TaskPage() {
  const today = new Date().toISOString().split("T")[0];
  const [selectedDate, setSelectedDate] = useState(today);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [mainTasks, setMainTasks] = useState<Task[]>([]);
  const [incompleteTasks, setIncompleteTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState("");
  const [priority, setPriority] = useState("normal");
  const [category, setCategory] = useState("general");
  const [marks, setMarks] = useState<Record<string, string>>({});
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);
  const [weekTasksCache, setWeekTasksCache] = useState<Record<string, { id: string; content: string; completed: boolean; priority: string; category: string }[]>>({});

  const loadTasks = () => tasksApi.list(selectedDate).then(setTasks).catch(console.error);
  const loadMainTasks = () => tasksApi.listMain().then(setMainTasks).catch(console.error);
  const loadIncompleteTasks = () => tasksApi.listIncomplete().then(setIncompleteTasks).catch(console.error);
  const loadMarks = () => {
    const d = new Date(selectedDate);
    tasksApi.dates(d.getFullYear(), d.getMonth() + 1).then(setMarks).catch(console.error);
  };

  useEffect(() => { loadTasks(); }, [selectedDate]);
  useEffect(() => { loadMainTasks(); loadIncompleteTasks(); }, []);
  useEffect(() => { loadMarks(); }, [selectedDate]);

  // Load week tasks for hover preview
  useEffect(() => {
    const d = new Date(selectedDate);
    const monday = new Date(d);
    monday.setDate(d.getDate() - d.getDay() + 1);
    const start = monday.toISOString().split("T")[0];
    tasksApi.weekTasks(start).then(setWeekTasksCache).catch(() => {});
  }, [selectedDate]);

  const handleDateHover = (ds: string) => {
    setHoveredDate(ds);
  };

  const handleAdd = async () => {
    if (!newTask.trim()) return;
    await tasksApi.create({ date: selectedDate, content: newTask.trim(), priority, category });
    setNewTask("");
    loadTasks();
    loadMarks();
    if (category === "main") loadMainTasks();
    loadIncompleteTasks();
  };

  const handleToggle = async (id: string) => {
    await tasksApi.toggle(id);
    loadTasks();
    loadMarks();
    loadMainTasks();
    loadIncompleteTasks();
  };

  const handleDelete = async (id: string) => {
    await tasksApi.delete(id);
    loadTasks();
    loadMarks();
    loadMainTasks();
    loadIncompleteTasks();
  };

  // 生成日历
  const d = new Date(selectedDate);
  const year = d.getFullYear();
  const month = d.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDay = new Date(year, month, 1).getDay();
  const monthName = `${year}年${month + 1}月`;

  const done = tasks.filter(t => t.completed).length;

  // 右侧显示：主线置顶 + 当日任务（去重主线） + 其他未完成任务（去重当日）
  const todayTaskIds = new Set(tasks.map(t => t.id));
  const mainTaskIds = new Set(mainTasks.map(t => t.id));
  // 当日非主线任务
  const todayOtherTasks = tasks.filter(t => !mainTaskIds.has(t.id));
  // 其他未完成任务（非当日、非主线）
  const otherIncomplete = incompleteTasks.filter(t => !todayTaskIds.has(t.id) && !mainTaskIds.has(t.id));
  // 合并：主线置顶 → 当日其他 → 其他未完成
  const displayTasks = [...mainTasks, ...todayOtherTasks, ...otherIncomplete];

  // 左侧主线任务（未完成）
  const incompleteMain = mainTasks.filter(t => !t.completed);

  return (
    <div className="flex gap-5 h-full">
      {/* 左侧日历 */}
      <div className="w-72 flex-shrink-0 space-y-3">
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-3">
            <button onClick={() => {
              const prev = new Date(year, month - 1, 1);
              setSelectedDate(prev.toISOString().split("T")[0]);
            }} className="w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-colors"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >‹</button>
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{monthName}</h3>
            <button onClick={() => {
              const next = new Date(year, month + 1, 1);
              setSelectedDate(next.toISOString().split("T")[0]);
            }} className="w-7 h-7 rounded-lg flex items-center justify-center text-sm transition-colors"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >›</button>
          </div>
          <div className="grid grid-cols-7 gap-0.5 text-center text-[11px]">
            {["日","一","二","三","四","五","六"].map(d => (
              <div key={d} className="py-1 font-medium" style={{ color: "var(--text-muted)" }}>{d}</div>
            ))}
            {Array.from({ length: firstDay }, (_, i) => <div key={`e${i}`} />)}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const mark = marks[ds];
              const isSelected = ds === selectedDate;
              const isToday = ds === today;
              const isHovered = ds === hoveredDate;
              const dayTasks = weekTasksCache[ds] || [];
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(ds)}
                  className="py-1.5 rounded-lg transition-colors relative text-xs"
                  style={isSelected
                    ? { background: "var(--accent-blue)", color: "#fff", fontWeight: 600 }
                    : isToday
                      ? { background: "var(--hover-bg)", color: "var(--accent-blue)", fontWeight: 600 }
                      : { color: "var(--text-primary)" }
                  }
                  onMouseEnter={e => {
                    if (!isSelected) e.currentTarget.style.background = "var(--hover-bg)";
                    handleDateHover(ds);
                  }}
                  onMouseLeave={e => {
                    if (!isSelected && !isToday) e.currentTarget.style.background = "transparent";
                    setHoveredDate(null);
                  }}
                >
                  {day}
                  {mark && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full"
                      style={{ background: mark === "pending" ? "#fbbf24" : "#10b981" }} />
                  )}
                  {/* Hover tooltip */}
                  {isHovered && dayTasks.length > 0 && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-20 pointer-events-none">
                      <div className="glass-card p-2 min-w-[120px] max-w-[180px] text-left shadow-lg animate-fade-in">
                        <p className="text-[10px] font-semibold mb-1" style={{ color: "var(--text-muted)" }}>
                          {ds} · {dayTasks.length} 项
                        </p>
                        {dayTasks.slice(0, 4).map(t => (
                          <p key={t.id} className="text-[10px] truncate" style={{
                            color: t.completed ? "var(--text-muted)" : "var(--text-primary)",
                            textDecoration: t.completed ? "line-through" : "none",
                          }}>
                            {t.completed ? "✓" : "○"} {t.content}
                          </p>
                        ))}
                        {dayTasks.length > 4 && (
                          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>+{dayTasks.length - 4} 更多</p>
                        )}
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* 统计 */}
        <div className="grid grid-cols-2 gap-2">
          <div className="glass-card p-3 text-center">
            <p className="text-xl font-bold" style={{ color: "#f59e0b" }}>{tasks.length}</p>
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>当日待办</p>
          </div>
          <div className="glass-card p-3 text-center">
            <p className="text-xl font-bold" style={{ color: "#10b981" }}>{done}</p>
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>已完成</p>
          </div>
        </div>

        {/* 主线任务 */}
        {incompleteMain.length > 0 && (
          <div className="glass-card p-3">
            <p className="text-[11px] font-semibold mb-2 flex items-center gap-1.5" style={{ color: "#8b5cf6" }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#8b5cf6" }} />
              主线任务
            </p>
            <div className="space-y-1.5">
              {incompleteMain.map(t => (
                <div key={t.id} className="flex items-start gap-2 px-2 py-1.5 rounded-lg text-xs cursor-pointer transition-colors"
                  style={{ color: "var(--text-primary)" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  onClick={() => handleToggle(t.id)}
                >
                  <span className="w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ borderColor: "#8b5cf6" }} />
                  <span className="flex-1 break-words whitespace-pre-wrap leading-relaxed">{t.content}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => setSelectedDate(today)}
          className="w-full py-2 rounded-xl text-xs font-medium transition-colors"
          style={{ border: "1px solid var(--accent-blue)", color: "var(--accent-blue)" }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(59,130,246,0.08)")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
        >
          跳转今日
        </button>
      </div>

      {/* 右侧任务列表 */}
      <div className="flex-1 space-y-4 min-w-0">
        <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{selectedDate === today ? "今日待办" : selectedDate}</h2>

        {/* 输入区域 - Issue 2: 重新排列，更大 */}
        <div className="glass-card p-4 space-y-3">
          <input
            className="input-glass"
            placeholder="添加新的待办事项..."
            value={newTask}
            onChange={e => setNewTask(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAdd()}
          />
          <div className="flex gap-3">
            <select className="input-glass flex-1" value={priority} onChange={e => setPriority(e.target.value)}>
              <option value="normal">普通优先级</option>
              <option value="low">低优先级</option>
              <option value="high">高优先级</option>
              <option value="urgent">紧急</option>
            </select>
            <select className="input-glass flex-1" value={category} onChange={e => setCategory(e.target.value)}>
              <option value="general">普通任务</option>
              <option value="main">主线任务</option>
              <option value="literature">文献相关</option>
              <option value="experiment">试验相关</option>
            </select>
            <button className="btn-gradient btn-click flex-shrink-0 px-6" onClick={handleAdd}>添加</button>
          </div>
        </div>

        {/* 任务列表 */}
        <div className="space-y-2">
          {displayTasks.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>暂无待办事项</p>
            </div>
          ) : displayTasks.map(task => {
            const isMain = (task as any).category === "main";
            const isToday = task.date === today;
            const showDate = !isToday && !task.completed;
            return (
              <div key={task.id} className="glass-card px-4 py-3 flex items-start gap-3"
                style={{ borderLeft: `3px solid ${isMain ? "#8b5cf6" : getPriority(task.priority).border}`, ...(isOverdue(task.date, task.completed) ? { background: "rgba(239,68,68,0.04)" } : {}) }}
              >
                <button
                  onClick={() => handleToggle(task.id)}
                  className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors mt-0.5 cursor-pointer"
                  style={task.completed
                    ? { background: "#10b981", borderColor: "#10b981", color: "#fff" }
                    : { borderColor: "var(--border-color)" }
                  }
                >
                  {task.completed && <span className="text-[10px]">✓</span>}
                </button>
                <span className="flex-1 text-sm min-w-0 break-words whitespace-pre-wrap" style={{ color: task.completed ? "var(--text-muted)" : "var(--text-primary)", textDecoration: task.completed ? "line-through" : "none" }}>
                  {isMain && <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mr-1.5"
                    style={{ background: "rgba(139,92,246,0.1)", color: "#8b5cf6" }}>主线</span>}
                  {task.content}
                </span>
                {showDate && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded flex-shrink-0"
                    style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>
                    {task.date}
                  </span>
                )}
                <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                  {task.completed_at ? new Date(task.completed_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) :
                   task.created_at ? new Date(task.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : ""}
                </span>
                <button onClick={() => handleDelete(task.id)} className="text-xs flex-shrink-0 transition-colors"
                  style={{ color: "var(--text-muted)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                >✕</button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
