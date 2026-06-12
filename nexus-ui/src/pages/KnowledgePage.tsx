export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-800">知识库</h2>
        <button className="btn-gradient btn-click">新建卡片</button>
      </div>

      <div className="flex gap-3">
        <input className="input-glass flex-1" placeholder="搜索知识卡片..." />
        <select className="input-glass w-40">
          <option>全部来源</option>
          <option>手动创建</option>
          <option>文献导入</option>
          <option>AI 对话</option>
        </select>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <KnowledgeCard title="PINN 基础原理" summary="物理信息神经网络将物理方程嵌入损失函数..." source="literature" stars={4} />
        <KnowledgeCard title="飞行控制 PID 调参" summary="PID 参数整定的 Ziegler-Nichols 方法..." source="manual" stars={3} />
        <KnowledgeCard title="DeepSeek 对话摘要" summary="关于强化学习在无人机控制中的应用讨论..." source="deepseek" stars={0} />
      </div>
    </div>
  );
}

function KnowledgeCard({ title, summary, source, stars }: { title: string; summary: string; source: string; stars: number }) {
  const badges: Record<string, { text: string; color: string }> = {
    manual: { text: "手动", color: "bg-slate-100 text-slate-600" },
    literature: { text: "文献", color: "bg-blue-50 text-blue-600" },
    deepseek: { text: "AI", color: "bg-purple-50 text-purple-600" },
  };
  const badge = badges[source] || badges.manual;
  return (
    <div className="glass-card p-5 space-y-3 cursor-pointer">
      <div className="flex items-center justify-between">
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${badge.color}`}>{badge.text}</span>
        <span className="text-amber-400 text-xs">{"★".repeat(stars)}{"☆".repeat(5 - stars)}</span>
      </div>
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-500 line-clamp-2">{summary}</p>
    </div>
  );
}
