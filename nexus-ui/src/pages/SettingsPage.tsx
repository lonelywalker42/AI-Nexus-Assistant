import { useEffect, useState } from "react";
import { modelsApi, type ModelConfig } from "../api/client";

export default function SettingsPage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", base_url: "", api_key: "", model_name: "", protocol: "openai", purpose: "all" });
  const [theme, setTheme] = useState(() => localStorage.getItem("nexus-theme") || "light");

  useEffect(() => {
    modelsApi.list().then(setModels).catch(console.error);
  }, []);

  const loadModels = () => modelsApi.list().then(setModels).catch(console.error);

  const handleSaveModel = async () => {
    if (!form.name || !form.base_url || !form.model_name) return;
    if (editingId) {
      // 编辑模式：不发送空 api_key（避免覆盖已有密钥）
      const updateData: Record<string, string> = {
        name: form.name,
        base_url: form.base_url,
        model_name: form.model_name,
        protocol: form.protocol,
        purpose: form.purpose,
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
              <input className="input-glass col-span-2" type="password" placeholder={editingId ? "留空表示保留原密钥" : "API Key"} value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} />
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
              } catch (err) {
                alert(`备份失败: ${err}`);
              }
            }}
          >手动备份</button>
        </div>
      </div>
    </div>
  );
}
