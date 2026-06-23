/**
 * 标签着色系统 — 基于标签名哈希自动分配颜色
 * 确保同一标签在不同位置显示一致的颜色
 */

// SpringNote 风格柔和色彩调色板
const TAG_PALETTE = [
  { bg: "rgba(255,107,157,0.1)", color: "#ff6b9d" },   // 玫瑰粉
  { bg: "rgba(139,92,246,0.1)", color: "#8b5cf6" },    // 紫罗兰
  { bg: "rgba(59,130,246,0.1)", color: "#3b82f6" },    // 天蓝
  { bg: "rgba(16,185,129,0.1)", color: "#10b981" },    // 翠绿
  { bg: "rgba(245,158,11,0.1)", color: "#f59e0b" },    // 琥珀
  { bg: "rgba(236,72,153,0.1)", color: "#ec4899" },    // 品红
  { bg: "rgba(6,182,212,0.1)", color: "#06b6d4" },     // 青蓝
  { bg: "rgba(249,115,22,0.1)", color: "#f97316" },    // 橘红
  { bg: "rgba(168,85,247,0.1)", color: "#a855f7" },    // 亮紫
  { bg: "rgba(20,184,166,0.1)", color: "#14b8a6" },    // 碧绿
  { bg: "rgba(244,63,94,0.1)", color: "#f43f5e" },     // 赤红
  { bg: "rgba(99,102,241,0.1)", color: "#6366f1" },    // 靛蓝
];

/**
 * 简单字符串哈希 (djb2)
 */
function hashString(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & 0x7fffffff; // 保证正数
  }
  return hash;
}

/**
 * 根据标签名获取一致的颜色
 * @param tagName 标签名称
 * @returns { bg, color } 背景色和文字色
 */
export function getTagColor(tagName: string): { bg: string; color: string } {
  const idx = hashString(tagName) % TAG_PALETTE.length;
  return TAG_PALETTE[idx];
}
