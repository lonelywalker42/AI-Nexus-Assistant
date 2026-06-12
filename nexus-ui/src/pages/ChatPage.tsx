import { useState } from "react";

export default function ChatPage() {
  const [input, setInput] = useState("");

  return (
    <div className="flex gap-4 h-full">
      {/* 左侧会话列表 */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-3">
        <div className="glass-card p-4 space-y-3">
          <p className="text-xs text-slate-400 font-medium">模型</p>
          <select className="input-glass text-sm">
            <option>DeepSeek-R1</option>
            <option>mimo-v2-flash</option>
          </select>
        </div>
        <button className="btn-gradient btn-click">新建对话</button>
        <div className="flex-1 space-y-2 overflow-y-auto">
          <SessionItem title="PINN 方法讨论" active />
          <SessionItem title="论文润色" />
          <SessionItem title="试验数据分析" />
        </div>
      </div>

      {/* 右侧对话区 */}
      <div className="flex-1 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-slate-800">PINN 方法讨论</h2>

        {/* 消息区 */}
        <div className="flex-1 space-y-4 overflow-y-auto">
          <Message role="user" content="帮我分析一下 PINN 在飞行控制领域的应用现状" />
          <Message role="ai" content={`## PINN 在飞行控制领域的应用

### 1. 研究现状
Physics-Informed Neural Networks (PINN) 近年来在飞行控制领域得到了广泛关注...

### 2. 关键技术
- **损失函数设计**: 将 Navier-Stokes 方程作为约束
- **网络架构**: 多层感知机 + 残差连接

### 3. 挑战
- 训练不稳定
- 多任务损失权重平衡`} />
        </div>

        {/* 输入区 */}
        <div className="glass-card p-3 flex gap-3">
          <textarea
            className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-slate-700 placeholder-slate-400"
            placeholder="输入消息... (Enter 发送)"
            rows={2}
            value={input}
            onChange={e => setInput(e.target.value)}
          />
          <button className="btn-gradient btn-click self-end">发送</button>
        </div>
      </div>
    </div>
  );
}

function SessionItem({ title, active }: { title: string; active?: boolean }) {
  return (
    <div className={`p-3 rounded-xl text-sm cursor-pointer transition-all ${active ? 'bg-primary-50 text-primary-600 font-medium' : 'text-slate-500 hover:bg-slate-100/60'}`}>
      {title}
    </div>
  );
}

function Message({ role, content }: { role: string; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${isUser ? "bg-primary-500 text-white" : "glass-card"}`}>
        <p className="text-xs font-semibold mb-1 opacity-70">{isUser ? "You" : "AI"}</p>
        {isUser ? (
          <p className="text-sm">{content}</p>
        ) : (
          <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: simpleMarkdown(content) }} />
        )}
      </div>
    </div>
  );
}

function simpleMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}
