export default function TaskPage() {
  return (
    <div className="flex gap-6 h-full">
      {/* 左侧日历 */}
      <div className="w-80 flex-shrink-0 space-y-4">
        <div className="glass-card p-5">
          <h3 className="text-lg font-semibold text-slate-700 mb-3">2026年6月</h3>
          <div className="grid grid-cols-7 gap-1 text-center text-xs">
            {["日","一","二","三","四","五","六"].map(d => (
              <div key={d} className="py-1 text-slate-400 font-medium">{d}</div>
            ))}
            {Array.from({length: 30}, (_, i) => (
              <button key={i} className={`py-2 rounded-lg hover:bg-primary-50 transition-colors ${i === 11 ? 'bg-primary-500 text-white' : 'text-slate-600'}`}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>

        {/* 统计 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="glass-card p-4 text-center">
            <p className="text-2xl font-bold text-amber-500">12</p>
            <p className="text-xs text-slate-400">总待办</p>
          </div>
          <div className="glass-card p-4 text-center">
            <p className="text-2xl font-bold text-emerald-500">8</p>
            <p className="text-xs text-slate-400">已完成</p>
          </div>
        </div>
      </div>

      {/* 右侧任务列表 */}
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-800">2026-06-12</h2>
          <button className="btn-gradient btn-click">添加任务</button>
        </div>

        <div className="space-y-3">
          <TaskCard content="完成文献综述初稿" priority="high" done={false} time="创建于 09:00" />
          <TaskCard content="阅读 PINN 论文" priority="normal" done={false} time="创建于 10:00" />
          <TaskCard content="整理试验数据" priority="normal" done={true} time="完成于 14:30" />
          <TaskCard content="准备组会 PPT" priority="urgent" done={false} time="创建于 08:00" />
        </div>
      </div>
    </div>
  );
}

function TaskCard({ content, priority, done, time }: { content: string; priority: string; done: boolean; time: string }) {
  const colors: Record<string, string> = {
    low: "border-slate-300", normal: "border-primary-400", high: "border-amber-400", urgent: "border-red-400"
  };
  return (
    <div className={`glass-card p-4 flex items-center gap-4 border-l-4 ${colors[priority] || colors.normal}`}>
      <button className={`w-7 h-7 rounded-full border-2 flex items-center justify-center transition-colors ${done ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 hover:border-emerald-400'}`}>
        {done && <span className="text-xs">✓</span>}
      </button>
      <span className={`flex-1 text-sm ${done ? 'text-slate-400 line-through' : 'text-slate-700'}`}>{content}</span>
      <span className="text-xs text-slate-400">{time}</span>
    </div>
  );
}
