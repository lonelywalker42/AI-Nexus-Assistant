import { useState, useEffect } from "react";
import { getPageIcon } from "../App";
import { systemApi, type SystemInfo } from "../api/client";
import { useAppName } from "../hooks/useAppName";
import { IconChat } from "./Icons";

interface Page {
  id: string;
  label: string;
  icon: string;
  group: string;
}

interface SidebarProps {
  pages: Page[];
  activePage: string;
  onNavigate: (id: string) => void;
}

const GROUPS: Array<{ key: string; label: string; badge?: string }> = [
  { key: "overview", label: "总览" },
  { key: "research", label: "科研助手" },
  { key: "personal", label: "个人助手" },
  { key: "settings", label: "设置" },
];

export default function Sidebar({ pages, activePage, onNavigate }: SidebarProps) {
  const [showAbout, setShowAbout] = useState(false);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const { name, subtitle } = useAppName();

  useEffect(() => {
    if (showAbout && !sysInfo) {
      systemApi.info().then(setSysInfo).catch(console.error);
    }
  }, [showAbout, sysInfo]);

  const chatPage = pages.find(p => p.id === "chat");

  return (
    <>
      <aside className="w-52 h-full flex flex-col" style={{ background: 'var(--glass-bg)', backdropFilter: 'blur(12px)', borderRight: '1px solid var(--border-color)' }}>
        {/* Logo */}
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <h1 className="text-lg font-bold tracking-wider" style={{ color: "var(--accent-blue)" }}>{name}</h1>
          <p className="text-[11px] mt-0.5" style={{ color: "var(--text-muted)" }}>{subtitle}</p>
        </div>

        {/* 导航 */}
        <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
          {GROUPS.map(group => {
            const groupPages = pages.filter(p => p.group === group.key);
            if (groupPages.length === 0) return null;

            return (
              <div key={group.key} className="mb-1">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
                  {group.label}
                  {group.badge && (
                    <span className="px-1.5 py-0 rounded text-[8px] font-medium"
                      style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b" }}>
                      {group.badge}
                    </span>
                  )}
                </p>
                {groupPages.map(page => (
                  <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
                ))}
              </div>
            );
          })}
        </nav>

        {/* AI 对话浮动按钮 */}
        {chatPage && (
          <div className="px-3 pb-2">
            <button
              onClick={() => onNavigate("chat")}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold cursor-pointer transition-all duration-200 btn-click"
              style={{
                background: activePage === "chat"
                  ? "linear-gradient(135deg, var(--accent-blue), var(--accent-green))"
                  : "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(16,185,129,0.15))",
                color: activePage === "chat" ? "#fff" : "var(--accent-blue)",
                border: activePage === "chat" ? "none" : "1px solid rgba(59,130,246,0.2)",
              }}
              onMouseEnter={e => {
                if (activePage !== "chat") {
                  e.currentTarget.style.background = "linear-gradient(135deg, rgba(59,130,246,0.25), rgba(16,185,129,0.25))";
                }
              }}
              onMouseLeave={e => {
                if (activePage !== "chat") {
                  e.currentTarget.style.background = "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(16,185,129,0.15))";
                }
              }}
            >
              <IconChat size={16} />
              <span>AI 对话</span>
            </button>
          </div>
        )}

        {/* 版本 — 可点击 */}
        <div className="px-4 py-2 text-center cursor-pointer" style={{ borderTop: '1px solid var(--border-color)' }}
          onClick={() => setShowAbout(true)}
          onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
        >
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>v3.1.0</span>
        </div>
      </aside>

      {/* About 弹窗 */}
      {showAbout && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.4)" }}
          onClick={() => setShowAbout(false)}
        >
          <div className="glass-card p-6 max-w-sm w-full mx-4 animate-fade-in"
            style={{ background: "var(--glass-bg)", backdropFilter: "blur(20px)" }}
            onClick={e => e.stopPropagation()}
          >
            <div className="text-center space-y-3">
              <div className="text-3xl font-bold tracking-wider" style={{ color: "var(--accent-blue)" }}>{name}</div>
              <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{name} Assistant</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>v3.1.0</p>
              <div className="h-px" style={{ background: "var(--border-color)" }} />
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                面向航空航天/控制领域科研人员的个人研究助手桌面应用。
                集成仪表盘、任务管理、今日工作、文献检索与管理、AI 综述、试验记录、知识库、AI 对话八大功能模块，
                支持 8 源学术搜索、PDF 文献导入与 AI 元数据提取、流式 AI 对话（含联网搜索）、本地数据备份与恢复。
              </p>
              <div className="flex justify-center gap-4 text-[10px] pt-1" style={{ color: "var(--text-muted)" }}>
                <span>Tauri 2 + React</span>
                <span>•</span>
                <span>FastAPI + SQLite</span>
                <span>•</span>
                <span>DeepSeek / OpenAI / Anthropic</span>
              </div>
              {sysInfo && (
                <div className="text-[10px] pt-1 space-y-0.5" style={{ color: "var(--text-muted)" }}>
                  <div>数据库: {sysInfo.db_size_str}</div>
                  <div>数据目录: {sysInfo.data_dir}</div>
                </div>
              )}
              <button className="btn-ghost mt-2 text-xs" onClick={() => setShowAbout(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function NavItem({ page, active, onClick, disabled }: { page: Page; active: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150 btn-click cursor-pointer"
      style={{
        ...(active
          ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }
          : { color: disabled ? "var(--text-muted)" : "var(--text-secondary)" }),
        ...(disabled ? { opacity: 0.5, cursor: "not-allowed" } : {}),
      }}
      onMouseEnter={e => { if (!active && !disabled) e.currentTarget.style.background = "var(--hover-bg)"; }}
      onMouseLeave={e => { if (!active && !disabled) e.currentTarget.style.background = "transparent"; }}
    >
      <span className="flex-shrink-0">{getPageIcon(page.icon, 15)}</span>
      <span className="text-[13px]">{page.label}</span>
      {active && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--accent-blue)" }} />
      )}
    </button>
  );
}
