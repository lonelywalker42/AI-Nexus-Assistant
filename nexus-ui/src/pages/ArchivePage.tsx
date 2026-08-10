/**
 * 工作归档页面 — 按周查看每日工作归档（已完成任务 + AI日报 + 工作总结）
 * 布局：左上日历（带周数） + 右上活跃度热力图 + 下方7天归档卡片
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { tasksApi, type Task } from "../api/client";
import { getPriority } from "../constants/task";

// ── 类型 ──

interface StructuredWorkNote {
  rawInput: string;
  completed: string[];
  issues: string[];
  plans: string[];
  timestamp: string;
}

// ── 日期工具 ──

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** 获取 dateStr 所在周的 周一~周日 日期数组 */
function getWeekDays(dateStr: string): string[] {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon, ...
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((day + 6) % 7));
  const result: string[] = [];
  for (let i = 0; i < 7; i++) {
    const dd = new Date(monday);
    dd.setDate(monday.getDate() + i);
    result.push(toDateStr(dd));
  }
  return result;
}

/** ISO 周数 */
function getISOWeek(date: Date): number {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7));
  const week1 = new Date(d.getFullYear(), 0, 4);
  return 1 + Math.round(((d.getTime() - week1.getTime()) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7);
}

function parseDate(dateStr: string): Date {
  return new Date(dateStr + "T00:00:00");
}

const WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
const MONTH_NAMES = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

// ── 活跃度热力图 ──

function ActivityHeatmap({ data }: { data: Map<string, number> }) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; date: string; count: number } | null>(null);

  // 生成最近 140 天（20 周）
  const days: { date: string; count: number }[] = useMemo(() => {
    const result: { date: string; count: number }[] = [];
    const today = new Date();
    for (let i = 139; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const ds = toDateStr(d);
      result.push({ date: ds, count: data.get(ds) || 0 });
    }
    return result;
  }, [data]);

  // 按周分组（列）
  const weeks: { date: string; count: number }[][] = useMemo(() => {
    const result: { date: string; count: number }[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      result.push(days.slice(i, i + 7));
    }
    return result;
  }, [days]);

  const getColor = (count: number) => {
    if (count === 0) return "var(--border-color)";
    if (count <= 1) return "#DCFCE7";
    if (count <= 3) return "#BBF7D0";
    if (count <= 5) return "#86EFAC";
    return "#4ADE80";
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-[3px]">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day) => (
              <div
                key={day.date}
                className="w-[13px] h-[13px] rounded-[2px] cursor-pointer transition-transform hover:scale-125"
                style={{ background: getColor(day.count) }}
                onMouseEnter={e => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({ x: rect.left + rect.width / 2, y: rect.top - 8, date: day.date, count: day.count });
                }}
                onMouseLeave={() => setTooltip(null)}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--text-muted)" }}>
        <span>少</span>
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="w-[11px] h-[11px] rounded-[2px]" style={{ background: getColor(i) }} />
        ))}
        <span>多</span>
      </div>
      {tooltip && (
        <div
          className="fixed z-[999] px-2.5 py-1.5 rounded-lg text-[11px] pointer-events-none"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
            background: "var(--text-primary)",
            color: "var(--glass-bg)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          {tooltip.date} · 完成 {tooltip.count} 项任务
        </div>
      )}
    </div>
  );
}

// ── 主页面 ──

export default function ArchivePage() {
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [currentMonth, setCurrentMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [weekTasks, setWeekTasks] = useState<Map<string, Task[]>>(new Map());
  const [weekNotes, setWeekNotes] = useState<Map<string, StructuredWorkNote>>(new Map());
  const [weekLogs, setWeekLogs] = useState<Map<string, string>>(new Map());
  const [activityData, setActivityData] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(true);

  const weekDays = useMemo(() => getWeekDays(selectedDate), [selectedDate]);

  // 加载活跃度数据（热力图接口）
  useEffect(() => {
    tasksApi.heatmap(140).then(data => {
      const map = new Map<string, number>();
      Object.entries(data).forEach(([d, count]) => { map.set(d, count); });
      setActivityData(map);
    }).catch(() => {});
  }, []);

  // 加载当周数据
  const loadWeekData = useCallback(async (days: string[]) => {
    setLoading(true);
    try {
      const taskResults = await tasksApi.weekTasks(days[0]).catch(() => ({} as Record<string, Task[]>));
      const tasksMap = new Map<string, Task[]>();
      days.forEach((d) => {
        tasksMap.set(d, (taskResults[d] || []).filter(t => t.completed));
      });
      setWeekTasks(tasksMap);

      // 从 localStorage 读取日报
      const notesMap = new Map<string, StructuredWorkNote>();
      days.forEach(d => {
        try {
          const raw = localStorage.getItem(`nexus-structured-note-${d}`);
          if (raw) {
            const note = JSON.parse(raw);
            if (note && note.completed) notesMap.set(d, note);
          }
        } catch {}
      });
      setWeekNotes(notesMap);

      // 从 localStorage 读取工作日志
      const logsMap = new Map<string, string>();
      days.forEach(d => {
        const log = localStorage.getItem(`nexus-worklog-${d}`);
        if (log && log.trim()) logsMap.set(d, log);
      });
      setWeekLogs(logsMap);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWeekData(weekDays);
  }, [weekDays, loadWeekData]);

  // ── 日历渲染 ──

  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    // 周一=0 偏移
    const startOffset = (firstDay.getDay() + 6) % 7;
    const totalDays = lastDay.getDate();
    const cells: { date: string; day: number; isCurrentMonth: boolean; weekNum?: number }[] = [];

    // 上月补齐
    const prevLast = new Date(year, month, 0);
    for (let i = startOffset - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, prevLast.getDate() - i);
      cells.push({ date: toDateStr(d), day: d.getDate(), isCurrentMonth: false });
    }
    // 本月
    for (let i = 1; i <= totalDays; i++) {
      const d = new Date(year, month, i);
      cells.push({ date: toDateStr(d), day: i, isCurrentMonth: true });
    }
    // 下月补齐
    const remaining = 7 - (cells.length % 7);
    if (remaining < 7) {
      for (let i = 1; i <= remaining; i++) {
        const d = new Date(year, month + 1, i);
        cells.push({ date: toDateStr(d), day: i, isCurrentMonth: false });
      }
    }
    return cells;
  }, [currentMonth]);

  // 按周分组日历格子（每行7天）
  const calendarWeeks = useMemo(() => {
    const result: { date: string; day: number; isCurrentMonth: boolean }[][] = [];
    for (let i = 0; i < calendarDays.length; i += 7) {
      result.push(calendarDays.slice(i, i + 7));
    }
    return result;
  }, [calendarDays]);

  const today = todayStr();

  return (
    <div className="space-y-5">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>工作归档</h2>
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
          <span>第 {getISOWeek(parseDate(selectedDate))} 周</span>
          <span>·</span>
          <span>{weekDays[0]} ~ {weekDays[6]}</span>
        </div>
      </div>

      {/* 上半区：日历 + 热力图 */}
      <div className="grid grid-cols-5 gap-4">
        {/* 左上：日历 */}
        <div className="col-span-2 glass-card p-4 space-y-3">
          {/* 月份导航 */}
          <div className="flex items-center justify-between">
            <button
              className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer transition-colors"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
            </button>
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {currentMonth.getFullYear()}年{MONTH_NAMES[currentMonth.getMonth()]}
            </span>
            <div className="flex gap-1">
              <button
                className="px-2 py-0.5 rounded-md text-[11px] cursor-pointer transition-colors"
                style={{ color: "var(--accent-blue)", background: "transparent" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                onClick={() => { setSelectedDate(today); setCurrentMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1)); }}
              >今天</button>
              <button
                className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer transition-colors"
                style={{ color: "var(--text-secondary)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
              </button>
            </div>
          </div>

          {/* 星期标题 */}
          <div className="grid grid-cols-7 gap-0.5 text-center text-[10px]" style={{ color: "var(--text-muted)" }}>
            {["一", "二", "三", "四", "五", "六", "日"].map(d => <div key={d} className="py-0.5">{d}</div>)}
          </div>

          {/* 日历网格（带周数） */}
          <div className="space-y-0.5">
            {calendarWeeks.map((week, wi) => {
              const weekNum = getISOWeek(parseDate(week[0].date));
              return (
                <div key={wi} className="flex items-center gap-0.5">
                  <span className="w-6 text-[9px] text-center flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                    {weekNum}
                  </span>
                  <div className="grid grid-cols-7 gap-0.5 flex-1 text-center text-[11px]">
                    {week.map(cell => {
                      const isSelected = cell.date === selectedDate;
                      const isToday = cell.date === today;
                      const inWeek = weekDays.includes(cell.date);
                      return (
                        <div
                          key={cell.date}
                          className="py-1 rounded-md cursor-pointer transition-all relative"
                          style={{
                            color: isSelected ? "#fff" : isToday ? "var(--accent-blue)" : cell.isCurrentMonth ? "var(--text-primary)" : "var(--text-muted)",
                            background: isSelected ? "var(--accent-blue)" : isToday ? "var(--hover-bg)" : "transparent",
                            fontWeight: isSelected || isToday ? 600 : 400,
                            opacity: inWeek ? 1 : 0.5,
                          }}
                          onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "var(--hover-bg)"; }}
                          onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isToday ? "var(--hover-bg)" : "transparent"; }}
                          onClick={() => setSelectedDate(cell.date)}
                        >
                          {cell.day}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 右上：活跃度热力图 */}
        <div className="col-span-3 glass-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>按日活跃度</span>
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>最近 20 周</span>
          </div>
          <ActivityHeatmap data={activityData} />
        </div>
      </div>

      {/* 下半区：7天归档卡片 */}
      {loading ? (
        <div className="grid grid-cols-7 gap-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="glass-card p-4 space-y-3 animate-pulse">
              <div className="h-4 rounded" style={{ background: "var(--border-color)", width: "60%" }} />
              <div className="space-y-2">
                <div className="h-3 rounded" style={{ background: "var(--border-color)", width: "80%" }} />
                <div className="h-3 rounded" style={{ background: "var(--border-color)", width: "60%" }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-3">
          {weekDays.map((day, idx) => {
            const tasks = weekTasks.get(day) || [];
            const note = weekNotes.get(day);
            const log = weekLogs.get(day);
            const isToday = day === today;
            const isEmpty = tasks.length === 0 && !note && !log;
            const dayDate = parseDate(day);

            return (
              <div
                key={day}
                className="glass-card p-3 space-y-3 flex flex-col"
                style={{
                  maxHeight: "calc(100vh - 420px)",
                  minHeight: "280px",
                  borderLeft: isToday ? "3px solid var(--accent-blue)" : undefined,
                }}
              >
                {/* 日期标题 */}
                <div className="flex items-center justify-between flex-shrink-0">
                  <span
                    className="text-xs font-semibold"
                    style={{ color: isToday ? "var(--accent-blue)" : "var(--text-primary)" }}
                  >
                    {WEEKDAY_LABELS[idx]}
                  </span>
                  <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                    {dayDate.getMonth() + 1}/{dayDate.getDate()}
                  </span>
                </div>

                {/* 内容区（可滚动） */}
                <div className="flex-1 overflow-y-auto space-y-3 min-h-0" style={{ scrollbarWidth: "thin" }}>
                  {isEmpty ? (
                    <div className="flex flex-col items-center justify-center py-6 gap-2">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)", opacity: 0.4 }}>
                        <rect x="2" y="3" width="20" height="5" rx="1" /><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8" /><path d="M10 12h4" />
                      </svg>
                      <span className="text-[10px]" style={{ color: "var(--text-muted)", opacity: 0.5 }}>暂无记录</span>
                    </div>
                  ) : (
                    <>
                      {/* 已完成任务 */}
                      {tasks.length > 0 && (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: "var(--accent-green)" }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
                            已完成
                          </div>
                          {tasks.map(t => {
                            const p = getPriority(t.priority);
                            return (
                              <div key={t.id} className="flex items-start gap-1.5 text-[11px] py-0.5">
                                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: p.color }} />
                                <span style={{ color: "var(--text-secondary)" }} className="line-clamp-4" title={t.content}>{t.content}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* AI 日报 */}
                      {note && (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: "var(--accent-blue)" }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                            日报
                          </div>
                          {note.completed.length > 0 && (
                            <div className="space-y-0.5">
                              <span className="text-[10px] font-medium" style={{ color: "var(--accent-green)" }}>✅ 完成</span>
                              {note.completed.map((item, i) => (
                                <div key={i} className="text-[11px] pl-2 line-clamp-4" style={{ color: "var(--text-secondary)" }} title={item}>· {item}</div>
                              ))}
                            </div>
                          )}
                          {note.issues.length > 0 && (
                            <div className="space-y-0.5">
                              <span className="text-[10px] font-medium" style={{ color: "#f59e0b" }}>⚠️ 问题</span>
                              {note.issues.map((item, i) => (
                                <div key={i} className="text-[11px] pl-2 line-clamp-4" style={{ color: "var(--text-secondary)" }} title={item}>· {item}</div>
                              ))}
                            </div>
                          )}
                          {note.plans.length > 0 && (
                            <div className="space-y-0.5">
                              <span className="text-[10px] font-medium" style={{ color: "var(--accent-blue)" }}>📋 计划</span>
                              {note.plans.map((item, i) => (
                                <div key={i} className="text-[11px] pl-2 line-clamp-4" style={{ color: "var(--text-secondary)" }} title={item}>· {item}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* 今日总结 */}
                      {log && (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: "var(--text-secondary)" }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                            今日总结
                          </div>
                          <div
                            className="text-[11px] line-clamp-6 whitespace-pre-wrap"
                            style={{ color: "var(--text-secondary)" }}
                            title={log}
                          >
                            {log}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
