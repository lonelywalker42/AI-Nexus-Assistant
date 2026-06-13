import { useState, useEffect, useRef } from "react";
import { searchApi, historyApi, chatApi, modelsApi, knowledgeApi, type Paper, type HistoryRecord, type ModelConfig, type KnowledgeCard } from "../api/client";
import { IconSearch, IconChevronRight } from "../components/Icons";

const SOURCES = [
  { key: "openalex", label: "OpenAlex", default: true },
  { key: "arxiv", label: "arXiv", default: true },
  { key: "semantic_scholar", label: "Semantic Scholar", default: true },
  { key: "crossref", label: "CrossRef", default: false },
  { key: "pubmed", label: "PubMed", default: false },
  { key: "google_scholar", label: "Google Scholar", default: false },
  { key: "scopus", label: "Scopus", default: false },
];

export default function LiteraturePage() {
  const [tab, setTab] = useState<"search" | "review" | "topic" | "history">("search");
  const [keywords, setKeywords] = useState([""]);
  const [selectedSources, setSelectedSources] = useState(SOURCES.filter(s => s.default).map(s => s.key));
  const [results, setResults] = useState<Paper[]>([]);
  const [searching, setSearching] = useState(false);
  const [stats, setStats] = useState("");

  // AI 综述
  const [reviewInput, setReviewInput] = useState("");
  const [reviewContent, setReviewContent] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const [reviewSource, setReviewSource] = useState<"search" | "kb" | "custom">("search");
  const [kbCards, setKbCards] = useState<KnowledgeCard[]>([]);
  const [selectedKbCards, setSelectedKbCards] = useState<string[]>([]);

  // 选题讨论
  const [topicInput, setTopicInput] = useState("");
  const [topicContent, setTopicContent] = useState("");
  const [discussing, setDiscussing] = useState(false);

  // 历史记录
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);

  // 模型
  const [models, setModels] = useState<ModelConfig[]>([]);

  const reviewEndRef = useRef<HTMLDivElement>(null);
  const topicEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    modelsApi.list().then(setModels).catch(console.error);
  }, []);

  useEffect(() => {
    if (tab === "history") {
      historyApi.list().then(setHistory).catch(console.error);
    }
  }, [tab]);

  // 加载知识库卡片（综述tab切换到kb时）
  useEffect(() => {
    if (tab === "review" && reviewSource === "kb") {
      knowledgeApi.listCards({ source_type: "literature" }).then(setKbCards).catch(console.error);
    }
  }, [tab, reviewSource]);

  const handleSearch = async () => {
    const query = keywords.filter(k => k.trim()).join(" ");
    if (!query.trim()) return;
    setSearching(true);
    setStats("搜索中...");
    try {
      const res = await searchApi.search(query, selectedSources);
      setResults(res.papers);
      setStats(`找到 ${res.count} 篇文献（已自动保存到历史记录）`);
    } catch (err) {
      setStats(`搜索失败: ${err}`);
    }
    setSearching(false);
  };

  const toggleSource = (key: string) => {
    setSelectedSources(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  // AI 综述 - 支持三种数据源
  const handleReview = async () => {
    setReviewing(true);
    setReviewContent("");

    let prompt = "";

    if (reviewSource === "custom" && reviewInput.trim()) {
      // 自定义输入
      prompt = `请基于以下文献数据生成一份结构化的AI综述报告，包含：研究背景、主要发现、研究趋势、关键结论。文献数据：\n\n${reviewInput.slice(0, 4000)}`;
    } else if (reviewSource === "kb" && selectedKbCards.length > 0) {
      // 知识库选中的卡片
      const selected = kbCards.filter(c => selectedKbCards.includes(c.id));
      const paperSummaries = selected.map((c, i) =>
        `[${i + 1}] ${c.title}\n摘要: ${c.summary || "无"}\n要点: ${c.key_points?.join("; ") || "无"}`
      ).join("\n\n");
      prompt = `请基于以下知识库文献生成一份结构化的AI综述报告，包含：研究背景、主要发现、研究趋势、关键结论。\n\n${paperSummaries}`;
    } else if (reviewSource === "search" && results.length > 0) {
      // 搜索结果
      const paperSummaries = results.slice(0, 20).map((p, i) =>
        `[${i + 1}] ${p.title} (${p.year}) - ${p.authors?.slice(0, 3).join(", ")} | ${p.journal}\n${p.abstract?.slice(0, 200) || ""}`
      ).join("\n\n");
      prompt = `请基于以下文献生成一份结构化的AI综述报告，包含：研究背景、主要发现、研究趋势、关键结论。\n\n${paperSummaries}`;
    } else {
      setReviewContent("请选择数据源：搜索结果、知识库文献，或粘贴自定义数据。");
      setReviewing(false);
      return;
    }

    try {
      const session = await chatApi.createSession("文献综述");
      await chatApi.addMessage(session.id, prompt);
      const modelId = models[0]?.id;
      for await (const chunk of chatApi.stream(session.id, modelId)) {
        if (chunk.type === "content") {
          setReviewContent(prev => prev + chunk.data);
        }
      }
    } catch (err) {
      setReviewContent(`生成失败: ${err}`);
    }
    setReviewing(false);
  };

  // 选题讨论
  const handleDiscuss = async () => {
    if (!topicInput.trim()) return;
    setDiscussing(true);
    setTopicContent("");

    const prompt = `你是一位资深的科研导师。请针对以下研究方向进行深入的选题讨论，提供：1) 3-5个具体选题建议；2) 每个选题的研究价值和创新点；3) 可能的研究方法；4) 预期难度和周期评估。\n\n研究方向：${topicInput}`;

    try {
      const session = await chatApi.createSession("选题讨论");
      await chatApi.addMessage(session.id, prompt);
      const modelId = models[0]?.id;
      for await (const chunk of chatApi.stream(session.id, modelId)) {
        if (chunk.type === "content") {
          setTopicContent(prev => prev + chunk.data);
        }
      }
    } catch (err) {
      setTopicContent(`生成失败: ${err}`);
    }
    setDiscussing(false);
  };

  // 解析历史记录中的文献数据（兼容 string / object / 截断JSON）
  const parseHistoryData = (data: unknown): Paper[] => {
    if (Array.isArray(data)) return data as Paper[];
    if (typeof data === "string" && data.length > 2) {
      try { return JSON.parse(data); } catch {
        // JSON 可能被截断，尝试修复
        try {
          // 补全截断的 JSON 数组
          let fixed = data.trim();
          // 移除末尾不完整的对象
          const lastComplete = fixed.lastIndexOf('}');
          if (lastComplete > 0) {
            fixed = fixed.substring(0, lastComplete + 1) + ']';
            // 确保以 [ 开头
            if (!fixed.startsWith('[')) fixed = '[' + fixed;
            return JSON.parse(fixed);
          }
        } catch {}
        return [];
      }
    }
    return [];
  };

  // 从历史记录加载到搜索
  const loadHistoryResults = (record: HistoryRecord) => {
    const papers = parseHistoryData(record.data);
    setResults(papers);
    setKeywords(record.query.split(" OR ").map(s => s.trim()));
    setStats(`已加载历史记录: "${record.query}" — ${papers.length} 篇文献 (${new Date(record.created_at).toLocaleDateString("zh-CN")})`);
    setTab("search");
  };

  // 切换知识库卡片选择
  const toggleKbCard = (id: string) => {
    setSelectedKbCards(prev => prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]);
  };

  const renderStreamingContent = (content: string, endRef: React.RefObject<HTMLDivElement | null>) => (
    <div className="glass-card p-5 max-h-96 overflow-y-auto">
      <div className="markdown-body text-sm" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(content) }} />
      <div ref={endRef} />
    </div>
  );

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>文献管理</h2>

      {/* Tab 切换 */}
      <div className="flex gap-1" style={{ borderBottom: "1px solid var(--border-color)" }}>
        {(["search", "review", "topic", "history"] as const).map(t => {
          const labels = { search: "关键词检索", review: "AI 综述", topic: "选题讨论", history: "历史记录" };
          const isActive = tab === t;
          return (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer"
              style={isActive
                ? { borderBottom: "2px solid var(--accent-blue)", color: "var(--accent-blue)" }
                : { borderBottom: "2px solid transparent", color: "var(--text-secondary)" }
              }
            >
              {labels[t]}
            </button>
          );
        })}
      </div>

      {/* 关键词检索 */}
      {tab === "search" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-4">
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>关键词组（组内 AND，组间 OR）</p>
            {keywords.map((kw, i) => (
              <div key={i} className="flex gap-2 items-center">
                <input
                  className="input-glass flex-1"
                  placeholder={`关键词 ${i + 1}`}
                  value={kw}
                  onChange={e => {
                    const next = [...keywords];
                    next[i] = e.target.value;
                    setKeywords(next);
                  }}
                />
                {i < keywords.length - 1 && <span className="text-sm font-bold" style={{ color: "var(--accent-blue)" }}>OR</span>}
                {keywords.length > 1 && (
                  <button onClick={() => setKeywords(keywords.filter((_, j) => j !== i))} className="text-sm transition-colors cursor-pointer"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")}
                    onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
                  >✕</button>
                )}
              </div>
            ))}
            <button onClick={() => setKeywords([...keywords, ""])} className="text-sm cursor-pointer" style={{ color: "var(--accent-blue)" }}>+ 添加关键词</button>

            <div className="flex gap-3 flex-wrap text-sm">
              {SOURCES.map(s => (
                <label key={s.key} className="flex items-center gap-1.5 cursor-pointer" style={{ color: "var(--text-secondary)" }}>
                  <input type="checkbox" checked={selectedSources.includes(s.key)} onChange={() => toggleSource(s.key)} className="rounded" />
                  {s.label}
                </label>
              ))}
            </div>

            <div className="flex gap-3">
              <button className="btn-gradient btn-click" onClick={handleSearch} disabled={searching}>
                {searching ? "搜索中..." : "搜索"}
              </button>
              {results.length > 0 && (
                <button className="btn-ghost" onClick={() => { setReviewSource("search"); setTab("review"); }}>
                  生成综述 ({results.length} 篇)
                </button>
              )}
            </div>
            {stats && <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{stats}</p>}
          </div>

          {/* 结果 */}
          <div className="space-y-2">
            {results.map((p, i) => (
              <div key={i} className="glass-card p-4 space-y-2">
                <div className="flex items-start gap-3">
                  <span className="text-sm font-bold flex-shrink-0" style={{ color: "var(--accent-blue)" }}>[{i + 1}]</span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold break-words" style={{ color: "var(--text-primary)" }}>{p.title}</h3>
                    <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
                      {p.authors?.slice(0, 3).join(", ")} | {p.year} | {p.journal}
                    </p>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0"
                    style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>{p.source}</span>
                </div>
                {p.abstract && <p className="text-xs line-clamp-2" style={{ color: "var(--text-secondary)" }}>{p.abstract.slice(0, 200)}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI 综述 — Issue 3: 支持知识库数据源 */}
      {tab === "review" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-4">
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>选择综述数据源</p>

            {/* 数据源选择 */}
            <div className="flex gap-2">
              {[
                { key: "search", label: `搜索结果 (${results.length})` },
                { key: "kb", label: "知识库文献" },
                { key: "custom", label: "自定义输入" },
              ].map(opt => (
                <button key={opt.key}
                  onClick={() => setReviewSource(opt.key as any)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors"
                  style={reviewSource === opt.key
                    ? { background: "var(--accent-blue)", color: "#fff" }
                    : { background: "var(--hover-bg)", color: "var(--text-secondary)", border: "1px solid var(--border-color)" }
                  }
                >{opt.label}</button>
              ))}
            </div>

            {/* 知识库选择器 */}
            {reviewSource === "kb" && (
              <div className="space-y-2 max-h-48 overflow-y-auto rounded-lg p-3" style={{ border: "1px solid var(--border-color)" }}>
                {kbCards.length === 0 ? (
                  <p className="text-xs text-center py-2" style={{ color: "var(--text-muted)" }}>知识库中暂无文献卡片</p>
                ) : kbCards.map(card => (
                  <label key={card.id} className="flex items-start gap-2 cursor-pointer py-1">
                    <input type="checkbox" checked={selectedKbCards.includes(card.id)} onChange={() => toggleKbCard(card.id)} className="mt-1 rounded" />
                    <span className="text-xs" style={{ color: "var(--text-primary)" }}>{card.title}</span>
                  </label>
                ))}
                {selectedKbCards.length > 0 && (
                  <p className="text-xs pt-1" style={{ color: "var(--accent-blue)" }}>已选 {selectedKbCards.length} 篇</p>
                )}
              </div>
            )}

            {/* 自定义输入 */}
            {reviewSource === "custom" && (
              <textarea
                className="input-glass"
                rows={4}
                placeholder="粘贴 ai-literature JSON 数据或文献摘要..."
                value={reviewInput}
                onChange={e => setReviewInput(e.target.value)}
              />
            )}

            {/* 搜索结果提示 */}
            {reviewSource === "search" && (
              <p className="text-xs" style={{ color: results.length > 0 ? "var(--text-secondary)" : "#ef4444" }}>
                {results.length > 0 ? `将基于 ${results.length} 篇搜索结果生成综述` : "请先在「关键词检索」tab 中搜索文献"}
              </p>
            )}

            <button className="btn-gradient btn-click" onClick={handleReview} disabled={reviewing}>
              {reviewing ? "生成中..." : "生成综述"}
            </button>
          </div>
          {reviewContent && renderStreamingContent(reviewContent, reviewEndRef)}
        </div>
      )}

      {/* 选题讨论 */}
      {tab === "topic" && (
        <div className="space-y-4">
          <div className="glass-card p-5 space-y-3">
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>输入研究方向，AI 将生成选题建议</p>
            <textarea
              className="input-glass"
              rows={3}
              placeholder="例如：航天器姿态控制中的自适应鲁棒方法研究..."
              value={topicInput}
              onChange={e => setTopicInput(e.target.value)}
            />
            <button className="btn-gradient btn-click" onClick={handleDiscuss} disabled={discussing}>
              {discussing ? "讨论中..." : "开始讨论"}
            </button>
          </div>
          {topicContent && renderStreamingContent(topicContent, topicEndRef)}
        </div>
      )}

      {/* 历史记录 */}
      {tab === "history" && (
        <div className="space-y-2">
          {history.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <p style={{ color: "var(--text-muted)" }}>暂无搜索历史</p>
            </div>
          ) : history.map(record => {
            const isExpanded = expandedHistory === record.id;
            const papers = parseHistoryData(record.data);
            return (
              <div key={record.id} className="glass-card overflow-hidden">
                {/* 头部 — 点击展开/收起 */}
                <div className="p-4 flex items-center gap-3 cursor-pointer"
                  onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  onClick={() => {
                    if (expandedHistory === record.id) {
                      setExpandedHistory(null);
                    } else {
                      setExpandedHistory(record.id);
                    }
                  }}
                >
                  <span className="flex-shrink-0 transition-transform duration-200"
                    style={{ color: "var(--text-muted)", transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}>
                    <IconChevronRight size={14} />
                  </span>
                  <span className="flex-shrink-0" style={{ color: "var(--text-muted)" }}><IconSearch size={14} /></span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{record.query}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {papers.length || record.result_count} 篇结果 · {new Date(record.created_at).toLocaleString("zh-CN")}
                    </p>
                  </div>
                  <button className="text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-colors flex-shrink-0"
                    style={{ background: "var(--accent-blue)", color: "#fff" }}
                    onClick={e => { e.stopPropagation(); loadHistoryResults(record); }}
                  >加载到检索</button>
                </div>

                {/* 展开的文献列表 */}
                {isExpanded && (
                  <div style={{ borderTop: "1px solid var(--border-color)" }}>
                    {papers.length === 0 ? (
                      <div className="px-4 py-3 text-xs text-center" style={{ color: "var(--text-muted)" }}>
                        无详细数据（该记录可能在旧版本中创建）
                      </div>
                    ) : (
                      <div className="px-4 py-2 space-y-0 max-h-64 overflow-y-auto">
                        {papers.map((p: Paper, i: number) => (
                          <div key={i} className="flex items-start gap-3 py-2.5"
                            style={{ borderBottom: i < papers.length - 1 ? "1px solid var(--border-color)" : "none" }}>
                            <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: "var(--accent-blue)" }}>[{i + 1}]</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium break-words leading-relaxed" style={{ color: "var(--text-primary)" }}>{p.title}</p>
                              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                                {p.authors?.length > 0 && (
                                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                                    {p.authors.slice(0, 3).join(", ")}{p.authors.length > 3 ? " 等" : ""}
                                  </span>
                                )}
                                {p.year && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{p.year}</span>}
                                {p.journal && <span className="text-xs" style={{ color: "var(--text-muted)" }}>{p.journal}</span>}
                                {p.source && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>{p.source}</span>}
                              </div>
                              {p.abstract && (
                                <p className="text-xs mt-1 line-clamp-2" style={{ color: "var(--text-muted)" }}>{p.abstract}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="px-4 py-2 flex justify-end" style={{ borderTop: "1px solid var(--border-color)" }}>
                      <button className="text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
                        style={{ background: "var(--accent-blue)", color: "#fff" }}
                        onClick={() => loadHistoryResults(record)}
                      >加载全部到检索页面</button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function renderSimpleMarkdown(md: string): string {
  if (!md) return "";
  let result = md;
  result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');
  result = result.replace(/^- (.+)$/gm, '<li>$1</li>');
  result = result.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  result = result.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  result = result.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  result = result.replace(/\n\n/g, '</p><p>');
  result = result.replace(/\n/g, '<br>');
  return result;
}
