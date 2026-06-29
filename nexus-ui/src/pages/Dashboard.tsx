import { useEffect, useState } from "react";
import { dashboardApi, tasksApi, type DashboardData } from "../api/client";
import { IconCheck, IconSearch, IconFlask, IconChart, IconLightning } from "../components/Icons";

/* ── 日期工具 ── */
function getWeekDays(date: Date): Date[] {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((day + 6) % 7));
  const result: Date[] = [];
  for (let i = 0; i < 7; i++) {
    const dd = new Date(monday);
    dd.setDate(monday.getDate() + i);
    result.push(dd);
  }
  return result;
}

function formatWeekday(d: Date): string {
  const days = ["日", "一", "二", "三", "四", "五", "六"];
  return days[d.getDay()];
}

function toDateStr(d: Date): string {
  return d.toISOString().split("T")[0];
}

/* ── 活跃度热力图 (5.1.3) ── */
function ActivityHeatmap({ taskDates }: { taskDates: Map<string, number> }) {
  const today = new Date();
  const weeks: { date: Date; count: number }[][] = [];
  let currentWeek: { date: Date; count: number }[] = [];

  for (let i = 139; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().split("T")[0];
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
                style={{ width: 13, height: 13, background: getColor(day.count) }}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({
                    x: rect.left + rect.width / 2, y: rect.top - 8,
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
  const [taskDates, setTaskDates] = useState<Map<string, number>>(new Map());
  const [weeklyData, setWeeklyData] = useState<{ label: string; value: number }[]>([]);

  useEffect(() => {
    dashboardApi.get().then(setData).catch(console.error);
    // 加载任务完成日期统计（热力图）
    tasksApi.heatmap(140).then(data => {
      const dates = new Map<string, number>();
      Object.entries(data).forEach(([d, count]) => { dates.set(d, count); });
      setTaskDates(dates);

      // 获取最近 7 天的数据
      const weekDays = getWeekDays(new Date());
      const weekData = weekDays.map(d => ({
        label: formatWeekday(d),
        value: data[toDateStr(d)] || 0,
      }));
      setWeeklyData(weekData);
    }).catch(() => {});
  }, []);

  const tasks = data?.tasks;
  const monthly = data?.monthly;
  const exps = data?.experiments;
  const kb = data?.knowledge;
  const rate = monthly && monthly.total > 0 ? Math.round((monthly.done / monthly.total) * 100) : 0;
  const maxVal = weeklyData.length > 0 ? Math.max(...weeklyData.map(w => w.value), 1) : 1;

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
            {weeklyData.map((item, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t transition-all"
                  style={{
                    height: `${(item.value / maxVal) * 100}%`,
                    background: `linear-gradient(to top, var(--accent-blue), rgba(59,130,246,0.5))`,
                    minHeight: "4px",
                  }}
                />
                <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>周{item.label}</span>
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

      {/* 活跃度热力图 */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--text-primary)" }}>任务活跃度</h3>
        <ActivityHeatmap taskDates={taskDates} />
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
