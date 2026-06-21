import { useEffect, useState, useRef, useCallback } from "react";
import { chatApi, modelsApi, papersApi, type ChatSession, type ChatMessage, type ModelConfig, type PaperDetail } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// 从文本中提取关键词生成 ≤10 字标题
function extractTitle(userMsg: string, _aiMsg: string): string {
  const text = userMsg.replace(/[@#]/g, "").trim();
  const patterns = [
    /(?:请|帮我|关于|分析|解释|什么是|如何|怎么)(.{2,8})/u,
    /^(.{2,10})[？?。.!！]/u,
  ];
  for (const p of patterns) {
    const m = text.match(p);
    if (m && m[1]) {
      const title = m[1].trim().slice(0, 10);
      if (title.length >= 2) return title;
    }
  }
  const cn = text.match(/[一-鿿]{2,10}/);
  if (cn) return cn[0].slice(0, 10);
  const en = text.match(/[a-zA-Z0-9\s]{3,15}/);
  if (en) return en[0].trim().slice(0, 10);
  return text.slice(0, 10) || "新对话";
}

// 复制状态 hook
function useCopyable() {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const copy = useCallback((id: string, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }, []);
  return { copiedId, copy };
}

// Code block component with copy button
function CodeBlock({ language, children }: { language: string; children: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-block-lang">{language || "code"}</span>
        <button className="code-block-copy" onClick={handleCopy}>
          {copied ? "✓ 已复制" : "复制"}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language || "text"}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: "0 0 8px 8px",
          fontSize: "13px",
          lineHeight: "1.6",
          background: "rgba(15, 23, 42, 0.06)",
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

// Markdown renderer component
function MarkdownContent({ content, isUser }: { content: string; isUser: boolean }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const codeStr = String(children).replace(/\n$/, "");
          if (match) {
            return <CodeBlock language={match[1]} children={codeStr} />;
          }
          return (
            <code className="inline-code" {...props}>
              {children}
            </code>
          );
        },
        table({ children }) {
          return (
            <div className="table-wrapper">
              <table>{children}</table>
            </div>
          );
        },
        a({ href, children }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer"
              style={{ color: isUser ? "rgba(255,255,255,0.9)" : "var(--accent-blue)", textDecoration: "underline" }}>
              {children}
            </a>
          );
        },
        blockquote({ children }) {
          return (
            <blockquote style={{
              borderLeft: "3px solid var(--accent-blue)",
              paddingLeft: "12px",
              margin: "8px 0",
              color: "var(--text-secondary)",
              fontStyle: "italic",
            }}>
              {children}
            </blockquote>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// 写作场景 prompt
const WRITING_PROMPTS: Record<string, string> = {
  polish: "请对以下学术文本进行润色，保持原意的同时提升语言表达的学术性和流畅度。注意：1) 使用准确的学术术语 2) 保持逻辑连贯 3) 避免口语化表达。",
  translate: "请将以下文本翻译为学术英语/中文（根据源语言自动判断方向）。要求：1) 使用准确的学术术语 2) 保持句式地道 3) 专有名词保持一致。",
  latex: "请将以下文本转换为 LaTeX 格式。包括：1) 数学公式转为 $...$ 或 \\[...\\] 2) 结构转为 section/subsection 3) 列表转为 enumerate/itemize 4) 保留原始语义。",
  abstract: "请为以下内容生成一份学术摘要（200-300字），包含：1) 研究背景 2) 方法 3) 主要发现 4) 结论。使用第三人称，语言精炼。",
};

// 会话分类
const CHAT_CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "general", label: "通用" },
  { key: "review", label: "文献综述" },
  { key: "idea", label: "IDEA" },
  { key: "research", label: "研究" },
  { key: "discussion", label: "选题讨论" },
];

// 研究讨论结构化 prompt 模板
const DISCUSSION_TEMPLATES = [
  { key: "gap", label: "研究空白", prompt: "请分析该方向目前的研究空白和不足之处，指出尚未解决的关键问题。" },
  { key: "innovation", label: "创新点", prompt: "请从方法论、应用场景、技术路线等角度，挖掘可能的创新点和突破方向。" },
  { key: "feasibility", label: "可行性", prompt: "请评估该研究方向的技术可行性，包括所需资源、技术难度、预期周期。" },
  { key: "related", label: "相关工作", prompt: "请推荐该方向值得重点关注的文献和研究团队。" },
];

function detectCategory(title: string, category: string): string {
  if (category && category !== "general") return category;
  if (title.includes("综述") || title.includes("review")) return "review";
  if (title.includes("IDEA") || title.includes("想法")) return "idea";
  if (title.includes("选题") || title.includes("研究") || title.includes("讨论")) return "discussion";
  if (title.includes("research")) return "research";
  return "general";
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
  const [streamToolCalls, setStreamToolCalls] = useState<{name: string; query: string; result?: string}[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [sessionSearch, setSessionSearch] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [streamStats, setStreamStats] = useState<{tokens: number; duration_ms: number} | null>(null);
  const streamStartTime = useRef<number>(0);

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

  // 自动滚动（仅在 autoScroll 开启时）
  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamContent, streamToolCalls, autoScroll]);

  // 检测用户滚动位置
  const handleChatScroll = useCallback(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    setAutoScroll(isAtBottom);
  }, []);

  // 停止生成
  const handleStopGenerate = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
  }, []);

  const handleNewSession = async (cat?: string) => {
    const category = cat || (activeCategory !== "all" ? activeCategory : "general");
    const res = await chatApi.createSession(undefined, category);
    setSessions(prev => [{ id: res.id, title: "新对话", model_name: "", category, created_at: new Date().toISOString() }, ...prev]);
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
    const selectedText = window.getSelection()?.toString() || input.trim();
    if (!selectedText) {
      alert("请先选中文本或在输入框中输入内容");
      return;
    }
    const prompt = WRITING_PROMPTS[action];
    if (!prompt) return;

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
    setStreamStats(null);
    setAutoScroll(true);
    streamStartTime.current = Date.now();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const modelId = selectedModelId || models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession!, modelId, controller.signal)) {
        if (chunk.type === "thinking") setStreamThinking(prev => prev + chunk.data);
        else if (chunk.type === "content") setStreamContent(prev => prev + chunk.data);
        else if (chunk.type === "stats") setStreamStats(chunk.data);
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // 用户主动停止
      } else {
        setStreamContent(`错误: ${err}`);
      }
    }

    abortRef.current = null;

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

    const isFirstMessage = messages.length === 0;

    setStreaming(true);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
    setStreamStats(null);
    setAutoScroll(true);
    streamStartTime.current = Date.now();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const modelId = selectedModelId || models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession!, modelId, controller.signal)) {
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
        } else if (chunk.type === "stats") {
          setStreamStats(chunk.data);
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // 用户主动停止，不显示错误
      } else {
        setStreamContent(`错误: ${err}`);
      }
    }

    abortRef.current = null;

    const updated = await chatApi.getMessages(activeSession!);
    setMessages(updated);
    setStreaming(false);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);

    // 首次对话后自动生成标题
    if (isFirstMessage && activeSession) {
      const aiReply = updated.find(m => m.role === "assistant");
      if (aiReply) {
        const autoTitle = extractTitle(content, aiReply.content);
        setSessions(prev => prev.map(s => s.id === activeSession ? { ...s, title: autoTitle } : s));
      }
    }
  };

  // 重新生成最后一条 AI 回复
  const handleRegenerate = useCallback(async () => {
    if (!activeSession || streaming || messages.length < 2) return;

    // 找到最后一条用户消息
    const lastUserMsg = [...messages].reverse().find(m => m.role === "user");
    if (!lastUserMsg) return;

    setStreaming(true);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
    setStreamStats(null);
    setAutoScroll(true);
    streamStartTime.current = Date.now();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const modelId = selectedModelId || models[0]?.id;
      for await (const chunk of chatApi.stream(activeSession, modelId, controller.signal)) {
        if (chunk.type === "thinking") setStreamThinking(prev => prev + chunk.data);
        else if (chunk.type === "content") setStreamContent(prev => prev + chunk.data);
        else if (chunk.type === "tool_call") {
          const info = JSON.parse(chunk.data);
          setStreamToolCalls(prev => [...prev, { name: info.name, query: info.query }]);
        } else if (chunk.type === "tool_result") {
          const info = JSON.parse(chunk.data);
          setStreamToolCalls(prev => prev.map((tc, i) =>
            i === prev.length - 1 && tc.name === info.name && tc.query === info.query
              ? { ...tc, result: info.result } : tc
          ));
        } else if (chunk.type === "stats") setStreamStats(chunk.data);
      }
    } catch (err: unknown) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setStreamContent(`错误: ${err}`);
      }
    }

    abortRef.current = null;
    const updated = await chatApi.getMessages(activeSession);
    setMessages(updated);
    setStreaming(false);
    setStreamContent("");
    setStreamThinking("");
    setStreamToolCalls([]);
  }, [activeSession, streaming, messages, selectedModelId, models]);

  const { copiedId, copy } = useCopyable();
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

        {/* 分类标签 */}
        <div className="flex flex-wrap gap-1 px-1">
          {CHAT_CATEGORIES.map(cat => {
            const count = cat.key === "all" ? sessions.length : sessions.filter(s => detectCategory(s.title, s.category) === cat.key).length;
            return (
              <button
                key={cat.key}
                className="px-2 py-1 rounded-lg text-[11px] font-medium cursor-pointer transition-all"
                style={activeCategory === cat.key
                  ? { background: "rgba(59,130,246,0.12)", color: "var(--accent-blue)" }
                  : { color: "var(--text-muted)" }
                }
                onClick={() => setActiveCategory(cat.key)}
              >
                {cat.label}{count > 0 ? ` ${count}` : ""}
              </button>
            );
          })}
        </div>

        <button className="btn-gradient btn-click text-xs py-2" onClick={() => handleNewSession()}>新建对话</button>
        <div className="px-1">
          <input
            className="input-glass text-xs w-full"
            placeholder="🔍 搜索会话..."
            value={sessionSearch}
            onChange={e => setSessionSearch(e.target.value)}
          />
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {(activeCategory === "all" ? sessions : sessions.filter(s => detectCategory(s.title, s.category) === activeCategory))
            .filter(s => !sessionSearch.trim() || s.title.toLowerCase().includes(sessionSearch.toLowerCase()))
            .map(s => {
            const cat = detectCategory(s.title, s.category);
            const catInfo = CHAT_CATEGORIES.find(c => c.key === cat);
            return (
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
              <span className="truncate">{s.title.slice(0, 20)}</span>
              {cat !== "general" && catInfo && (
                <span className="ml-1 text-[9px] px-1 py-0.5 rounded" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>
                  {catInfo.label}
                </span>
              )}
            </div>
            );
          })}
        </div>
        {activeSession && (
          <div className="flex gap-2">
            <button className="text-xs py-2 transition-colors flex-1" style={{ color: "var(--text-muted)" }}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
              onClick={async () => {
                if (!activeSession) return;
                try {
                  const res = await chatApi.exportSession(activeSession);
                  const blob = new Blob([res.content], { type: "text/markdown" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url; a.download = `${res.title || "export"}.md`; a.click();
                  URL.revokeObjectURL(url);
                } catch (err) { alert("导出失败: " + err); }
              }}>导出MD</button>
            <button className="text-xs py-2 transition-colors flex-1" style={{ color: "var(--text-muted)" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
              onClick={handleDeleteSession}>删除</button>
          </div>
        )}
      </div>

      {/* 右侧 */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        <h2 className="text-base font-bold" style={{ color: "var(--text-primary)" }}>{currentSession?.title || "选择或新建对话"}</h2>

        <div ref={chatContainerRef} onScroll={handleChatScroll} className="flex-1 space-y-3 overflow-y-auto chat-scroll-area">
          {messages.map((msg, msgIdx) => {
            const isLastAi = msg.role === "assistant" && msgIdx === messages.length - 1 && !streaming;
            return (
            <div key={msg.id} className={`chat-message-enter flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              style={{ animationDelay: `${Math.min(msgIdx * 0.03, 0.3)}s` }}>
              <div className="max-w-[80%] rounded-2xl px-4 py-3 group relative"
                style={msg.role === "user"
                  ? { background: "var(--accent-blue)", color: "#fff" }
                  : { background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }
                }
              >
                {/* 操作按钮 */}
                <div className="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 z-10">
                  <button
                    className="px-2 py-1 rounded-lg text-xs cursor-pointer"
                    style={{
                      background: msg.role === "user" ? "rgba(255,255,255,0.25)" : "var(--hover-bg)",
                      color: msg.role === "user" ? "rgba(255,255,255,0.9)" : "var(--text-secondary)",
                      backdropFilter: "blur(4px)",
                    }}
                    onClick={(e) => { e.stopPropagation(); copy(msg.id, msg.thinking_content ? `[Thinking]\n${msg.thinking_content}\n\n${msg.content}` : msg.content); }}
                  >
                    {copiedId === msg.id ? "✓" : "复制"}
                  </button>
                  {isLastAi && (
                    <button
                      className="px-2 py-1 rounded-lg text-xs cursor-pointer"
                      style={{ background: "var(--hover-bg)", color: "var(--accent-blue)", backdropFilter: "blur(4px)" }}
                      onClick={(e) => { e.stopPropagation(); handleRegenerate(); }}
                      title="重新生成"
                    >
                      🔄
                    </button>
                  )}
                </div>
                <p className="text-[10px] font-semibold mb-1.5 opacity-60">{msg.role === "user" ? "You" : "AI"}</p>
                {msg.thinking_content && (
                  <details className="thinking-block mb-2">
                    <summary className="text-xs cursor-pointer flex items-center gap-1.5"
                      style={{ color: msg.role === "user" ? "rgba(255,255,255,0.6)" : "var(--text-muted)" }}>
                      <span className="thinking-icon">💭</span> Thinking
                    </summary>
                    <div className="thinking-content mt-1.5 text-xs whitespace-pre-wrap"
                      style={{ color: msg.role === "user" ? "rgba(255,255,255,0.7)" : "var(--text-secondary)" }}>
                      {msg.thinking_content}
                    </div>
                  </details>
                )}
                <div className="markdown-body text-sm">
                  <MarkdownContent content={msg.content} isUser={msg.role === "user"} />
                </div>
              </div>
            </div>
            );
          })}

          {streaming && (
            <div className="chat-message-enter flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-4 py-3 group relative" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }}>
                <p className="text-[10px] font-semibold mb-1.5 opacity-60" style={{ color: "var(--text-secondary)" }}>AI</p>
                {streamToolCalls.length > 0 && (
                  <div className="mb-2 space-y-1.5">
                    {streamToolCalls.map((tc, i) => (
                      <div key={i} className="tool-call-item rounded-lg overflow-hidden"
                        style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.1)" }}>
                        <div className="flex items-center gap-2 text-xs px-3 py-1.5">
                          <span className="tool-call-icon">{tc.result ? "✅" : "🔍"}</span>
                          <span className="font-medium truncate flex-1" style={{ color: "var(--accent-blue)" }}>{tc.query}</span>
                          {!tc.result && <span className="stream-typing-dots" style={{ color: "var(--text-muted)" }}>搜索中</span>}
                        </div>
                        {tc.result && (
                          <div className="px-3 py-2 text-[11px] border-t" style={{ borderColor: "rgba(59,130,246,0.1)", color: "var(--text-secondary)" }}>
                            {(() => {
                              try {
                                const data = JSON.parse(tc.result);
                                if (Array.isArray(data)) {
                                  return (
                                    <div className="space-y-1">
                                      {data.slice(0, 3).map((item: any, j: number) => (
                                        <div key={j} className="flex items-start gap-2">
                                          <span style={{ color: "var(--accent-blue)" }}>•</span>
                                          <span className="truncate">{item.title || item.name || JSON.stringify(item).slice(0, 60)}</span>
                                        </div>
                                      ))}
                                      {data.length > 3 && <div style={{ color: "var(--text-muted)" }}>...共 {data.length} 条结果</div>}
                                    </div>
                                  );
                                }
                                return <span>{data.summary || data.message || JSON.stringify(data).slice(0, 100)}</span>;
                              } catch {
                                return <span>{tc.result.slice(0, 100)}</span>;
                              }
                            })()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {streamThinking && (
                  <details open className="thinking-block mb-2">
                    <summary className="text-xs cursor-pointer flex items-center gap-1.5" style={{ color: "var(--text-muted)" }}>
                      <span className="thinking-icon">💭</span> Thinking
                    </summary>
                    <div className="thinking-content mt-1.5 text-xs whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>
                      {streamThinking}
                    </div>
                  </details>
                )}
                <div className="markdown-body text-sm">
                  {streamContent ? (
                    <MarkdownContent content={streamContent} isUser={false} />
                  ) : streamToolCalls.length === 0 ? (
                    <span className="stream-cursor">▊</span>
                  ) : null}
                </div>
                {streamStats && (
                  <div className="mt-2 text-[10px] flex items-center gap-3" style={{ color: "var(--text-muted)" }}>
                    <span>📊 {streamStats.tokens} tokens</span>
                    <span>⏱ {(streamStats.duration_ms / 1000).toFixed(1)}s</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 快捷操作 */}
        <div className="flex gap-2 text-xs flex-wrap">
          {/* 研究讨论模板（仅在讨论类会话中显示） */}
          {currentSession && detectCategory(currentSession.title, currentSession.category) === "discussion" && (
            <>
              {DISCUSSION_TEMPLATES.map(t => (
                <button key={t.key} className="px-3 py-1 rounded-full transition-colors cursor-pointer"
                  style={{ background: "rgba(59,130,246,0.08)", color: "var(--accent-blue)" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "rgba(59,130,246,0.15)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "rgba(59,130,246,0.08)")}
                  onClick={() => {
                    setInput(prev => prev ? `${prev}\n${t.prompt}` : t.prompt);
                  }}
                >{t.label}</button>
              ))}
              <span className="w-px h-5 flex-shrink-0" style={{ background: "var(--border-color)" }} />
            </>
          )}
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
            {streaming ? (
              <button className="flex-shrink-0 px-4 py-2 rounded-xl text-sm font-medium text-white cursor-pointer transition-all"
                style={{ background: "#ef4444" }}
                onClick={handleStopGenerate}>
                停止生成
              </button>
            ) : (
              <button className="btn-gradient btn-click flex-shrink-0" onClick={handleSend}>
                发送
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
