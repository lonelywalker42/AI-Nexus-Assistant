export default function SettingsPage() {
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
            <tr className="border-b border-slate-100">
              <td className="py-3 text-slate-700">DeepSeek-R1</td>
              <td className="text-slate-500">deepseek-reasoner</td>
              <td><span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 text-xs">openai</span></td>
              <td className="text-slate-500">all</td>
              <td><button className="text-xs text-primary-500 hover:underline">编辑</button></td>
            </tr>
          </tbody>
        </table>
        <button className="btn-gradient btn-click">添加模型</button>
      </div>

      {/* 主题 */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold text-slate-700">主题</h3>
        <div className="flex gap-3">
          <button className="px-4 py-2 rounded-xl bg-primary-500 text-white text-sm font-medium">浅色</button>
          <button className="px-4 py-2 rounded-xl bg-slate-100 text-slate-600 text-sm">深色</button>
        </div>
      </div>

      {/* 数据管理 */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-lg font-semibold text-slate-700">数据管理</h3>
        <div className="flex gap-3 flex-wrap">
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors">导入 ai-literature JSON</button>
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors">导入 DeepSeek 对话</button>
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors">导入 PDF</button>
          <button className="px-4 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors">手动备份</button>
        </div>
      </div>
    </div>
  );
}
