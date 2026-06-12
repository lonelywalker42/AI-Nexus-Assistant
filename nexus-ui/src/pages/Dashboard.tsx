import { useEffect, useState } from "react";
import { dashboardApi, type DashboardData } from "../api/client";

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    dashboardApi.get().then(setData).catch(console.error);
  }, []);

  const tasks = data?.tasks;
  const monthly = data?.monthly;
  const exps = data?.experiments;
  const kb = data?.knowledge;
  const rate = monthly && monthly.total > 0 ? Math.round((monthly.done / monthly.total) * 100) : 0;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">仪表盘</h2>

      <div className="grid grid-cols-3 gap-4">
        <StatCard title="今日任务" value={String(tasks?.total ?? 0)} subtitle={`完成 ${tasks?.done ?? 0}/${tasks?.total ?? 0}`} color="text-amber-500" />
        <StatCard title="月度完成率" value={`${rate}%`} subtitle={`${monthly?.done ?? 0}/${monthly?.total ?? 0} 本月`} color="text-emerald-500" />
        <StatCard title="进行中试验" value={String(exps?.running ?? 0)} subtitle={`共 ${exps?.total ?? 0} 项`} color="text-blue-500" />
        <StatCard title="知识卡片" value={String(kb?.total ?? 0)} subtitle={`${kb?.tag_count ?? 0} 个标签`} color="text-purple-500" />
        <StatCard title="规划中试验" value={String(exps?.planning ?? 0)} subtitle="待启动" color="text-slate-500" />
        <StatCard title="已完成试验" value={String(exps?.completed ?? 0)} subtitle="已归档" color="text-emerald-400" />
      </div>

      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">近期活动</h3>
        <div className="space-y-3">
          {data?.activities?.length ? data.activities.map((a, i) => (
            <ActivityItem key={i} time={a.time} text={a.text} type={a.type} />
          )) : <p className="text-sm text-slate-400">暂无近期活动</p>}
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
  const icons: Record<string, string> = { task: "✓", search: "🔍", experiment: "🧪", review: "📊", topic: "💡" };
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/40 transition-colors">
      <span className="text-lg">{icons[type] || "•"}</span>
      <span className="text-sm text-slate-700 flex-1">{text}</span>
      <span className="text-xs text-slate-400">{time}</span>
    </div>
  );
}
