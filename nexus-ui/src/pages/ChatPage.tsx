import { useEffect, useState, useRef, useCallback } from "react";
import { chatApi, modelsApi, papersApi, type ChatSession, type ChatMessage, type ModelConfig, type PaperDetail } from "../api/client";

function renderMarkdown(md: string): string {
  if (!md) return "";

  const codeBlocks: string[] = [];
  let result = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre><code class="lang-${lang}">${escapeHtml(code.trim())}</code></pre>`);
    return `__CODEBLOCK_${idx}__`;
  });

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

  result = result.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, '<div class="math-block">$$$$1$$</div>');
  result = result.replace(/\$([^$\n]+?)\$/g, '<span class="math-inline">$$$$1$$</span>');
  result = result.replace(/^- (.+)$/gm, '<li>$1</li>');
  result = result.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  result = result.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  result = result.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  result = result.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
  result = result.replace(/^---$/gm, '<hr>');
  result = result.replace(/\n\n/g, '</p><p>');
  result = result.replace(/\n/g, '<br>');
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

// 写作场景 prompt
const WRITING_PROMPTS: Record<string, string> = {
  polish: "请对以下学术文本进行润色，保持原意的同时提升语言表达的学术性和流畅度。注意：1) 使用准确的学术术语 2) 保持逻辑连贯 3) 避免口语化表达。",
  translate: "请将以下文本翻译为学术英语/中文（根据源语言自动判断方向）。要求：1) 使用准确的学术术语 2) 保持句式地道 3) 专有名词保持一致。",
  latex: "请将以下文本转换为 LaTeX 格式。包括：1) 数学公式转为 $...$ 或 \\[...\\] 2) 结构转为 section/subsection 3) 列表转为 enumerate/itemize 4) 保留原始语义。",
  abstract: "请为以下内容生成一份学术摘要（200-300字），包含：1) 研究背景 2) 方法 3) 主要发现 4) 结论。使用第三人称，语言精炼。",
};

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [streamThinking, setStreamThinking] = useState("");
  const [streamToolCalls, setStreamToolCalls] = useState<{name: string; query: string; result?: string}[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // @引用系统
  const [showMention, setShowMention] = useState(false);
  const [mentionResults, setMentionResults] = useState<Pick<PaperDetail, "id" | "title" | "authors" | "year">[]>([]);
  const [selectedMentions, setSelectedMentions] = useState<Pick<PaperDetail, "id" | "title" | "authors" | "year">[]>([]);
  const mentionRef = useRef<HTMLDivElement>(null);

  // 搜索文献供 @引用
  const searchMentionPapers = useCallback(async (q: string) => {
    if (!q.trim()) { setMentionResults([]); return; }
    try {
      const results = await papersApi.searchMention(q, 8);
      setMentionResults(results);
    } catch { setMentionResults([]); }
  }, []);

  // 监听 @ 触发
  useEffect(() => {
    const lastAt = input.lastIndexOf("@");
    if (lastAt >= 0 && (lastAt === 0 || input[lastAt - 1] === " ")) {
      const q = input.slice(lastAt + 1);
      if (!q.includes(" ") && q.length < 50) {
        setShowMention(true);
        searchMentionPapers(q);
        return;
      }
    }
    setShowMention(false);
  }, [input, searchMentionPapers]);

  // 插入引用
  const insertMention = (paper: Pick<PaperDetail, "id" | "title" | "authors" | "year">) => {
    const lastAt = input.lastIndexOf("@");
    const before = input.slice(0, lastAt);
    setInput(before + `@${paper.title} `);
    setSelectedMentions(prev => {
      if (prev.find(p => p.id === paper.id)) return prev;
      return [...prev, paper];
    });
    setShowMention(false);
  };

  useEffect(() => {
    chatApi.listSessions().then(setSessions).catch(console.error);
    modelsApi.list().then(ms => {
      setModels(ms);
      if (ms.length && !selectedModelId) setSelectedModelId(ms[0].id);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (activeSession) {
      chatApi.getMessages(activeSession).then(setMessages).catch(console.error);
    }
  }, [activeSession]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent, streamToolCalls]);

  const handleNewSession = async () => {
    const res = await chatApi.createSession();
    setSessions(prev => [{ id: res.id, title: "新对话", model_name: "", category: "general", created_at: new Date().toISOString() }, ...prev]);
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

  // 快捷操作
  const handleQuickAction = async (action: string) => {
    // 获取选中文本（如果没有则用输入框内容）
    const selectedText = window.getSelection()?.toString() || input.trim();
    if (!selectedText) {
      alert("请先选中文本或在输入框中输入内容");
      return;
    }
    const prompt = WRITING_PROMPTS[action];
    if (!prompt) return;

    // 设置输入内容并发送
    const fullContent = `${prompt}\n\n${selectedText}`;
    setInput("");
    if (!activeSession) await handleNewSession();

    const msg = await chatApi.addMessage(activeSession!, fullContent);
    setMessages(prev => [...prev, msg]);
    if (messages.length === 0) {
      setSessions(prev => prev.map(s => s.id === activeSession ? { ...s, title: `${action === "polish" ? "润色" : action === "translate" ? "翻译" : action === "latex" ? "LaTeX" : "摘要"}: ${selectedText.slice(0, 20)}` } : s));
    }

    setStreaming(true);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);

    try {
      const modelId = selectedModelId || models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession!, modelId)) {
        if (chunk.type === "thinking") setStreamThinking(prev => prev + chunk.data);
        else if (chunk.type === "content") setStreamContent(prev => prev + chunk.data);
      }
    } catch (err) {
      setStreamContent(`错误: ${err}`);
    }

    const updated = await chatApi.getMessages(activeSession!);
    setMessages(updated);
    setStreaming(false);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
  };

  // 存为知识卡片
  const handleSaveAsCard = async () => {
    const lastAiMessage = [...messages].reverse().find(m => m.role === "assistant");
    if (!lastAiMessage) { alert("没有 AI 回复可保存"); return; }
    try {
      const { knowledgeApi } = await import("../api/client");
      await knowledgeApi.createCard({
        title: lastAiMessage.content.slice(0, 60),
        summary: lastAiMessage.content.slice(0, 500),
        source_type: "manual",
      });
      alert("已保存为知识卡片");
    } catch (err) { alert("保存失败: " + err); }
  };

  const handleSend = async () => {
    if (!input.trim() || streaming) return;
    if (!activeSession) {
      await handleNewSession();
    }

    // 构建带引用上下文的内容
    let content = input.trim();
    if (selectedMentions.length > 0) {
      const refsContext = selectedMentions.map((p, i) =>
        `[参考文献${i + 1}] ${p.title} (${p.authors?.slice(0, 3).join(", ")}${p.authors && p.authors.length > 3 ? " 等" : ""}, ${p.year})`
      ).join("\n");
      content = `${refsContext}\n\n${content}`;
    }
    setInput("");
    setSelectedMentions([]);

    const msg = await chatApi.addMessage(activeSession!, content);
    setMessages(prev => [...prev, msg]);

    if (messages.length === 0) {
      setSessions(prev => prev.map(s => s.id === activeSession ? { ...s, title: content.slice(0, 30) } : s));
    }

    setStreaming(true);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);

    try {
      const modelId = selectedModelId || models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession!, modelId)) {
        if (chunk.type === "thinking") {
          setStreamThinking(prev => prev + chunk.data);
        } else if (chunk.type === "content") {
          setStreamContent(prev => prev + chunk.data);
        } else if (chunk.type === "tool_call") {
          const info = JSON.parse(chunk.data);
          setStreamToolCalls(prev => [...prev, { name: info.name, query: info.query }]);
        } else if (chunk.type === "tool_result") {
          const info = JSON.parse(chunk.data);
          setStreamToolCalls(prev => prev.map((tc, i) =>
            i === prev.length - 1 && tc.name === info.name && tc.query === info.query
              ? { ...tc, result: info.result }
              : tc
          ));
        }
      }
    } catch (err) {
      setStreamContent(`错误: ${err}`);
    }

    const updated = await chatApi.getMessages(activeSession!);
    setMessages(updated);
    setStreaming(false);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
  };

  const currentSession = sessions.find(s => s.id === activeSession);

  return (
    <div className="flex gap-4 h-full">
      {/* 左侧 */}
      <div className="w-56 flex-shrink-0 flex flex-col gap-2">
        <div className="glass-card p-3 space-y-2">
          <p className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>模型</p>
          <select className="input-glass text-sm"
            value={selectedModelId}
            onChange={e => setSelectedModelId(e.target.value)}
          >
            {models.length ? models.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            )) : <option>未配置模型</option>}
          </select>
        </div>
        <button className="btn-gradient btn-click" onClick={handleNewSession}>新建对话</button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => setActiveSession(s.id)}
              className="px-3 py-2 rounded-xl text-sm cursor-pointer transition-all truncate"
              style={activeSession === s.id
                ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)", fontWeight: 500 }
                : { color: "var(--text-secondary)" }
              }
              onMouseEnter={e => { if (activeSession !== s.id) e.currentTarget.style.background = "var(--hover-bg)"; }}
              onMouseLeave={e => { if (activeSession !== s.id) e.currentTarget.style.background = "transparent"; }}
            >
              {s.title.slice(0, 20)}
            </div>
          ))}
        </div>
        {activeSession && (
          <button className="text-sm py-2 transition-colors" style={{ color: "var(--text-muted)" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
            onClick={handleDeleteSession}>删除当前对话</button>
        )}
      </div>

      {/* 右侧 */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>{currentSession?.title || "选择或新建对话"}</h2>

        <div className="flex-1 space-y-3 overflow-y-auto">
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className="max-w-[80%] rounded-2xl px-4 py-3"
                style={msg.role === "user"
                  ? { background: "var(--accent-blue)", color: "#fff" }
                  : { background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }
                }
              >
                <p className="text-[10px] font-semibold mb-1 opacity-60">{msg.role === "user" ? "You" : "AI"}</p>
                {msg.thinking_content && (
                  <details className="mb-2">
                    <summary className="text-xs cursor-pointer" style={{ color: msg.role === "user" ? "rgba(255,255,255,0.6)" : "var(--text-muted)" }}>Thinking...</summary>
                    <p className="text-xs italic mt-1 whitespace-pre-wrap" style={{ color: msg.role === "user" ? "rgba(255,255,255,0.7)" : "var(--text-secondary)" }}>{msg.thinking_content}</p>
                  </details>
                )}
                <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
              </div>
            </div>
          ))}

          {streaming && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-4 py-3" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }}>
                <p className="text-[10px] font-semibold mb-1 opacity-60" style={{ color: "var(--text-secondary)" }}>AI</p>
                {streamToolCalls.length > 0 && (
                  <div className="mb-2 space-y-1">
                    {streamToolCalls.map((tc, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs px-2 py-1 rounded-lg"
                        style={{ background: "rgba(59,130,246,0.08)", color: "var(--accent-blue)" }}>
                        <span>🔍</span>
                        <span className="font-medium">{tc.query}</span>
                        {!tc.result && <span className="animate-pulse ml-auto">搜索中...</span>}
                        {tc.result && <span className="ml-auto" style={{ color: "var(--text-muted)" }}>✓</span>}
                      </div>
                    ))}
                  </div>
                )}
                {streamThinking && (
                  <details open className="mb-2">
                    <summary className="text-xs cursor-pointer" style={{ color: "var(--text-muted)" }}>Thinking...</summary>
                    <p className="text-xs italic mt-1 whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>{streamThinking}</p>
                  </details>
                )}
                <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderMarkdown(streamContent || (streamToolCalls.length ? "" : "...")) }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 快捷操作 */}
        <div className="flex gap-2 text-xs">
          {[
            { key: "polish", label: "润色" },
            { key: "translate", label: "翻译" },
            { key: "latex", label: "LaTeX" },
            { key: "abstract", label: "摘要" },
          ].map(({ key, label }) => (
            <button key={key} className="px-3 py-1 rounded-full transition-colors cursor-pointer"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              onClick={() => handleQuickAction(key)}
            >{label}</button>
          ))}
          <span className="flex-1" />
          <button className="px-3 py-1 rounded-full transition-colors cursor-pointer"
            style={{ color: "var(--text-secondary)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            onClick={handleSaveAsCard}
          >存为卡片</button>
        </div>

        {/* 已选引用 */}
        {selectedMentions.length > 0 && (
          <div className="flex gap-1.5 flex-wrap">
            {selectedMentions.map(p => (
              <span key={p.id} className="text-xs px-2 py-0.5 rounded-full flex items-center gap-1"
                style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>
                {p.title.slice(0, 20)}...
                <button className="cursor-pointer" onClick={() => setSelectedMentions(prev => prev.filter(m => m.id !== p.id))}>×</button>
              </span>
            ))}
          </div>
        )}

        {/* 输入区 */}
        <div className="relative">
          {/* @引用下拉 */}
          {showMention && mentionResults.length > 0 && (
            <div ref={mentionRef} className="absolute bottom-full left-0 right-0 mb-1 glass-card p-2 max-h-48 overflow-y-auto z-10"
              style={{ background: "var(--glass-bg)", border: "1px solid var(--border-color)" }}>
              {mentionResults.map(p => (
                <div key={p.id} className="px-3 py-2 rounded-lg cursor-pointer text-xs"
                  style={{ color: "var(--text-primary)" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  onClick={() => insertMention(p)}>
                  <p className="font-medium">{p.title}</p>
                  <p style={{ color: "var(--text-muted)" }}>{p.authors?.slice(0, 2).join(", ")} · {p.year}</p>
                </div>
              ))}
            </div>
          )}
          <div className="glass-card p-3 flex gap-3 items-end">
            <textarea
              className="flex-1 bg-transparent border-none outline-none resize-none text-sm"
              style={{ color: "var(--text-primary)" }}
              placeholder="输入消息... (@ 引用文献，Enter 发送)"
              rows={2}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
              }}
            />
            <button className="btn-gradient btn-click flex-shrink-0" onClick={handleSend} disabled={streaming}>
              {streaming ? "..." : "发送"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
