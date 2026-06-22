/**
 * 平台检测 Hook — v4.0.0
 * 运行时检测当前平台类型（桌面端/移动端）
 * 优先使用 Tauri OS 插件，回退到 User-Agent 检测
 */

import { useState, useEffect } from "react";

type Platform = "windows" | "macos" | "linux" | "android" | "ios" | "unknown";

interface PlatformInfo {
  os: Platform;
  isMobile: boolean;
  isDesktop: boolean;
  isTauri: boolean;
}

// 从 User-Agent 检测平台（不依赖 Tauri API 的回退方案）
function detectFromUA(): Platform {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("android")) return "android";
  if (ua.includes("iphone") || ua.includes("ipad")) return "ios";
  if (ua.includes("win")) return "windows";
  if (ua.includes("mac")) return "macos";
  if (ua.includes("linux")) return "linux";
  return "unknown";
}

export function usePlatform(): PlatformInfo {
  const [info, setInfo] = useState<PlatformInfo>(() => {
    const os = detectFromUA();
    return {
      os,
      isMobile: os === "android" || os === "ios",
      isDesktop: os === "windows" || os === "macos" || os === "linux",
      isTauri: "__TAURI_INTERNALS__" in window,
    };
  });

  useEffect(() => {
    // 尝试使用 Tauri OS 插件获取精确平台信息
    (async () => {
      try {
        const { platform } = await import("@tauri-apps/plugin-os");
        const os = platform() as Platform;
        setInfo({
          os,
          isMobile: os === "android" || os === "ios",
          isDesktop: os === "windows" || os === "macos" || os === "linux",
          isTauri: true,
        });
      } catch {
        // 非 Tauri 环境，使用 UA 检测结果
      }
    })();
  }, []);

  return info;
}
