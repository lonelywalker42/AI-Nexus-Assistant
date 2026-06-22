import { useEffect, useState } from "react";
import { modelsApi, type ModelConfig } from "../api/client";
import { useAppName, setAppName, resetAppName } from "../hooks/useAppName";

// 自动更新相关类型
interface UpdateInfo {
  version: string;
  notes: string;
  available: boolean;
  downloading?: boolean;
  progress?: number;
}

interface BackupItem {
  name: string;
  path: string;
  size: number;
  time: string;
}

export default function SettingsPage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", base_url: "", api_key: "", model_name: "", protocol: "openai", purpose: "all" });
  const [theme, setTheme] = useState(() => localStorage.getItem("nexus-theme") || "light");
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [searchRunning, setSearchRunning] = useState<boolean | null>(null);
  const { name: appName, isDefault } = useAppName();
  const [editingName, setEditingName] = useState(appName);

  // 自定义配色方案
  const [customThemes, setCustomThemes] = useState<Array<{name: string; primary: string; accent: string; bgStart: string; bgEnd: string}>>([]);
  const [editingTheme, setEditingTheme] = useState<number | null>(null);

  // 自动更新状态
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);

  // 检查更新（通过 GitHub API，跨平台通用）
  const checkForUpdate = async () => {
    setCheckingUpdate(true);
    setUpdateError(null);
    try {
      const resp = await fetch("https://api.github.com/repos/chenjingwei/AI-Nexus-Assistant/releases/latest");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const latestVer = (data.tag_name as string).replace("v", "");
      const currentVer = "4.0.1"; // 与 tauri.conf.json version 一致
      const available = compareVersions(latestVer, currentVer) > 0;
      setUpdateInfo({
        version: latestVer,
        notes: data.body || "无更新说明",
        available,
      });
    } catch (err: any) {
      setUpdateError(err.message || "检查更新失败");
    }
    setCheckingUpdate(false);
  };

  // 语义化版本比较
  const compareVersions = (a: string, b: string): number => {
    const pa = a.split(".").map(Number);
    const pb = b.split(".").map(Number);
    for (let i = 0; i < 3; i++) {
      if ((pa[i] || 0) > (pb[i] || 0)) return 1;
      if ((pa[i] || 0) < (pb[i] || 0)) return -1;
    }
    return 0;
  };

  // 尝试使用 Tauri 原生 updater（仅桌面端生效）
  const nativeUpdate = async () => {
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const { relaunch } = await import("@tauri-apps/plugin-process");
      const update = await check();
      if (update) {
        setUpdateInfo({
          version: update.version,
          notes: update.body || "无更新说明",
          available: true,
          downloading: false,
          progress: 0,
        });
        setUpdateInfo(prev => prev ? { ...prev, downloading: true } : null);
        await update.downloadAndInstall((progress) => {
          if (progress.event === "Started" && progress.data.contentLength) {
            setUpdateInfo(prev => prev ? { ...prev, progress: 0 } : null);
          } else if (progress.event === "Progress" && progress.data.chunkLength) {
            setUpdateInfo(prev => {
              if (!prev) return null;
              const newProgress = (prev.progress || 0) + progress.data.chunkLength;
              return { ...prev, progress: newProgress };
            });
          }
        });
        setUpdateInfo(prev => prev ? { ...prev, downloading: false } : null);
        await relaunch();
      } else {
        setUpdateInfo({ version: "", notes: "", available: false });
      }
    } catch {
      // 非 Tauri 环境（浏览器开发模式），回退到 GitHub API
      await checkForUpdate();
    }
  };

  useEffect(() => {
    try {
      const saved = localStorage.getItem("nexus-custom-themes");
      if (saved) setCustomThemes(JSON.parse(saved));
    } catch {}
  }, []);

  const saveCustomThemes = (themes: typeof customThemes) => {
    setCustomThemes(themes);
    localStorage.setItem("nexus-custom-themes", JSON.stringify(themes));
  };

  const applyCustomTheme = (idx: number) => {
    const t = customThemes[idx];
    if (!t) return;
    const root = document.documentElement;
    root.setAttribute("data-theme", `custom-${idx + 1}`);
    root.style.setProperty("--accent-blue", t.primary);
    root.style.setProperty("--accent-green", t.accent);
    root.style.setProperty("--bg-gradient", `linear-gradient(135deg, ${t.bgStart} 0%, ${t.bgEnd} 100%)`);
    localStorage.setItem("nexus-theme", `custom-${idx + 1}`);
    setTheme(`custom-${idx + 1}`);
  };

  const addCustomTheme = () => {
    if (customThemes.length >= 3) return;
    const newTheme = { name: `Custom ${customThemes.length + 1}`, primary: "#3b82f6", accent: "#10b981", bgStart: "#f8fafc", bgEnd: "#f1f5f9" };
    saveCustomThemes([...customThemes, newTheme]);
    setEditingTheme(customThemes.length);
  };

  const updateCustomTheme = (idx: number, field: string, value: string) => {
    const updated = [...customThemes];
    (updated[idx] as any)[field] = value;
    saveCustomThemes(updated);
  };

  const deleteCustomTheme = (idx: number) => {
    const updated = customThemes.filter((_, i) => i !== idx);
    saveCustomThemes(updated);
    if (editingTheme === idx) setEditingTheme(null);
  };

  useEffect(() => {
    modelsApi.list().then(setModels).catch(console.error);
    loadBackups();
    loadSearchStatus();
  }, []);

  // 同步 appName 变化到 editingName
  useEffect(() => {
    setEditingName(appName);
  }, [appName]);

  const loadModels = () => modelsApi.list().then(setModels).catch(console.error);
  const loadBackups = () => fetch("http://127.0.0.1:8765/api/backups").then(r => r.json()).then(setBackups).catch(() => {});
  const loadSearchStatus = () => fetch("http://127.0.0.1:8765/api/search-service/status").then(r => r.json()).then(d => setSearchRunning(d.running)).catch(() => setSearchRunning(null));

  const handleSaveModel = async () => {
    if (!form.name || !form.base_url || !form.model_name) return;
    // 新建时 api_key 必填
    if (!editingId && !form.api_key) {
      alert("请输入 API Key");
      return;
    }
    if (editingId) {
      const updateData: Record<string, string> = {
        name: form.name, base_url: form.base_url,
        model_name: form.model_name, protocol: form.protocol, purpose: form.purpose,
      };
      if (form.api_key) updateData.api_key = form.api_key;
      await modelsApi.update(editingId, updateData);
    } else {
      await modelsApi.create(form);
    }
    setShowForm(false);
    setEditingId(null);
    setForm({ name: "", base_url: "", api_key: "", model_name: "", protocol: "openai", purpose: "all" });
    loadModels();
  };

  const handleEdit = (m: ModelConfig) => {
    setEditingId(m.id);
    setForm({ name: m.name, base_url: m.base_url, api_key: "", model_name: m.model_name, protocol: m.protocol, purpose: m.purpose });
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此模型？")) return;
    await modelsApi.delete(id);
    loadModels();
  };

  const handleThemeChange = (t: string) => {
    setTheme(t);
    localStorage.setItem("nexus-theme", t);
    document.documentElement.setAttribute("data-theme", t);
  };

  const handleRestore = async (path: string) => {
    if (!confirm("确定要恢复到此备份？当前数据将被覆盖（恢复前会自动备份当前数据）。")) return;
    try {
      const res = await fetch("http://127.0.0.1:8765/api/backups/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      const result = await res.json();
      if (result.ok) {
        alert("恢复成功！请重启应用以加载恢复的数据。");
        loadBackups();
      } else {
        alert("恢复失败");
      }
    } catch (err) {
      alert(`恢复失败: ${err}`);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const getBackupLabel = (name: string) => {
    if (name.includes("manual")) return "手动备份";
    if (name.includes("daily")) return "每日备份";
    if (name.includes("weekly")) return "每周备份";
    if (name.includes("monthly")) return "每月备份";
    if (name.includes("before_restore")) return "恢复前备份";
    return "备份";
  };

  return (
    <div className="max-w-3xl space-y-6">
      <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>设置</h2>

      {/* AI 模型 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>AI 模型配置</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b" style={{ color: "var(--text-muted)", borderColor: "var(--border-color)" }}>
                <th className="py-2 font-medium">名称</th>
                <th className="font-medium">模型</th>
                <th className="font-medium">协议</th>
                <th className="font-medium">用途</th>
                <th className="font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {models.map(m => (
                <tr key={m.id} className="border-b" style={{ borderColor: "var(--border-color)" }}>
                  <td className="py-2.5" style={{ color: "var(--text-primary)" }}>{m.name}</td>
                  <td style={{ color: "var(--text-secondary)" }}>{m.model_name}</td>
                  <td>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
                      {m.protocol}
                    </span>
                  </td>
                  <td style={{ color: "var(--text-secondary)" }}>{m.purpose}</td>
                  <td>
                    <div className="flex gap-2 items-center">
                      <button onClick={() => handleEdit(m)}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium cursor-pointer transition-colors"
                        style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "rgba(59,130,246,0.2)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "rgba(59,130,246,0.1)")}
                      >编辑</button>
                      <button onClick={() => handleDelete(m.id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium cursor-pointer transition-colors"
                        style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "rgba(239,68,68,0.15)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "rgba(239,68,68,0.08)")}
                      >删除</button>
                    </div>
                  </td>
                </tr>
              ))}
              {models.length === 0 && (
                <tr><td colSpan={5} className="py-4 text-center text-sm" style={{ color: "var(--text-muted)" }}>暂无模型配置</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {showForm && (
          <div className="p-4 rounded-xl space-y-3" style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
            <div className="grid grid-cols-2 gap-3">
              <input className="input-glass" placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              <input className="input-glass" placeholder="模型名 (如 deepseek-reasoner)" value={form.model_name} onChange={e => setForm({ ...form, model_name: e.target.value })} />
              <input className="input-glass col-span-2" placeholder="Base URL (如 https://api.deepseek.com/v1)" value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} />
              <input className="input-glass col-span-2" type="password" placeholder={editingId ? "留空表示保留原密钥" : "API Key（必填）"} value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} />
              <select className="input-glass" value={form.protocol} onChange={e => setForm({ ...form, protocol: e.target.value })}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
              </select>
              <select className="input-glass" value={form.purpose} onChange={e => setForm({ ...form, purpose: e.target.value })}>
                <option value="all">通用</option>
                <option value="summary">总结</option>
                <option value="review">综述</option>
                <option value="chat">对话</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button className="btn-gradient btn-click" onClick={handleSaveModel}>{editingId ? "保存修改" : "添加"}</button>
              <button className="btn-ghost" onClick={() => { setShowForm(false); setEditingId(null); }}>取消</button>
            </div>
          </div>
        )}

        {!showForm && (
          <button className="btn-gradient btn-click" onClick={() => { setShowForm(true); setEditingId(null); setForm({ name: "", base_url: "", api_key: "", model_name: "", protocol: "openai", purpose: "all" }); }}>
            添加模型
          </button>
        )}
      </div>

      {/* 个性化 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>个性化</h3>
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium mb-2" style={{ color: "var(--text-secondary)" }}>应用名称</p>
            <div className="flex gap-2 items-center">
              <input
                className="input-glass text-sm flex-1 max-w-xs"
                placeholder="输入自定义名称..."
                value={editingName}
                onChange={e => setEditingName(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { setAppName(editingName); } }}
                maxLength={20}
              />
              <button className="btn-ghost text-xs py-2" onClick={() => setAppName(editingName)}>
                保存
              </button>
              {!isDefault && (
                <button className="text-xs cursor-pointer transition-colors" style={{ color: "var(--text-muted)" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                  onClick={() => { resetAppName(); setEditingName("NEXUS"); }}>
                  恢复默认
                </button>
              )}
            </div>
            <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
              当前显示名称：<span style={{ color: "var(--accent-blue)" }}>{appName}</span>
              {isDefault ? "（默认）" : ""}
            </p>
          </div>
        </div>
      </div>

      {/* 主题 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>主题</h3>
        <div className="flex gap-3">
          <button
            onClick={() => handleThemeChange("light")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${theme === "light" ? "bg-primary-500 text-white" : ""}`}
            style={theme !== "light" ? { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" } : {}}
          >浅色</button>
          <button
            onClick={() => handleThemeChange("warm")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${theme === "warm" ? "text-white" : ""}`}
            style={theme === "warm" ? { background: "#E07A5F" } : { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" }}
          >暖色</button>
          <button
            onClick={() => handleThemeChange("dark")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${theme === "dark" ? "bg-primary-500 text-white" : ""}`}
            style={theme !== "dark" ? { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" } : {}}
          >深色</button>
        </div>

        {/* 自定义配色方案 */}
        <div className="pt-3 space-y-3" style={{ borderTop: "1px solid var(--border-color)" }}>
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>自定义配色方案</p>
            {customThemes.length < 3 && (
              <button className="text-xs cursor-pointer flex items-center gap-1" style={{ color: "var(--accent-blue)" }}
                onClick={addCustomTheme}>+ 添加方案</button>
            )}
          </div>
          {customThemes.map((ct, i) => (
            <div key={i} className="p-3 rounded-xl space-y-2" style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full" style={{ background: ct.primary }} />
                  <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{ct.name}</span>
                </div>
                <div className="flex gap-1">
                  <button className="text-[10px] px-2 py-1 rounded cursor-pointer"
                    style={{ background: "var(--accent-blue)", color: "#fff" }}
                    onClick={() => applyCustomTheme(i)}>应用</button>
                  <button className="text-[10px] px-2 py-1 rounded cursor-pointer"
                    style={{ color: "var(--text-muted)" }}
                    onClick={() => setEditingTheme(editingTheme === i ? null : i)}>
                    {editingTheme === i ? "收起" : "编辑"}
                  </button>
                  <button className="text-[10px] px-2 py-1 rounded cursor-pointer"
                    style={{ color: "#ef4444" }}
                    onClick={() => deleteCustomTheme(i)}>删除</button>
                </div>
              </div>
              {editingTheme === i && (
                <div className="grid grid-cols-2 gap-2 pt-2">
                  <div>
                    <label className="text-[10px]" style={{ color: "var(--text-muted)" }}>名称</label>
                    <input className="input-glass text-xs mt-1" value={ct.name}
                      onChange={(e) => updateCustomTheme(i, "name", e.target.value)} />
                  </div>
                  <div>
                    <label className="text-[10px]" style={{ color: "var(--text-muted)" }}>主色调</label>
                    <div className="flex gap-1 items-center mt-1">
                      <input type="color" value={ct.primary} className="w-6 h-6 rounded cursor-pointer border-none"
                        onChange={(e) => updateCustomTheme(i, "primary", e.target.value)} />
                      <input className="input-glass text-xs flex-1" value={ct.primary}
                        onChange={(e) => updateCustomTheme(i, "primary", e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px]" style={{ color: "var(--text-muted)" }}>强调色</label>
                    <div className="flex gap-1 items-center mt-1">
                      <input type="color" value={ct.accent} className="w-6 h-6 rounded cursor-pointer border-none"
                        onChange={(e) => updateCustomTheme(i, "accent", e.target.value)} />
                      <input className="input-glass text-xs flex-1" value={ct.accent}
                        onChange={(e) => updateCustomTheme(i, "accent", e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px]" style={{ color: "var(--text-muted)" }}>背景渐变</label>
                    <div className="flex gap-1 items-center mt-1">
                      <input type="color" value={ct.bgStart} className="w-6 h-6 rounded cursor-pointer border-none"
                        onChange={(e) => updateCustomTheme(i, "bgStart", e.target.value)} />
                      <input type="color" value={ct.bgEnd} className="w-6 h-6 rounded cursor-pointer border-none"
                        onChange={(e) => updateCustomTheme(i, "bgEnd", e.target.value)} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
          {customThemes.length === 0 && (
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>最多保存 3 种自定义配色方案</p>
          )}
        </div>
      </div>

      {/* 联网搜索服务 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>联网搜索服务</h3>
        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
          AI 对话中使用联网搜索需要 open-webSearch 服务运行（需要 Node.js）
        </p>
        <div className="flex items-center gap-3">
          <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
            状态：
            {searchRunning === null ? "检测中..." :
              searchRunning ?
                <span style={{ color: "var(--accent-green)" }}>运行中</span> :
                <span style={{ color: "#ef4444" }}>未启动</span>}
          </span>
          <button className="btn-ghost text-xs" onClick={loadSearchStatus}>刷新</button>
          {searchRunning ? (
            <button className="btn-ghost text-xs"
              style={{ color: "#ef4444" }}
              onClick={async () => {
                try {
                  await fetch("http://127.0.0.1:8765/api/search-service/stop", { method: "POST" });
                  loadSearchStatus();
                } catch (err) { alert(`停止失败: ${err}`); }
              }}
            >停止服务</button>
          ) : (
            <button className="btn-gradient btn-click text-xs"
              onClick={async () => {
                try {
                  const res = await fetch("http://127.0.0.1:8765/api/search-service/start", { method: "POST" });
                  const data = await res.json();
                  loadSearchStatus();
                  if (!data.ok) {
                    const errMsg = data.error || "未知错误";
                    alert(`启动失败：${errMsg}\n\n请确保：\n1. Node.js 已安装（https://nodejs.org）\n2. 安装后重启应用\n3. 检查系统 PATH 环境变量包含 Node.js 路径`);
                  }
                } catch (err) { alert(`启动失败: ${err}\n\n请确认后端服务正在运行`); }
              }}
            >启动服务</button>
          )}
        </div>

        {/* open-webSearch 配置指南 */}
        <details className="text-xs" style={{ color: "var(--text-secondary)" }}>
          <summary className="cursor-pointer font-medium" style={{ color: "var(--accent-blue)" }}>📖 配置指南</summary>
          <div className="mt-3 space-y-3 pl-3 border-l-2" style={{ borderColor: "var(--border-color)" }}>
            <div>
              <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>便携版 (Portable)</p>
              <ol className="list-decimal pl-4 space-y-1">
                <li>下载安装 <a href="https://nodejs.org" target="_blank" className="underline" style={{ color: "var(--accent-blue)" }}>Node.js</a> (推荐 LTS 版本)</li>
                <li>安装完成后<strong>重启应用</strong></li>
                <li>点击上方「启动服务」按钮</li>
                <li>如果仍无法启动，检查系统 PATH 是否包含 Node.js 路径</li>
              </ol>
            </div>
            <div>
              <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>安装程序版 (Installer)</p>
              <ol className="list-decimal pl-4 space-y-1">
                <li>安装程序会自动检测 Node.js</li>
                <li>如未安装，会提示下载安装</li>
                <li>安装 Node.js 后重启应用即可</li>
              </ol>
            </div>
            <div>
              <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>常见问题</p>
              <ul className="list-disc pl-4 space-y-1">
                <li>启动失败：确保 Node.js 已安装且在 PATH 中</li>
                <li>搜索超时：网络环境可能导致搜索较慢，请耐心等待</li>
                <li>服务端口被占用：默认端口 3210，如有冲突请重启应用</li>
              </ul>
            </div>
          </div>
        </details>
      </div>

      {/* v3.6.0: MinerU PDF 转换 */}
      <MinerUSection />

      {/* 应用更新 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>应用更新</h3>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          检查 GitHub Release 获取最新版本。桌面端支持自动下载安装，移动端请前往应用商店更新。
        </p>
        <div className="flex items-center gap-3">
          <button className="btn-gradient btn-click text-xs" disabled={checkingUpdate}
            onClick={nativeUpdate}
          >
            {checkingUpdate ? "检查中..." : "检查更新"}
          </button>
          <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
            当前版本: v4.0.1
          </span>
        </div>

        {updateError && (
          <div className="text-xs p-3 rounded-lg" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
            ❌ {updateError}
          </div>
        )}

        {updateInfo && !updateInfo.available && !updateError && (
          <div className="text-xs p-3 rounded-lg" style={{ background: "rgba(16,185,129,0.1)", color: "var(--accent-green)" }}>
            ✅ 已是最新版本
          </div>
        )}

        {updateInfo && updateInfo.available && (
          <div className="space-y-3 p-4 rounded-lg" style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                🆕 新版本 v{updateInfo.version} 可用
              </span>
            </div>
            <div className="text-xs max-h-32 overflow-y-auto whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>
              {updateInfo.notes}
            </div>
            {updateInfo.downloading ? (
              <div className="space-y-1">
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>下载中...</div>
                <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: "var(--border-color)" }}>
                  <div className="h-full rounded-full transition-all" style={{ background: "var(--accent-blue)", width: updateInfo.progress ? `${Math.min(100, updateInfo.progress)}%` : "0%" }} />
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <button className="btn-gradient btn-click text-xs"
                  onClick={async () => {
                    try {
                      const { check } = await import("@tauri-apps/plugin-updater");
                      const { relaunch } = await import("@tauri-apps/plugin-process");
                      const update = await check();
                      if (update) {
                        setUpdateInfo(prev => prev ? { ...prev, downloading: true } : null);
                        await update.downloadAndInstall();
                        setUpdateInfo(prev => prev ? { ...prev, downloading: false } : null);
                        await relaunch();
                      }
                    } catch {
                      // 非 Tauri 环境，打开浏览器下载
                      window.open(`https://github.com/chenjingwei/AI-Nexus-Assistant/releases/latest`, "_blank");
                    }
                  }}
                >
                  {typeof window !== "undefined" && "__TAURI_INTERNALS__" in window ? "自动更新" : "前往下载"}
                </button>
                <button className="btn-ghost text-xs" onClick={() => setUpdateInfo(null)}>忽略</button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 数据管理 */}
      <div className="glass-card p-5 space-y-4">
        <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>数据管理</h3>
        <div className="flex gap-3 flex-wrap">
          <button className="btn-ghost"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".json";
              input.onchange = async (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (!file) return;
                const text = await file.text();
                try {
                  const data = JSON.parse(text);
                  const res = await fetch("http://127.0.0.1:8765/api/knowledge/import/json", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data),
                  });
                  const result = await res.json();
                  alert(`导入完成: ${JSON.stringify(result)}`);
                } catch (err) {
                  alert(`导入失败: ${err}`);
                }
              };
              input.click();
            }}
          >导入 JSON</button>
          <button className="btn-ghost"
            onClick={async () => {
              try {
                const res = await fetch("http://127.0.0.1:8765/api/backup", { method: "POST" });
                const result = await res.json();
                alert(`备份完成: ${result.path || "成功"}`);
                loadBackups();
              } catch (err) {
                alert(`备份失败: ${err}`);
              }
            }}
          >手动备份</button>
          <button className="btn-ghost"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".db,.zip";
              input.onchange = async (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (!file) return;
                if (!confirm(`确定要从 "${file.name}" 恢复数据吗？当前数据将被覆盖（恢复前会自动备份）。`)) return;
                try {
                  const bytes = await file.arrayBuffer();
                  const res = await fetch("http://127.0.0.1:8765/api/backups/import-db", {
                    method: "POST",
                    headers: { "Content-Type": "application/octet-stream" },
                    body: bytes,
                  });
                  const result = await res.json();
                  if (result.ok) {
                    alert("恢复成功！请重启应用以加载恢复的数据。");
                    loadBackups();
                  } else {
                    alert("恢复失败: " + (result.detail || "未知错误"));
                  }
                } catch (err) {
                  alert(`恢复失败: ${err}`);
                }
              };
              input.click();
            }}
          >导入 .db/.zip 恢复</button>
          <button className="btn-ghost"
            onClick={async () => {
              try {
                const res = await fetch("http://127.0.0.1:8765/api/backups/export-db");
                if (!res.ok) { alert("导出失败"); return; }
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `nexus_backup_${new Date().toISOString().slice(0,10)}.zip`;
                a.click();
                URL.revokeObjectURL(url);
              } catch (err) {
                alert(`导出失败: ${err}`);
              }
            }}
          >导出数据 (.zip)</button>
        </div>

        {/* 备份列表 */}
        {backups.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>历史备份 ({backups.length})</p>
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {backups.map(b => (
                <div key={b.path}
                  className="flex items-center justify-between px-3 py-2 rounded-lg text-xs"
                  style={{ background: "var(--hover-bg)", border: "1px solid var(--border-color)" }}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{
                          background: b.name.includes("manual") ? "rgba(59,130,246,0.1)" :
                                     b.name.includes("monthly") ? "rgba(16,185,129,0.1)" :
                                     b.name.includes("weekly") ? "rgba(245,158,11,0.1)" : "rgba(107,114,128,0.1)",
                          color: b.name.includes("manual") ? "var(--accent-blue)" :
                                 b.name.includes("monthly") ? "var(--accent-green)" :
                                 b.name.includes("weekly") ? "#f59e0b" : "var(--text-muted)"
                        }}
                      >{getBackupLabel(b.name)}</span>
                      <span style={{ color: "var(--text-secondary)" }}>{formatSize(b.size)}</span>
                    </div>
                    <p className="mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>{b.time}</p>
                  </div>
                  <button
                    onClick={() => handleRestore(b.path)}
                    className="ml-3 px-2.5 py-1 rounded-lg text-xs font-medium cursor-pointer transition-colors flex-shrink-0"
                    style={{ background: "rgba(16,185,129,0.1)", color: "var(--accent-green)" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(16,185,129,0.2)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "rgba(16,185,129,0.1)")}
                  >恢复</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// v3.6.0: MinerU PDF 转换组件
function MinerUSection() {
  const [status, setStatus] = useState<{ available: boolean; version: string }>({ available: false, version: "" });
  const [loading, setLoading] = useState(false);

  const checkStatus = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8765/api/system/mineru-status");
      const data = await res.json();
      setStatus(data);
    } catch {}
  };

  useEffect(() => { checkStatus(); }, []);

  return (
    <div className="glass-card p-5 space-y-3">
      <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>PDF 转换引擎 (MinerU)</h3>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        MinerU 可将 PDF 高质量转换为 Markdown，保留公式、图片和表格。安装后 LLM 阅读论文效果显著提升。约需 2GB 磁盘空间。
      </p>
      <div className="flex items-center gap-3">
        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>状态:</span>
        {status.available ? (
          <span className="text-xs" style={{ color: "var(--accent-green)" }}>✅ 已安装 {status.version && `v${status.version}`}</span>
        ) : (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>❌ 未安装（当前使用 PyMuPDF 降级方案）</span>
        )}
        <button className="btn-ghost text-xs" onClick={checkStatus}>刷新</button>
        {!status.available && (
          <button className="btn-gradient btn-click text-xs" disabled={loading}
            onClick={async () => {
              if (!confirm("确定安装 MinerU？需要约 2GB 磁盘空间，安装过程可能需要几分钟。")) return;
              setLoading(true);
              try {
                const res = await fetch("http://127.0.0.1:8765/api/system/install-mineru", { method: "POST" });
                const reader = res.body?.getReader();
                if (reader) {
                  while (true) {
                    const { done } = await reader.read();
                    if (done) break;
                  }
                }
                alert("MinerU 安装完成！");
                checkStatus();
              } catch (err) {
                alert(`安装失败: ${err}`);
              }
              setLoading(false);
            }}
          >{loading ? "安装中..." : "安装 MinerU"}</button>
        )}
      </div>

      {/* MinerU 配置指南 */}
      <details className="text-xs" style={{ color: "var(--text-secondary)" }}>
        <summary className="cursor-pointer font-medium" style={{ color: "var(--accent-blue)" }}>📖 配置指南</summary>
        <div className="mt-3 space-y-3 pl-3 border-l-2" style={{ borderColor: "var(--border-color)" }}>
          <div>
            <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>便携版 (Portable)</p>
            <ol className="list-decimal pl-4 space-y-1">
              <li>确保已安装 Python 3.8+ 并在 PATH 中</li>
              <li>点击上方「安装 MinerU」按钮</li>
              <li>安装过程需要下载约 2GB 依赖，请耐心等待</li>
              <li>安装完成后状态会自动更新为「已安装」</li>
            </ol>
          </div>
          <div>
            <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>安装程序版 (Installer)</p>
            <ol className="list-decimal pl-4 space-y-1">
              <li>安装程序已内置 Python 环境</li>
              <li>点击「安装 MinerU」即可自动配置</li>
              <li>如遇权限问题，请以管理员身份运行应用</li>
            </ol>
          </div>
          <div>
            <p className="font-medium mb-1" style={{ color: "var(--text-primary)" }}>常见问题</p>
            <ul className="list-disc pl-4 space-y-1">
              <li>安装失败：检查网络连接，或尝试手动安装 <code>pip install magic-pdf</code></li>
              <li>转换效果差：MinerU 对扫描版 PDF 效果有限，建议使用文字版 PDF</li>
              <li>占用空间大：MinerU 依赖约 2GB，可在不使用时卸载释放空间</li>
            </ul>
          </div>
        </div>
      </details>
    </div>
  );
}
