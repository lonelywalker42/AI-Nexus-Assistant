// 任务系统共享常量 — 消除 TaskPage/TodayPage 重复定义

export const PRIORITIES = [
  { key: "urgent", label: "紧急", shortLabel: "急", color: "#ef4444", bg: "rgba(239,68,68,0.12)", border: "#f87171" },
  { key: "high", label: "高优先级", shortLabel: "高", color: "#f59e0b", bg: "rgba(245,158,11,0.12)", border: "#fbbf24" },
  { key: "normal", label: "普通", shortLabel: "普", color: "var(--text-secondary)", bg: "rgba(59,130,246,0.08)", border: "#60a5fa" },
  { key: "low", label: "低优先级", shortLabel: "低", color: "var(--text-muted)", bg: "rgba(148,163,184,0.1)", border: "#94a3b8" },
] as const;

export type PriorityKey = typeof PRIORITIES[number]["key"];

export const CATEGORIES = [
  { key: "general", label: "日常", icon: "📋" },
  { key: "main", label: "核心", icon: "🎯" },
  { key: "literature", label: "文献", icon: "📄" },
  { key: "experiment", label: "试验", icon: "🧪" },
  { key: "writing", label: "写作", icon: "✏️" },
] as const;

export type CategoryKey = typeof CATEGORIES[number]["key"];

export function getPriority(key: string) {
  return PRIORITIES.find(p => p.key === key) || PRIORITIES[2]; // default: normal
}

export function getCategory(key: string) {
  return CATEGORIES.find(c => c.key === key) || CATEGORIES[0]; // default: general
}

// 判断任务是否逾期（date < 今天且未完成）
export function isOverdue(dateStr: string, completed: boolean): boolean {
  if (completed) return false;
  const today = new Date().toISOString().slice(0, 10);
  return dateStr < today;
}
