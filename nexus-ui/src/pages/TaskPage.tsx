import { useEffect, useState } from "react";
import { tasksApi, type Task } from "../api/client";

const PRIORITY_COLORS: Record<string, string> = {
  low: "border-slate-300", normal: "border-primary-400",
  high: "border-amber-400", urgent: "border-red-400",
};

export default function TaskPage() {
  const today = new Date().toISOString().split("T")[0];
  const [selectedDate, setSelectedDate] = useState(today);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState("");
  const [priority, setPriority] = useState("normal");
  const [category, setCategory] = useState("general");
  const [marks, setMarks] = useState<Record<string, string>>({});

  const loadTasks = () => tasksApi.list(selectedDate).then(setTasks).catch(console.error);
  const loadMarks = () => {
    const d = new Date(selectedDate);
    tasksApi.dates(d.getFullYear(), d.getMonth() + 1).then(setMarks).catch(console.error);
  };

  useEffect(() => { loadTasks(); }, [selectedDate]);
  useEffect(() => { loadMarks(); }, [selectedDate]);

  const handleAdd = async () => {
    if (!newTask.trim()) return;
    await tasksApi.create({ date: selectedDate, content: newTask.trim(), priority, category });
    setNewTask("");
    loadTasks();
    loadMarks();
  };

  const handleToggle = async (id: string) => {
    await tasksApi.toggle(id);
    loadTasks();
    loadMarks();
  };

  const handleDelete = async (id: string) => {
    await tasksApi.delete(id);
    loadTasks();
    loadMarks();
  };

  // 生成日历
  const d = new Date(selectedDate);
  const year = d.getFullYear();
  const month = d.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDay = new Date(year, month, 1).getDay();
  const monthName = `${year}年${month + 1}月`;

  const done = tasks.filter(t => t.completed).length;

  return (
    <div className="flex gap-6 h-full">
      {/* 左侧日历 */}
      <div className="w-80 flex-shrink-0 space-y-4">
        <div className="glass-card p-5">
          <h3 className="text-lg font-semibold text-slate-700 mb-3">{monthName}</h3>
          <div className="grid grid-cols-7 gap-1 text-center text-xs">
            {["日","一","二","三","四","五","六"].map(d => (
              <div key={d} className="py-1 text-slate-400 font-medium">{d}</div>
            ))}
            {Array.from({ length: firstDay }, (_, i) => <div key={`e${i}`} />)}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const ds = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const mark = marks[ds];
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(ds)}
                  className={`py-2 rounded-lg transition-colors relative ${
                    ds === selectedDate ? "bg-primary-500 text-white" : "text-slate-600 hover:bg-primary-50"
                  }`}
                >
                  {day}
                  {mark && (
                    <span className={`absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full ${
                      mark === "pending" ? "bg-amber-400" : "bg-emerald-400"
                    }`} />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="glass-card p-4 text-center">
            <p className="text-2xl font-bold text-amber-500">{tasks.length}</p>
            <p className="text-xs text-slate-400">总待办</p>
          </div>
          <div className="glass-card p-4 text-center">
            <p className="text-2xl font-bold text-emerald-500">{done}</p>
            <p className="text-xs text-slate-400">已完成</p>
          </div>
        </div>

        <button
          onClick={() => setSelectedDate(today)}
          className="w-full py-2 rounded-xl border border-primary-400 text-primary-600 text-sm font-medium hover:bg-primary-50 transition-colors"
        >
          跳转今日
        </button>
      </div>

      {/* 右侧任务列表 */}
      <div className="flex-1 space-y-4">
        <h2 className="text-xl font-bold text-slate-800">{selectedDate}</h2>

        <div className="flex gap-3">
          <input
            className="input-glass flex-1"
            placeholder="添加新的待办事项..."
            value={newTask}
            onChange={e => setNewTask(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAdd()}
          />
          <select className="input-glass w-24" value={priority} onChange={e => setPriority(e.target.value)}>
            <option value="normal">普通</option>
            <option value="low">低</option>
            <option value="high">高</option>
            <option value="urgent">紧急</option>
          </select>
          <select className="input-glass w-24" value={category} onChange={e => setCategory(e.target.value)}>
            <option value="general">普通</option>
            <option value="main">主线</option>
            <option value="literature">文献</option>
            <option value="experiment">试验</option>
          </select>
          <button className="btn-gradient btn-click" onClick={handleAdd}>添加</button>
        </div>

        <div className="space-y-3">
          {tasks.length === 0 ? (
            <p className="text-center text-slate-400 py-8">暂无待办事项</p>
          ) : (() => {
            // 主线任务置顶
            const mainTasks = tasks.filter(t => (t as any).category === "main");
            const otherTasks = tasks.filter(t => (t as any).category !== "main");
            const sorted = [...mainTasks, ...otherTasks];
            return sorted.map(task => {
              const isMain = (task as any).category === "main";
              return (
            <div key={task.id} className={`glass-card p-4 flex items-center gap-4 border-l-4 ${
              isMain ? "border-purple-500 ring-1 ring-purple-200" : (PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.normal)
            }`}>
              <button
                onClick={() => handleToggle(task.id)}
                className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-colors ${
                  task.completed ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-300 hover:border-emerald-400"
                }`}
              >
                {task.completed && <span className="text-xs">✓</span>}
              </button>
              <span className={`flex-1 text-sm ${task.completed ? "text-slate-400 line-through" : "text-slate-700"}`}>
                {isMain && <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-600 mr-2">主线</span>}
                {task.content}
              </span>
              <span className="text-xs text-slate-400">
                {task.completed_at ? `完成于 ${new Date(task.completed_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}` :
                 task.created_at ? `创建于 ${new Date(task.created_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}` : ""}
              </span>
              <button onClick={() => handleDelete(task.id)} className="text-slate-400 hover:text-red-500 text-xs">✕</button>
            </div>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
}
