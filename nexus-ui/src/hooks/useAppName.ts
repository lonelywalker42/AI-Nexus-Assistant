import { useState, useEffect } from "react";

const STORAGE_KEY = "nexus-app-name";
const DEFAULT_NAME = "NEXUS";
const DEFAULT_SUBTITLE = "AI 科研助手";

export function getAppName(): string {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_NAME;
}

export function setAppName(name: string) {
  if (name && name !== DEFAULT_NAME) {
    localStorage.setItem(STORAGE_KEY, name.trim());
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
  // 通知所有监听者
  window.dispatchEvent(new Event("app-name-changed"));
}

export function resetAppName() {
  localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event("app-name-changed"));
}

export function useAppName() {
  const [name, setName] = useState(getAppName());

  useEffect(() => {
    const handler = () => setName(getAppName());
    window.addEventListener("app-name-changed", handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("app-name-changed", handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  return { name, subtitle: DEFAULT_SUBTITLE, isDefault: name === DEFAULT_NAME };
}
