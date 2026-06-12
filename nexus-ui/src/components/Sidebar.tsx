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
  return (
    <aside className="w-64 h-full flex flex-col border-r border-slate-200/60"
           style={{ background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(12px)' }}>
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-200/60">
        <h1 className="text-xl font-bold tracking-wider text-primary-600">NEXUS</h1>
        <p className="text-xs text-slate-400 mt-0.5">AI 科研助手</p>
      </div>

      {/* 导航 */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {/* 总览 */}
        <p className="px-3 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">总览</p>
        {pages.slice(0, 2).map((page) => (
          <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
        ))}

        {/* 研究 */}
        <p className="px-3 py-1 pt-4 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">研究</p>
        {pages.slice(2, 5).map((page) => (
          <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
        ))}

        {/* 系统 */}
        <p className="px-3 py-1 pt-4 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">系统</p>
        {pages.slice(5).map((page) => (
          <NavItem key={page.id} page={page} active={activePage === page.id} onClick={() => onNavigate(page.id)} />
        ))}
      </nav>

      {/* 版本 */}
      <div className="px-4 py-3 border-t border-slate-200/60 text-center">
        <span className="text-[11px] text-slate-400">v0.3.0</span>
      </div>
    </aside>
  );
}

function NavItem({ page, active, onClick }: { page: Page; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium
        transition-all duration-200 btn-click
        ${active
          ? 'bg-primary-50 text-primary-600 shadow-sm'
          : 'text-slate-500 hover:bg-slate-100/60 hover:text-slate-700'
        }
      `}
    >
      <span className="text-base">{page.icon}</span>
      <span>{page.label}</span>
      {active && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-500" />
      )}
    </button>
  );
}
