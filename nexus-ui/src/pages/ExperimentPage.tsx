export default function ExperimentPage() {
  return (
    <div className="flex gap-6 h-full">
      {/* 左侧列表 */}
      <div className="w-72 flex-shrink-0 space-y-3">
        <input className="input-glass" placeholder="搜索试验..." />
        <div className="space-y-2">
          <ExperimentItem title="风洞试验 - 翼型优化" status="running" active />
          <ExperimentItem title="仿真对比 - PID vs LQR" status="completed" />
          <ExperimentItem title="控制律设计 - 自适应" status="planning" />
        </div>
        <button className="btn-gradient btn-click w-full">新建试验</button>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 glass-card p-6 space-y-4">
        <h2 className="text-xl font-bold text-slate-800">风洞试验 - 翼型优化 v3</h2>
        <div className="flex gap-2">
          <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-600 text-xs font-medium">进行中</span>
        </div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div><p className="text-slate-400">背景</p><p className="text-slate-700 mt-1">验证三种翼型在不同攻角下的升阻比</p></div>
          <div><p className="text-slate-400">目标</p><p className="text-slate-700 mt-1">对比 NACA2412 vs 自定义翼型</p></div>
          <div><p className="text-slate-400">状态</p><p className="text-slate-700 mt-1">v3 进行中</p></div>
        </div>
      </div>
    </div>
  );
}

function ExperimentItem({ title, status, active }: { title: string; status: string; active?: boolean }) {
  const colors: Record<string, string> = { planning: "bg-blue-500", running: "bg-amber-500", completed: "bg-emerald-500" };
  return (
    <div className={`glass-card p-3 flex items-center gap-3 cursor-pointer transition-all ${active ? 'ring-2 ring-primary-400' : ''}`}>
      <span className={`w-2 h-2 rounded-full ${colors[status] || "bg-slate-300"}`} />
      <span className="text-sm text-slate-700 truncate">{title}</span>
    </div>
  );
}
