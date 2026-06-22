import { useRef, useState, useEffect, useCallback } from "react";
import { IconMaximize, IconX } from "../components/Icons";

export default function GameConsolePage() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
      setIsFullscreen(false);
    } else {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    }
  }, []);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  return (
    <div ref={containerRef} className="flex-1 flex flex-col min-h-0" style={{ background: "var(--bg-gradient)" }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 flex-shrink-0"
        style={{ borderBottom: "1px solid var(--border-color)" }}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>🎮 游戏机模式</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full"
            style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
            8 款游戏
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleFullscreen}
            className="p-1.5 rounded-lg transition-colors cursor-pointer"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            title={isFullscreen ? "退出全屏" : "全屏"}
          >
            {isFullscreen ? <IconX size={16} /> : <IconMaximize size={16} />}
          </button>
        </div>
      </div>

      {/* Game iframe */}
      <div className="flex-1 flex items-center justify-center min-h-0 p-4">
        <iframe
          ref={iframeRef}
          src="/games.html"
          className="rounded-lg shadow-2xl"
          style={{
            width: "480px",
            height: "640px",
            maxWidth: "100%",
            maxHeight: "100%",
            border: "none",
            imageRendering: "pixelated",
          }}
          allow="autoplay"
          title="Retro Arcade"
        />
      </div>
    </div>
  );
}
