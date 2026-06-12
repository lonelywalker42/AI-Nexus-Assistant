import { useEffect, useState, useRef } from "react";
import { chatApi, modelsApi, type ChatSession, type ChatMessage, type ModelConfig } from "../api/client";

function renderMarkdown(md: string): string {
  if (!md) return "";

  // 保护代码块不被后续规则影响
  const codeBlocks: string[] = [];
  let result = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="lang-${lang}">${escapeHtml(code.trim())}</code></pre>`);
    return `__CODEBLOCK_${idx}__`;
  });

  // 表格
  result = result.replace(
    /(?:^|\n)(\|.+\|)\n(\|[-| :]+\|)\n((?:\|.+\|\n?)+)/g,
    (_, header, _sep, body) => {
      const ths = header.split("|").filter((c: string) => c.trim()).map((c: string) => `<th>${c.trim()}</th>`).join("");
      const rows = body.trim().split("\n").map((row: string) => {
        const tds = row.split("|").filter((c: string) => c.trim()).map((c: string) => `<td>${c.trim()}</td>`).join("");
        return `<tr>${tds}</tr>`;
      }).join("");
      return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
    }
  );

  // 标题
  result = result.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 粗体/斜体
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 行内代码
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');

  // LaTeX 公式（行内 $...$ 和块 $$...$$）
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, '<div class="math-block">$$1$$</div>');
  result = result.replace(/\$([^$\n]+?)\$/g, '<span class="math-inline">$$$1$$</span>');

  // 列表
  result = result.replace(/^- (.+)$/gm, '<li>$1</li>');
  result = result.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  result = result.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);

  // 引用
  result = result.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

  // 链接
  result = result.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');

  // 分割线
  result = result.replace(/^---$/gm, '<hr>');

  // 段落（双换行）
  result = result.replace(/\n\n/g, '</p><p>');
  result = result.replace(/\n/g, '<br>');

  // 恢复代码块
  result = result.replace(/__CODEBLOCK_(\d+)__/g, (_, idx) => codeBlocks[parseInt(idx)]);

  return result;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [streamThinking, setStreamThinking] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatApi.listSessions().then(setSessions).catch(console.error);
    modelsApi.list().then(setModels).catch(console.error);
  }, []);

  useEffect(() => {
    if (activeSession) {
      chatApi.getMessages(activeSession).then(setMessages).catch(console.error);
    }
  }, [activeSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent]);

  const handleNewSession = async () => {
    const res = await chatApi.createSession();
    setSessions(prev => [{ id: res.id, title: "新对话", model_name: "", created_at: new Date().toISOString() }, ...prev]);
    setActiveSession(res.id);
    setMessages([]);
  };

  const handleDeleteSession = async () => {
    if (!activeSession) return;
    await chatApi.deleteSession(activeSession);
    setSessions(prev => prev.filter(s => s.id !== activeSession));
    setActiveSession(null);
    setMessages([]);
  };

  const handleSend = async () => {
    if (!input.trim() || streaming) return;
    if (!activeSession) {
      await handleNewSession();
    }

    const content = input.trim();
    setInput("");

    // 保存用户消息
    const msg = await chatApi.addMessage(activeSession!, content);
    setMessages(prev => [...prev, msg]);

    // 更新会话标题（首条消息）
    if (messages.length === 0) {
      setSessions(prev => prev.map(s => s.id === activeSession ? { ...s, title: content.slice(0, 30) } : s));
    }

    // 流式 AI 回复
    setStreaming(true);
    setStreamContent("");
    setStreamThinking("");

    try {
      const modelId = models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession!, modelId)) {
        if (chunk.type === "thinking") {
          setStreamThinking(prev => prev + chunk.data);
        } else if (chunk.type === "content") {
          setStreamContent(prev => prev + chunk.data);
        }
      }
    } catch (err) {
      setStreamContent(`错误: ${err}`);
    }

    // 刷新消息列表
    const updated = await chatApi.getMessages(activeSession!);
    setMessages(updated);
    setStreaming(false);
    setStreamContent("");
    setStreamThinking("");
  };

  const currentSession = sessions.find(s => s.id === activeSession);

  return (
    <div className="flex gap-4 h-full">
      {/* 左侧 */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-3">
        <div className="glass-card p-4 space-y-3">
          <p className="text-xs text-slate-400 font-medium">模型</p>
          <select className="input-glass text-sm">
            {models.length ? models.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            )) : <option>未配置模型</option>}
          </select>
        </div>
        <button className="btn-gradient btn-click" onClick={handleNewSession}>新建对话</button>
        <div className="flex-1 space-y-2 overflow-y-auto">
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => setActiveSession(s.id)}
              className={`p-3 rounded-xl text-sm cursor-pointer transition-all ${
                activeSession === s.id ? "bg-primary-50 text-primary-600 font-medium" : "text-slate-500 hover:bg-slate-100/60"
              }`}
            >
              {s.title.slice(0, 20)}
            </div>
          ))}
        </div>
        {activeSession && (
          <button className="text-sm text-red-400 hover:text-red-600 py-2" onClick={handleDeleteSession}>删除当前对话</button>
        )}
      </div>

      {/* 右侧 */}
      <div className="flex-1 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-slate-800">{currentSession?.title || "选择或新建对话"}</h2>

        <div className="flex-1 space-y-4 overflow-y-auto">
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === "user" ? "bg-primary-500 text-white" : "glass-card"
              }`}>
                <p className="text-xs font-semibold mb-1 opacity-70">{msg.role === "user" ? "You" : "AI"}</p>
                {msg.thinking_content && (
                  <details className="mb-2">
                    <summary className="text-xs text-slate-400 cursor-pointer">Thinking...</summary>
                    <p className="text-xs text-slate-500 italic mt-1 whitespace-pre-wrap">{msg.thinking_content}</p>
                  </details>
                )}
                <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
              </div>
            </div>
          ))}

          {/* 流式输出 */}
          {streaming && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-5 py-3 glass-card">
                <p className="text-xs font-semibold mb-1 opacity-70">AI</p>
                {streamThinking && (
                  <details open className="mb-2">
                    <summary className="text-xs text-slate-400 cursor-pointer">Thinking...</summary>
                    <p className="text-xs text-slate-500 italic mt-1 whitespace-pre-wrap">{streamThinking}</p>
                  </details>
                )}
                <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderMarkdown(streamContent || "...") }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 快捷操作 */}
        <div className="flex gap-2 text-xs">
          {["润色", "翻译", "LaTeX", "摘要"].map(label => (
            <button key={label} className="px-3 py-1 rounded-full text-slate-500 hover:bg-slate-100 transition-colors">
              {label}
            </button>
          ))}
          <span className="flex-1" />
          <button className="px-3 py-1 rounded-full text-slate-500 hover:bg-slate-100 transition-colors">存为卡片</button>
        </div>

        {/* 输入区 */}
        <div className="glass-card p-3 flex gap-3">
          <textarea
            className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-slate-700 placeholder-slate-400"
            placeholder="输入消息... (Enter 发送)"
            rows={2}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
          />
          <button className="btn-gradient btn-click self-end" onClick={handleSend} disabled={streaming}>
            {streaming ? "..." : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}
