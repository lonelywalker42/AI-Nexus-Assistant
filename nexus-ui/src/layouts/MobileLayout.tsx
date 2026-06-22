/**
 * 移动端布局 — v4.0.0
 * 底部标签栏导航，适配 Android/iOS
 */

import {
  IconClipboard, IconSearch, IconLightbulb, IconChat, IconGear,
} from "../components/Icons";

interface MobileLayoutProps {
  children: React.ReactNode;
  activePage: string;
  onNavigate: (page: string) => void;
}

const TABS = [
  { id: "tasks", label: "任务", icon: IconClipboard },
  { id: "literature", label: "文献", icon: IconSearch },
  { id: "knowledge", label: "IDEA", icon: IconLightbulb },
  { id: "chat", label: "AI", icon: IconChat },
  { id: "settings", label: "设置", icon: IconGear },
];

export default function MobileLayout({ children, activePage, onNavigate }: MobileLayoutProps) {
  return (
    <div className="flex flex-col h-screen" style={{ background: "var(--bg-gradient)" }}>
      {/* 主内容区域 */}
      <main className="flex-1 overflow-auto pb-16">
        {children}
      </main>

      {/* 底部标签栏 */}
      <nav
        className="fixed bottom-0 left-0 right-0 h-16 flex items-center justify-around z-50"
        style={{
          background: "var(--glass-bg)",
          backdropFilter: "blur(12px)",
          borderTop: "1px solid var(--border-color)",
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}
      >
        {TABS.map((tab) => {
          const isActive = activePage === tab.id || (tab.id === "tasks" && activePage === "dashboard");
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => onNavigate(tab.id)}
              className="flex flex-col items-center justify-center gap-0.5 py-1 px-3 transition-colors"
              style={{
                color: isActive ? "var(--accent-blue)" : "var(--text-muted)",
              }}
            >
              <Icon size={20} />
              <span className="text-[10px]">{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
