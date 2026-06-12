import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import TaskPage from "./pages/TaskPage";
import LiteraturePage from "./pages/LiteraturePage";
import ExperimentPage from "./pages/ExperimentPage";
import KnowledgePage from "./pages/KnowledgePage";
import ChatPage from "./pages/ChatPage";
import SettingsPage from "./pages/SettingsPage";

const PAGES = [
  { id: "dashboard", label: "仪表盘", icon: "📊" },
  { id: "tasks", label: "任务与日程", icon: "📋" },
  { id: "literature", label: "文献管理", icon: "📚" },
  { id: "experiments", label: "试验管理", icon: "🧪" },
  { id: "knowledge", label: "知识库", icon: "🧠" },
  { id: "chat", label: "AI 对话", icon: "💬" },
  { id: "settings", label: "设置", icon: "⚙️" },
];

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const renderPage = () => {
    switch (activePage) {
      case "dashboard": return <Dashboard />;
      case "tasks": return <TaskPage />;
      case "literature": return <LiteraturePage />;
      case "experiments": return <ExperimentPage />;
      case "knowledge": return <KnowledgePage />;
      case "chat": return <ChatPage />;
      case "settings": return <SettingsPage />;
      default: return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-gradient)' }}>
      {/* 标题栏 */}
      <div className="fixed top-0 left-0 right-0 h-9 z-50 flex items-center justify-between px-4"
           style={{ background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #e2e8f0' }}
           data-tauri-drag-region>
        <span className="text-xs text-slate-400 select-none">AI Nexus Assistant</span>
        <div className="flex gap-1">
          <button className="w-7 h-5 rounded hover:bg-slate-100 text-slate-400 text-xs">—</button>
          <button className="w-7 h-5 rounded hover:bg-slate-100 text-slate-400 text-xs">□</button>
          <button className="w-7 h-5 rounded hover:bg-red-500 hover:text-white text-slate-400 text-xs">×</button>
        </div>
      </div>

      {/* 侧边栏 */}
      <div className="mt-9">
        <Sidebar pages={PAGES} activePage={activePage} onNavigate={setActivePage} />
      </div>

      {/* 主内容 */}
      <main className="flex-1 mt-9 overflow-auto p-6">
        <div className="animate-fade-in">
          {renderPage()}
        </div>
      </main>
    </div>
  );
}

export default App;
