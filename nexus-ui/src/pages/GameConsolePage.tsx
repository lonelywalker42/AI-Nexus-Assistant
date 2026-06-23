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
    <div
      ref={containerRef}
      className="flex-1 flex flex-col min-h-0 relative overflow-hidden"
      style={{ background: "var(--bg-gradient)" }}
    >
      {/* CRT Scanline Overlay */}
      <div
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          background:
            "repeating-linear-gradient(to bottom, transparent 0px, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)",
          mixBlendMode: "multiply",
        }}
      />

      {/* Retro Header Bar */}
      <div
        className="flex items-center justify-between px-4 py-2.5 flex-shrink-0 relative z-20"
        style={{
          background: "rgba(15,15,35,0.85)",
          borderBottom: "2px solid rgba(0,255,65,0.3)",
          backdropFilter: "blur(8px)",
        }}
      >
        <div className="flex items-center gap-3">
          {/* Pixel icon */}
          <div
            className="flex items-center justify-center w-7 h-7"
            style={{
              background: "rgba(0,255,65,0.15)",
              border: "1px solid rgba(0,255,65,0.4)",
              borderRadius: "2px",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              style={{ imageRendering: "pixelated" }}
            >
              <rect x="2" y="2" width="4" height="4" fill="#00ff41" />
              <rect x="8" y="2" width="4" height="4" fill="#00ff41" />
              <rect x="4" y="6" width="8" height="4" fill="#00ff41" />
              <rect x="2" y="10" width="4" height="4" fill="#00ff41" />
              <rect x="10" y="10" width="4" height="4" fill="#00ff41" />
            </svg>
          </div>

          {/* Title with pixel font effect */}
          <div className="flex flex-col">
            <span
              className="text-sm tracking-wider"
              style={{
                color: "#00ff41",
                fontFamily: "'Press Start 2P', 'VT323', Consolas, monospace",
                fontSize: "12px",
                textShadow: "0 0 8px rgba(0,255,65,0.6), 0 0 16px rgba(0,255,65,0.3)",
                letterSpacing: "2px",
              }}
            >
              RETRO ARCADE
            </span>
            <span
              className="text-[9px] tracking-wide"
              style={{
                color: "rgba(0,255,65,0.5)",
                fontFamily: "Consolas, monospace",
              }}
            >
              16 GAMES · NEXUS CONSOLE
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5">
          {/* Fullscreen button */}
          <button
            onClick={toggleFullscreen}
            className="flex items-center justify-center w-7 h-7 transition-all duration-200 cursor-pointer"
            style={{
              background: isFullscreen
                ? "rgba(255,51,51,0.2)"
                : "rgba(0,255,65,0.1)",
              border: `1px solid ${isFullscreen ? "rgba(255,51,51,0.5)" : "rgba(0,255,65,0.3)"}`,
              borderRadius: "2px",
              color: isFullscreen ? "#ff3333" : "#00ff41",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = isFullscreen
                ? "rgba(255,51,51,0.3)"
                : "rgba(0,255,65,0.2)";
              e.currentTarget.style.boxShadow = isFullscreen
                ? "0 0 8px rgba(255,51,51,0.4)"
                : "0 0 8px rgba(0,255,65,0.4)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isFullscreen
                ? "rgba(255,51,51,0.2)"
                : "rgba(0,255,65,0.1)";
              e.currentTarget.style.boxShadow = "none";
            }}
            title={isFullscreen ? "退出全屏" : "全屏"}
          >
            {isFullscreen ? <IconX size={14} /> : <IconMaximize size={14} />}
          </button>
        </div>
      </div>

      {/* Game iframe container */}
      <div className="flex-1 flex items-center justify-center min-h-0 relative z-20 p-3">
        {/* CRT Monitor Frame */}
        <div
          className="relative"
          style={{
            width: "480px",
            height: "640px",
            maxWidth: "100%",
            maxHeight: "100%",
          }}
        >
          {/* Outer glow */}
          <div
            className="absolute -inset-2 rounded-lg"
            style={{
              background:
                "linear-gradient(135deg, rgba(0,255,65,0.1), rgba(0,255,255,0.05))",
              filter: "blur(8px)",
            }}
          />

          {/* Monitor bezel */}
          <div
            className="relative rounded-lg overflow-hidden"
            style={{
              border: "3px solid rgba(0,255,65,0.2)",
              boxShadow:
                "inset 0 0 30px rgba(0,0,0,0.5), 0 0 20px rgba(0,255,65,0.1), 0 0 40px rgba(0,255,65,0.05)",
              background: "#0a0a0a",
            }}
          >
            {/* Inner scanlines */}
            <div
              className="absolute inset-0 pointer-events-none z-10"
              style={{
                background:
                  "repeating-linear-gradient(to bottom, transparent 0px, transparent 1px, rgba(0,0,0,0.15) 1px, rgba(0,0,0,0.15) 2px)",
              }}
            />

            {/* Corner LEDs */}
            <div className="absolute top-2 right-2 z-10 flex items-center gap-1.5">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: "#00ff41",
                  boxShadow: "0 0 4px #00ff41, 0 0 8px rgba(0,255,65,0.5)",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              />
            </div>

            {/* iframe */}
            <iframe
              ref={iframeRef}
              src="/games.html"
              className="block"
              style={{
                width: "100%",
                height: "640px",
                border: "none",
                imageRendering: "pixelated",
              }}
              allow="autoplay"
              title="Retro Arcade"
            />
          </div>

          {/* Bottom label */}
          <div
            className="flex items-center justify-center mt-2 gap-3"
            style={{
              fontFamily: "Consolas, monospace",
              fontSize: "9px",
              color: "rgba(0,255,65,0.4)",
              letterSpacing: "2px",
            }}
          >
            <span>◄ SELECT ►</span>
            <span>·</span>
            <span>ENTER START</span>
            <span>·</span>
            <span>ESC MENU</span>
          </div>
        </div>
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
