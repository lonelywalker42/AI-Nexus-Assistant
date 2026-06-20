import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import TaskPage from "./pages/TaskPage";
import TodayPage from "./pages/TodayPage";
import LiteraturePage from "./pages/LiteraturePage";
import PaperLibraryPage from "./pages/PaperLibraryPage";
import ExperimentPage from "./pages/ExperimentPage";
import KnowledgePage from "./pages/KnowledgePage";
import ChatPage from "./pages/ChatPage";
import SettingsPage from "./pages/SettingsPage";
import MusicPage from "./pages/MusicPage";
import BookshelfPage from "./pages/BookshelfPage";
import WritingPage from "./pages/WritingPage";
import { dashboardApi } from "./api/client";
import {
  IconChart, IconClipboard, IconBook, IconSearch, IconFlask, IconBrain, IconChat,
  IconGear, IconX, IconMinus, IconMaximize, IconCalendar, IconLightbulb, IconImage,
  IconMusic, IconBookOpen,
} from "./components/Icons";
import { useAppName } from "./hooks/useAppName";

// ── 页面注册 ──
const PAGES = [
  // 总览
  { id: "dashboard", label: "仪表盘", icon: "chart", group: "overview" },
  { id: "tasks", label: "任务与日程", icon: "clipboard", group: "overview" },
  { id: "today", label: "今日工作", icon: "calendar", group: "overview" },
  // 科研助手
  { id: "literature", label: "文献检索", icon: "search", group: "research" },
  { id: "paper-library", label: "文献库", icon: "book", group: "research" },
  { id: "knowledge", label: "IDEA", icon: "lightbulb", group: "research" },
  { id: "experiments", label: "试验管理", icon: "flask", group: "research" },
  { id: "chat", label: "AI 对话", icon: "chat", group: "research" },
  { id: "writing", label: "写作", icon: "book", group: "research" },
  // 个人助手
  { id: "music", label: "音乐", icon: "music", group: "personal" },
  { id: "bookshelf", label: "书架", icon: "bookOpen", group: "personal" },
  { id: "materials", label: "素材库", icon: "image", group: "personal" },
  // 设置
  { id: "settings", label: "设置", icon: "gear", group: "settings" },
];

const ICON_MAP: Record<string, React.FC<{ size?: number }>> = {
  chart: IconChart, clipboard: IconClipboard, book: IconBook, search: IconSearch,
  flask: IconFlask, brain: IconBrain, chat: IconChat, gear: IconGear,
  calendar: IconCalendar, lightbulb: IconLightbulb, image: IconImage,
  music: IconMusic, bookOpen: IconBookOpen,
};

export function getPageIcon(iconKey: string, size = 18) {
  const Icon = ICON_MAP[iconKey];
  return Icon ? <Icon size={size} /> : null;
}

// Tauri 窗口控制
async function windowMinimize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().minimize();
  } catch {}
}

async function windowToggleMaximize() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    const win = getCurrentWindow();
    if (await win.isMaximized()) {
      await win.unmaximize();
    } else {
      await win.maximize();
    }
  } catch {}
}

async function windowClose() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().close();
  } catch {}
}

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const { name } = useAppName();

  // 初始化主题
  useEffect(() => {
    const saved = localStorage.getItem("nexus-theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
  }, []);

  useEffect(() => {
    dashboardApi.get()
      .then(() => setLoading(false))
      .catch(() => {
        const interval = setInterval(() => {
          dashboardApi.get().then(() => {
            setLoading(false);
            clearInterval(interval);
          }).catch(() => {});
        }, 1000);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: 'var(--bg-gradient)' }}>
        <div className="glass-card p-8 text-center space-y-4">
          <div className="flex justify-center" style={{ color: "var(--accent-blue)" }}><IconBrain size={40} /></div>
          <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{name} Assistant</h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>正在启动后端服务...</p>
          <div className="w-48 h-1.5 rounded-full overflow-hidden mx-auto" style={{ background: "var(--border-color)" }}>
            <div className="h-full rounded-full animate-pulse" style={{ width: "60%", background: "var(--accent-blue)" }} />
          </div>
        </div>
      </div>
    );
  }

  const renderPage = () => {
    switch (activePage) {
      case "dashboard": return <Dashboard onNavigate={setActivePage} />;
      case "tasks": return <TaskPage />;
      case "today": return <TodayPage onNavigate={setActivePage} />;
      case "literature": return <LiteraturePage />;
      case "paper-library": return <PaperLibraryPage />;
      case "experiments": return <ExperimentPage />;
      case "knowledge": return <KnowledgePage />;
      case "chat": return <ChatPage />;
      case "writing": return <WritingPage />;
      case "music": return <MusicPage />;
      case "bookshelf": return <BookshelfPage />;
      case "materials": return (
        <div className="flex-1 flex items-center justify-center">
          <div className="glass-card p-12 text-center space-y-4">
            <IconImage size={48} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
            <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>素材库</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>即将推出</p>
          </div>
        </div>
      );
      case "settings": return <SettingsPage />;
      default: return <Dashboard onNavigate={setActivePage} />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden select-none" style={{ background: 'var(--bg-gradient)' }}>
      {/* 标题栏 */}
      <div
        className="fixed top-0 left-0 right-0 h-9 z-50 flex items-center justify-between px-4"
        style={{ background: 'var(--glass-bg)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border-color)' }}
        data-tauri-drag-region
      >
        <span className="text-xs pointer-events-none" style={{ color: "var(--text-muted)" }}>{name} Assistant</span>
        <div className="flex gap-0.5" data-tauri-drag-region="false">
          <button
            onClick={windowMinimize}
            className="w-9 h-7 rounded flex items-center justify-center transition-colors cursor-pointer"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            data-tauri-drag-region="false"
          ><IconMinus size={14} /></button>
          <button
            onClick={windowToggleMaximize}
            className="w-9 h-7 rounded flex items-center justify-center transition-colors cursor-pointer"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            data-tauri-drag-region="false"
          ><IconMaximize size={14} /></button>
          <button
            onClick={windowClose}
            className="w-9 h-7 rounded flex items-center justify-center transition-colors cursor-pointer"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={e => { e.currentTarget.style.background = "#ef4444"; e.currentTarget.style.color = "#fff"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--text-secondary)"; }}
            data-tauri-drag-region="false"
          ><IconX size={14} /></button>
        </div>
      </div>

      {/* 侧边栏 */}
      <div className="mt-9">
        <Sidebar pages={PAGES} activePage={activePage} onNavigate={setActivePage} />
      </div>

      {/* 主内容 */}
      <main className="flex-1 mt-9 p-6 flex flex-col overflow-hidden">
        <div className="animate-fade-in flex-1 flex flex-col min-h-0 overflow-auto">
          {renderPage()}
        </div>
      </main>

      {/* 右下角缩放提示 */}
      <div
        className="fixed bottom-0 right-0 w-4 h-4 pointer-events-none z-50"
        style={{ background: 'linear-gradient(135deg, transparent 50%, var(--text-muted) 50%)', opacity: 0.2 }}
      />
    </div>
  );
}

export default App;
