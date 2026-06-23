import { useEffect, useState } from "react";
import { dashboardApi, type DashboardData } from "../api/client";
import { IconCheck, IconSearch, IconFlask, IconChart, IconLightning } from "../components/Icons";

interface DashboardProps {
  onNavigate?: (page: string) => void;
}

// 活动类型到页面的映射
const ACTIVITY_PAGE_MAP: Record<string, string> = {
  task: "tasks",
  search: "literature",
  experiment: "experiments",
  review: "literature",
  topic: "literature",
};

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    dashboardApi.get().then(setData).catch(console.error);
  }, []);

  const tasks = data?.tasks;
  const monthly = data?.monthly;
  const exps = data?.experiments;
  const kb = data?.knowledge;
  const rate = monthly && monthly.total > 0 ? Math.round((monthly.done / monthly.total) * 100) : 0;

  // 模拟最近 7 天任务完成数据（实际应从 API 获取）
  const weeklyData = [3, 5, 2, 7, 4, 6, 3];
  const maxVal = Math.max(...weeklyData, 1);
  const weekDays = ["一", "二", "三", "四", "五", "六", "日"];

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>仪表盘</h2>

      <div className="grid grid-cols-3 gap-3">
        <StatCard title="今日任务" value={String(tasks?.total ?? 0)} subtitle={`完成 ${tasks?.done ?? 0}/${tasks?.total ?? 0}`} color="#f59e0b" onClick={() => onNavigate?.("tasks")} />
        <StatCard title="月度完成率" value={`${rate}%`} subtitle={`${monthly?.done ?? 0}/${monthly?.total ?? 0} 本月`} color="#10b981" onClick={() => onNavigate?.("tasks")} />
        <StatCard title="进行中试验" value={String(exps?.running ?? 0)} subtitle={`共 ${exps?.total ?? 0} 项`} color="#3b82f6" onClick={() => onNavigate?.("experiments")} />
        <StatCard title="知识卡片" value={String(kb?.total ?? 0)} subtitle={`${kb?.tag_count ?? 0} 个标签`} color="#8b5cf6" onClick={() => onNavigate?.("knowledge")} />
        <StatCard title="规划中试验" value={String(exps?.planning ?? 0)} subtitle="待启动" color="#64748b" onClick={() => onNavigate?.("experiments")} />
        <StatCard title="已完成试验" value={String(exps?.completed ?? 0)} subtitle="已归档" color="#34d399" onClick={() => onNavigate?.("experiments")} />
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 任务完成趋势 */}
        <div className="glass-card p-4">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>本周任务完成趋势</h3>
          <div className="flex items-end gap-2 h-24">
            {weeklyData.map((val, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t transition-all"
                  style={{
                    height: `${(val / maxVal) * 100}%`,
                    background: `linear-gradient(to top, var(--accent-blue), rgba(59,130,246,0.5))`,
                    minHeight: "4px",
                  }}
                />
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>周{weekDays[i]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 实验状态分布 */}
        <div className="glass-card p-4">
          <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>实验状态分布</h3>
          <div className="flex items-center gap-4 h-24">
            <div className="flex-1 flex items-end gap-1 h-full">
              {[
                { label: "规划", value: exps?.planning ?? 0, color: "#64748b" },
                { label: "进行", value: exps?.running ?? 0, color: "#3b82f6" },
                { label: "完成", value: exps?.completed ?? 0, color: "#10b981" },
              ].map((item, i) => {
                const total = (exps?.total ?? 1) || 1;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div className="text-[10px] font-medium" style={{ color: item.color }}>{item.value}</div>
                    <div
                      className="w-full rounded-t"
                      style={{
                        height: `${(item.value / total) * 100}%`,
                        background: item.color,
                        minHeight: "4px",
                      }}
                    />
                    <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{item.label}</span>
                  </div>
                );
              })}
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{exps?.total ?? 0}</div>
              <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>总计</div>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>近期活动</h3>
        <div className="space-y-1">
          {data?.activities?.length ? data.activities.map((a, i) => {
            const targetPage = ACTIVITY_PAGE_MAP[a.type] || "dashboard";
            return (
              <ActivityItem
                key={i}
                time={a.time}
                text={a.text}
                type={a.type}
                onClick={() => onNavigate?.(targetPage)}
              />
            );
          }) : <p className="text-sm" style={{ color: "var(--text-muted)" }}>暂无近期活动</p>}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, color, onClick }: { title: string; value: string; subtitle: string; color: string; onClick?: () => void }) {
  return (
    <div
      className={`glass-card p-4 ${onClick ? "cursor-pointer glass-card-hover" : ""}`}
      onClick={onClick}
    >
      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{title}</p>
      <p className="text-2xl font-bold mt-1" style={{ color }}>{value}</p>
      <p className="text-[11px] mt-0.5" style={{ color: "var(--text-muted)" }}>{subtitle}</p>
    </div>
  );
}

const ACTIVITY_ICONS: Record<string, React.FC<{ size?: number }>> = {
  task: IconCheck, search: IconSearch, experiment: IconFlask, review: IconChart, topic: IconLightning,
};

function ActivityItem({ time, text, type, onClick }: { time: string; text: string; type: string; onClick?: () => void }) {
  const Icon = ACTIVITY_ICONS[type] || IconLightning;
  return (
    <div
      className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors cursor-pointer"
      style={{ color: "var(--text-primary)" }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      onClick={onClick}
    >
      <span className="w-5 h-5 flex items-center justify-center flex-shrink-0" style={{ color: "var(--text-muted)" }}><Icon size={14} /></span>
      <span className="text-sm flex-1 truncate">{text}</span>
      <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>{time}</span>
      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>
        {type === "task" ? "任务" : type === "search" ? "检索" : type === "experiment" ? "试验" : type}
      </span>
    </div>
  );
}
