export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">仪表盘</h2>

      {/* KPI 卡片 */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard title="今日任务" value="12" subtitle="完成 8/12" color="text-amber-500" />
        <StatCard title="文献总数" value="234" subtitle="本月新增 12" color="text-blue-500" />
        <StatCard title="进行中试验" value="3" subtitle="共 8 项" color="text-emerald-500" />
      </div>

      {/* 近期活动 */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">近期活动</h3>
        <div className="space-y-3">
          <ActivityItem time="14:30" text="完成: 阅读 PINN 论文" type="task" />
          <ActivityItem time="13:15" text="搜索: tailsitter flight control" type="search" />
          <ActivityItem time="10:00" text="试验: 风洞试验 v3 更新结果" type="experiment" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, color }: { title: string; value: string; subtitle: string; color: string }) {
  return (
    <div className="glass-card p-5">
      <p className="text-sm text-slate-500">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
      <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
    </div>
  );
}

function ActivityItem({ time, text, type }: { time: string; text: string; type: string }) {
  const icons: Record<string, string> = { task: "✓", search: "🔍", experiment: "🧪" };
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/40 transition-colors">
      <span className="text-lg">{icons[type] || "•"}</span>
      <span className="text-sm text-slate-700 flex-1">{text}</span>
      <span className="text-xs text-slate-400">{time}</span>
    </div>
  );
}
