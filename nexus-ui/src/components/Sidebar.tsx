import { useState, useEffect } from "react";
import { getPageIcon } from "../App";
import { systemApi, type SystemInfo } from "../api/client";

interface Page {
  id: string;
  label: string;
  icon: string;
}

interface SidebarProps {
  pages: Page[];
  activePage: string;
  onNavigate: (id: string) => void;
}

export default function Sidebar({ pages, activePage, onNavigate }: SidebarProps) {
  const [showAbout, setShowAbout] = useState(false);
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    if (showAbout && !sysInfo) {
      systemApi.info().then(setSysInfo).catch(console.error);
    }
  }, [showAbout, sysInfo]);

  return (
    <>
      <aside className="w-56 h-full flex flex-col" style={{ background: 'var(--glass-bg)', backdropFilter: 'blur(12px)', borderRight: '1px solid var(--border-color)' }}>
        {/* Logo */}
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <h1 className="text-lg font-bold tracking-wider" style={{ color: "var(--accent-blue)" }}>NEXUS</h1>
          <p className="text-[11px] mt-0.5" style={{ color: "var(--text-muted)" }}>AI 科研助手</p>
        </div>

        {/* 导航 */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>总览</p>
          {pages.slice(0, 2).map((page) => (
            <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
          ))}

          <p className="px-3 py-1 pt-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>研究</p>
          {pages.slice(2, 5).map((page) => (
            <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
          ))}

          <p className="px-3 py-1 pt-3 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>系统</p>
          {pages.slice(5).map((page) => (
            <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
          ))}
        </nav>

        {/* 版本 — 可点击 */}
        <div className="px-4 py-2 text-center cursor-pointer" style={{ borderTop: '1px solid var(--border-color)' }}
          onClick={() => setShowAbout(true)}
          onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
        >
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>v1.4.0</span>
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
              <div className="text-3xl font-bold tracking-wider" style={{ color: "var(--accent-blue)" }}>NEXUS</div>
              <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>AI Nexus Assistant</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>v1.0.0</p>
              <div className="h-px" style={{ background: "var(--border-color)" }} />
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                面向航空航天/控制领域科研人员的个人研究助手桌面应用。
                集成任务管理、文献检索、AI 综述、试验记录、知识库、AI 对话六大功能模块，
                支持 8 源学术搜索、流式 AI 对话、本地文献管理。
              </p>
              <div className="flex justify-center gap-4 text-[10px] pt-1" style={{ color: "var(--text-muted)" }}>
                <span>Tauri 2 + React</span>
                <span>•</span>
                <span>FastAPI + SQLite</span>
                <span>•</span>
                <span>DeepSeek / OpenAI</span>
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

function NavItem({ page, active, onClick }: { page: Page; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150 btn-click cursor-pointer"
      style={active
        ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }
        : { color: "var(--text-secondary)" }
      }
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = "var(--hover-bg)"; }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}
    >
      <span className="flex-shrink-0">{getPageIcon(page.icon, 16)}</span>
      <span>{page.label}</span>
      {active && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--accent-blue)" }} />
      )}
    </button>
  );
}
