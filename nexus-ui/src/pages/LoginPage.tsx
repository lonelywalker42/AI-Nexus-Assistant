import { useState } from "react";
import { authApi } from "../api/client";

interface LoginPageProps {
  onLogin: () => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError("请输入用户名和密码");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await authApi.login(username, password);
      onLogin();
    } catch (err: any) {
      setError(err.message || "登录失败");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--bg-gradient)" }}>
      <div className="glass-card p-8 w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
            AI Nexus Assistant
          </h1>
          <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
            科研助手 · v4.5.5
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg text-sm outline-none transition-all"
              style={{
                background: "var(--input-bg)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
              }}
              placeholder="admin"
              autoFocus
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg text-sm outline-none transition-all"
              style={{
                background: "var(--input-bg)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
              }}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="text-xs p-3 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-sm font-medium transition-all"
            style={{
              background: "var(--accent-blue)",
              color: "#fff",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "登录中..." : "登录"}
          </button>
        </form>

        <div className="text-center">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            默认账号: admin / nexus2024
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            桌面端本地模式可跳过登录
          </p>
        </div>
      </div>
    </div>
  );
}
