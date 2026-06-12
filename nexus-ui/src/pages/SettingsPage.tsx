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
    await modelsApi.create(form);
    setShowForm(false);
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
    if (t === "dark") {
      document.documentElement.style.setProperty("--bg-gradient", "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)");
      document.documentElement.style.setProperty("--glass-bg", "rgba(30, 41, 59, 0.7)");
      document.documentElement.style.setProperty("--text-primary", "#e2e8f0");
    } else {
      document.documentElement.style.setProperty("--bg-gradient", "linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%)");
      document.documentElement.style.setProperty("--glass-bg", "rgba(255, 255, 255, 0.7)");
      document.documentElement.style.setProperty("--text-primary", "#1e293b");
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">设置</h2>

      {/* AI 模型 */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold text-slate-700">AI 模型配置</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-200">
              <th className="py-2">名称</th><th>模型</th><th>协议</th><th>用途</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {models.map(m => (
              <tr key={m.id} className="border-b border-slate-100">
                <td className="py-3 text-slate-700">{m.name}</td>
                <td className="text-slate-500">{m.model_name}</td>
                <td><span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 text-xs">{m.protocol}</span></td>
                <td className="text-slate-500">{m.purpose}</td>
                <td className="flex gap-2">
                  <button onClick={() => handleEdit(m)} className="text-xs text-primary-500 hover:underline">编辑</button>
                  <button onClick={() => handleDelete(m.id)} className="text-xs text-red-400 hover:text-red-600">删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {showForm && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input className="input-glass" placeholder="名称" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              <input className="input-glass" placeholder="模型名 (如 deepseek-reasoner)" value={form.model_name} onChange={e => setForm({ ...form, model_name: e.target.value })} />
              <input className="input-glass col-span-2" placeholder="Base URL (如 https://api.deepseek.com/v1)" value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} />
              <input className="input-glass col-span-2" type="password" placeholder="API Key" value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} />
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
              <button className="px-4 py-2 rounded-xl text-sm text-slate-500 hover:bg-slate-100" onClick={() => { setShowForm(false); setEditingId(null); }}>取消</button>
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
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold text-slate-700">主题</h3>
        <div className="flex gap-3">
          <button
            onClick={() => handleThemeChange("light")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${theme === "light" ? "bg-primary-500 text-white" : "bg-slate-100 text-slate-600"}`}
          >浅色</button>
          <button
            onClick={() => handleThemeChange("dark")}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${theme === "dark" ? "bg-primary-500 text-white" : "bg-slate-100 text-slate-600"}`}
          >深色</button>
        </div>
      </div>

      {/* 数据管理 */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold text-slate-700">数据管理</h3>
        <div className="flex gap-3 flex-wrap">
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
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
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
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
