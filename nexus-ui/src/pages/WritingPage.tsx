import { useState, useEffect, useRef, useCallback } from "react";
import { writingApi, papersApi, type WritingDocument, type PaperDetail } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import {
  IconBook, IconPlus,
} from "../components/Icons";

// AI 操作类型
const AI_OPERATIONS = [
  { key: "polish", label: "润色", desc: "优化学术表达" },
  { key: "translate", label: "翻译", desc: "中英互译" },
  { key: "expand", label: "扩写", desc: "补充细节论证" },
  { key: "condense", label: "精简", desc: "压缩冗余内容" },
  { key: "latex", label: "LaTeX", desc: "转换为LaTeX格式" },
];

// 写作模板
const WRITING_TEMPLATES = [
  {
    key: "aiaa",
    label: "AIAA 论文",
    content: `# Title

## Abstract

[Your abstract here]

## Nomenclature

| Symbol | Description |
|--------|-------------|
| $x$    | State variable |

## 1. Introduction

Background and motivation...

## 2. Methodology

### 2.1 Problem Formulation

### 2.2 Proposed Approach

## 3. Results and Discussion

### 3.1 Simulation Setup

### 3.2 Comparison with Baseline

## 4. Conclusions

## References

`,
  },
  {
    key: "ieee",
    label: "IEEE 论文",
    content: `# Title

**Abstract—** [Your abstract here]

**Index Terms—** keyword1, keyword2, keyword3

## I. Introduction

## II. Related Work

## III. Proposed Method

### A. Problem Definition

### B. Algorithm Design

## IV. Experiments

### A. Dataset

### B. Results

## V. Conclusion

## References

`,
  },
  {
    key: "report",
    label: "研究报告",
    content: `# 报告标题

> 日期: ${new Date().toLocaleDateString()}

## 1. 研究背景

## 2. 研究目标

## 3. 研究方法

## 4. 实验结果

## 5. 结论与展望

## 参考文献

`,
  },
  {
    key: "review",
    label: "文献综述",
    content: `# 综述标题

## 摘要

## 1. 引言

## 2. 研究现状

### 2.1 方法一

### 2.2 方法二

## 3. 方法对比

## 4. 研究趋势

## 5. 结论

## 参考文献

`,
  },
];

export default function WritingPage() {
  const [documents, setDocuments] = useState<WritingDocument[]>([]);
  const [activeDoc, setActiveDoc] = useState<WritingDocument | null>(null);
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [linkedPapers, setLinkedPapers] = useState<PaperDetail[]>([]);
  const [showPaperSearch, setShowPaperSearch] = useState(false);
  const [paperQuery, setPaperQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Pick<PaperDetail, "id" | "title" | "authors" | "year">[]>([]);

  // AI panel state
  const [aiResult, setAiResult] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedText, setSelectedText] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [wordCount, setWordCount] = useState(0);

  const editorRef = useRef<HTMLTextAreaElement>(null);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const contentRef = useRef(content);
  const titleRef = useRef(title);
  const activeDocRef = useRef(activeDoc);

  // Keep refs in sync
  useEffect(() => { contentRef.current = content; }, [content]);
  useEffect(() => { titleRef.current = title; }, [title]);
  useEffect(() => { activeDocRef.current = activeDoc; }, [activeDoc]);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const res = await writingApi.list();
      setDocuments((res as any).documents || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  // Load linked papers when active doc changes
  useEffect(() => {
    if (activeDoc?.linked_paper_ids?.length) {
      Promise.all(activeDoc.linked_paper_ids.map(id => papersApi.get(id).catch(() => null)))
        .then(papers => setLinkedPapers(papers.filter(Boolean) as PaperDetail[]));
    } else {
      setLinkedPapers([]);
    }
  }, [activeDoc?.linked_paper_ids]);

  // Auto-save debounce
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(() => {
      if (activeDoc) {
        writingApi.update(activeDoc.id, { content, title }).catch(console.error);
      }
    }, 2000);
  }, [activeDoc, content, title]);

  useEffect(() => {
    scheduleAutoSave();
    return () => { if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current); };
  }, [content, title, scheduleAutoSave]);

  // Save immediately when content/title changes (debounced)
  // Also save on component unmount to prevent data loss on page switch
  useEffect(() => {
    return () => {
      // Save on unmount (page switch) using refs for latest values
      const doc = activeDocRef.current;
      const c = contentRef.current;
      const t = titleRef.current;
      if (doc && (c || t)) {
        writingApi.update(doc.id, { content: c, title: t }).catch(console.error);
      }
    };
  }, []); // Only run on unmount

  // Update word count
  useEffect(() => {
    setWordCount(content.length);
  }, [content]);

  const handleNewDocument = async (templateKey?: string) => {
    const template = templateKey ? WRITING_TEMPLATES.find(t => t.key === templateKey) : null;
    const docTitle = template ? template.label + " - 新文档" : "无标题文档";
    const docContent = template ? template.content : "";
    try {
      const res = await writingApi.create({ title: docTitle, content: docContent });
      const newDoc: WritingDocument = {
        id: (res as any).id,
        title: docTitle,
        content: docContent,
        outline: [],
        linked_paper_ids: [],
        document_type: "paper",
        word_count: docContent.length,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setDocuments(prev => [newDoc, ...prev]);
      setActiveDoc(newDoc);
      setTitle(docTitle);
      setContent(docContent);
    } catch (err) {
      console.error("Failed to create document:", err);
    }
  };

  const handleSelectDoc = async (doc: WritingDocument) => {
    try {
      const full = await writingApi.get(doc.id) as any;
      setActiveDoc(full);
      setTitle(full.title);
      setContent(full.content || "");
    } catch (err) {
      console.error("Failed to load document:", err);
    }
  };

  const handleDeleteDoc = async (id: string) => {
    if (!confirm("确定删除此文档？")) return;
    try {
      await writingApi.delete(id);
      setDocuments(prev => prev.filter(d => d.id !== id));
      if (activeDoc?.id === id) {
        setActiveDoc(null);
        setTitle("");
        setContent("");
      }
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const handleAiOperation = async (operation: string) => {
    if (!activeDoc) return;
    const text = selectedText || content;
    if (!text.trim()) {
      alert("请先选中文本或在编辑器中输入内容");
      return;
    }

    setAiLoading(true);
    setAiResult("");
    try {
      const res = await writingApi.aiOperation(activeDoc.id, operation, text.slice(0, 8000));
      const data = res as any;
      if (data.error) {
        setAiResult(`❌ ${data.error}`);
      } else {
        setAiResult(data.result || "");
      }
    } catch (err) {
      setAiResult(`❌ 请求失败: ${err}`);
    } finally {
      setAiLoading(false);
    }
  };

  const handleCustomAi = async () => {
    if (!activeDoc || !customPrompt.trim()) return;
    const text = selectedText || content;
    if (!text.trim()) {
      alert("请先选中文本或在编辑器中输入内容");
      return;
    }

    setAiLoading(true);
    setAiResult("");
    try {
      const res = await writingApi.aiOperation(activeDoc.id, "custom", `${customPrompt}\n\n${text.slice(0, 6000)}`);
      const data = res as any;
      if (data.error) {
        setAiResult(`❌ ${data.error}`);
      } else {
        setAiResult(data.result || "");
      }
    } catch (err) {
      setAiResult(`❌ 请求失败: ${err}`);
    } finally {
      setAiLoading(false);
    }
  };

  const handleInsertAiResult = () => {
    if (!aiResult || !editorRef.current) return;
    const start = editorRef.current.selectionStart;
    const end = editorRef.current.selectionEnd;
    const before = content.slice(0, start);
    const after = content.slice(end);
    setContent(before + aiResult + after);
    setAiResult("");
  };

  const handleSearchPapers = async () => {
    if (!paperQuery.trim()) return;
    try {
      const results = await papersApi.searchMention(paperQuery, 8);
      setSearchResults(results as any);
    } catch {
      setSearchResults([]);
    }
  };

  const handleLinkPaper = async (paperId: string) => {
    if (!activeDoc) return;
    try {
      const res = await writingApi.linkPaper(activeDoc.id, paperId) as any;
      setActiveDoc(prev => prev ? { ...prev, linked_paper_ids: res.linked_paper_ids } : null);
      const paper = await papersApi.get(paperId);
      setLinkedPapers(prev => [...prev, paper as any]);
      setShowPaperSearch(false);
      setPaperQuery("");
    } catch (err) {
      console.error("Failed to link paper:", err);
    }
  };

  const handleInsertCitation = (index: number, _paper: PaperDetail) => {
    if (!editorRef.current) return;
    const start = editorRef.current.selectionStart;
    const before = content.slice(0, start);
    const after = content.slice(start);
    setContent(before + `[${index}]` + after);
  };

  const handleGetSelection = () => {
    if (!editorRef.current) return;
    const start = editorRef.current.selectionStart;
    const end = editorRef.current.selectionEnd;
    setSelectedText(content.slice(start, end));
  };

  const handleExportMarkdown = async () => {
    if (!activeDoc) return;
    try {
      const res = await writingApi.exportDoc(activeDoc.id, "markdown") as any;
      if (res.error) { alert("导出失败: " + res.error); return; }
      const blob = new Blob([res.content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = res.filename || `${title}.md`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { alert("导出失败: " + err); }
  };

  const handleExportDocx = async () => {
    if (!activeDoc) return;
    try {
      const res = await writingApi.exportDoc(activeDoc.id, "docx") as any;
      if (res.error) { alert("导出失败: " + res.error); return; }
      // base64 解码
      const binary = atob(res.content);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = res.filename || `${title}.docx`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { alert("导出失败: " + err); }
  };

  return (
    <div className="flex h-full gap-3">
      {/* Left Panel — Document List + Sources */}
      <div className="w-60 flex-shrink-0 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>写作工作台</h3>
          <div className="flex gap-1">
            <select className="text-[10px] bg-transparent border-none outline-none cursor-pointer"
              style={{ color: "var(--text-muted)" }}
              value=""
              onChange={e => { if (e.target.value) handleNewDocument(e.target.value); e.target.value = ""; }}>
              <option value="" disabled>模板</option>
              {WRITING_TEMPLATES.map(t => (
                <option key={t.key} value={t.key}>{t.label}</option>
              ))}
            </select>
            <button className="w-6 h-6 rounded-lg flex items-center justify-center cursor-pointer transition-colors"
              style={{ color: "var(--accent-blue)" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              onClick={() => handleNewDocument()}>
              <IconPlus size={14} />
            </button>
          </div>
        </div>

        {/* Document List */}
        <div className="flex-1 space-y-1 overflow-y-auto">
          {documents.map(doc => (
            <div key={doc.id}
              className="px-3 py-2 rounded-xl text-sm cursor-pointer transition-all group"
              style={activeDoc?.id === doc.id
                ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)", fontWeight: 500 }
                : { color: "var(--text-secondary)" }
              }
              onMouseEnter={e => { if (activeDoc?.id !== doc.id) e.currentTarget.style.background = "var(--hover-bg)"; }}
              onMouseLeave={e => { if (activeDoc?.id !== doc.id) e.currentTarget.style.background = "transparent"; }}
              onClick={() => handleSelectDoc(doc)}>
              <div className="flex items-center justify-between">
                <span className="truncate flex-1">{doc.title || "无标题文档"}</span>
                <button className="opacity-0 group-hover:opacity-100 transition-opacity p-1 cursor-pointer"
                  onClick={(e) => { e.stopPropagation(); handleDeleteDoc(doc.id); }}
                  style={{ color: "var(--text-muted)" }}>
                  ✕
                </button>
              </div>
              <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                {doc.word_count} 字 · {new Date(doc.updated_at).toLocaleDateString()}
              </p>
            </div>
          ))}
          {documents.length === 0 && (
            <p className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>
              点击 + 创建新文档
            </p>
          )}
        </div>

        {/* Linked Papers */}
        {activeDoc && (
          <div className="glass-card p-2 space-y-1.5">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>关联文献</p>
              <button className="text-[10px] cursor-pointer" style={{ color: "var(--accent-blue)" }}
                onClick={() => setShowPaperSearch(!showPaperSearch)}>
                {showPaperSearch ? "取消" : "+ 添加"}
              </button>
            </div>
            {showPaperSearch && (
              <div className="space-y-1.5">
                <div className="flex gap-1">
                  <input className="input-glass text-[10px] flex-1 py-1" placeholder="搜索文献..."
                    value={paperQuery} onChange={e => setPaperQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSearchPapers()} />
                  <button className="btn-ghost text-[10px] py-1 px-2" onClick={handleSearchPapers}>搜索</button>
                </div>
                {searchResults.length > 0 && (
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {searchResults.map(p => (
                      <div key={p.id} className="px-2 py-1 rounded text-[10px] cursor-pointer"
                        style={{ color: "var(--text-secondary)" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                        onClick={() => handleLinkPaper(p.id)}>
                        <p className="truncate font-medium">{p.title}</p>
                        <p style={{ color: "var(--text-muted)" }}>{p.authors?.slice(0, 2).join(", ")} · {p.year}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {linkedPapers.length > 0 ? (
              <div className="space-y-1">
                {linkedPapers.map((p, i) => (
                  <div key={p.id} className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] group"
                    style={{ color: "var(--text-secondary)" }}>
                    <span className="cursor-pointer flex-shrink-0" style={{ color: "var(--accent-blue)" }}
                      title="插入引用" onClick={() => handleInsertCitation(i + 1, p)}>[{i + 1}]</span>
                    <span className="truncate flex-1">{p.title}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>暂无关联文献</p>
            )}
          </div>
        )}
      </div>

      {/* Center — Editor */}
      <div className="flex-1 flex flex-col min-w-0 gap-2">
        {activeDoc ? (
          <>
            {/* Title + Toolbar */}
            <div className="flex items-center gap-2">
              <input className="flex-1 bg-transparent border-none outline-none text-lg font-bold"
                style={{ color: "var(--text-primary)" }}
                value={title} onChange={e => setTitle(e.target.value)} placeholder="文档标题" />
              <div className="flex gap-1">
                <button className="btn-ghost text-[10px] py-1 px-2"
                  style={showPreview ? { background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" } : {}}
                  onClick={() => setShowPreview(!showPreview)}>
                  {showPreview ? "编辑" : "预览"}
                </button>
                <div className="relative group">
                  <button className="btn-ghost text-[10px] py-1 px-2"
                    style={{ color: "var(--accent-green)" }}>
                    导出 ▾
                  </button>
                  <div className="absolute right-0 top-full mt-1 glass-card p-1 min-w-[100px] z-50 hidden group-hover:block"
                    style={{ border: "1px solid var(--border-color)" }}>
                    <button className="block w-full text-left px-2 py-1 text-[10px] rounded cursor-pointer transition-colors"
                      style={{ color: "var(--text-secondary)" }}
                      onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                      onClick={handleExportMarkdown}>Markdown</button>
                    <button className="block w-full text-left px-2 py-1 text-[10px] rounded cursor-pointer transition-colors"
                      style={{ color: "var(--text-secondary)" }}
                      onMouseEnter={e => (e.currentTarget.style.background = "var(--hover-bg)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                      onClick={handleExportDocx}>DOCX</button>
                  </div>
                </div>
              </div>
            </div>

            {/* Format Toolbar */}
            <div className="flex gap-1 flex-wrap">
              {[
                { label: "B", action: () => insertMarkdown("**", "**"), title: "加粗" },
                { label: "I", action: () => insertMarkdown("*", "*"), title: "斜体" },
                { label: "H1", action: () => insertMarkdown("# ", ""), title: "一级标题" },
                { label: "H2", action: () => insertMarkdown("## ", ""), title: "二级标题" },
                { label: "H3", action: () => insertMarkdown("### ", ""), title: "三级标题" },
                { label: "引用", action: () => insertMarkdown("> ", ""), title: "引用" },
                { label: "代码", action: () => insertMarkdown("```\n", "\n```"), title: "代码块" },
                { label: "列表", action: () => insertMarkdown("- ", ""), title: "无序列表" },
                { label: "公式", action: () => insertMarkdown("$$\n", "\n$$"), title: "数学公式" },
                { label: "表格", action: () => insertMarkdown("| 列1 | 列2 |\n|---|---|\n| ", " | |\n"), title: "表格" },
              ].map(btn => (
                <button key={btn.label}
                  className="px-2 py-1 rounded text-[10px] cursor-pointer transition-colors"
                  style={{ color: "var(--text-secondary)", background: "var(--hover-bg)" }}
                  title={btn.title}
                  onMouseEnter={e => (e.currentTarget.style.color = "var(--accent-blue)")}
                  onMouseLeave={e => (e.currentTarget.style.color = "var(--text-secondary)")}
                  onClick={btn.action}>
                  {btn.label}
                </button>
              ))}
              <span className="flex-1" />
              <span className="text-[10px] py-1" style={{ color: "var(--text-muted)" }}>
                {wordCount} 字
              </span>
            </div>

            {/* Editor / Preview */}
            {showPreview ? (
              <div className="flex-1 rounded-xl overflow-y-auto p-6"
                style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)", lineHeight: 1.8 }}>
                <div className="max-w-3xl mx-auto writing-preview">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {content}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              <textarea ref={editorRef}
                className="flex-1 rounded-xl p-6 resize-none outline-none"
                style={{
                  background: "var(--glass-bg)",
                  border: "1px solid var(--glass-border)",
                  color: "var(--text-primary)",
                  lineHeight: 1.8,
                  fontFamily: "'Open Sans', system-ui, sans-serif",
                  fontSize: "14px",
                }}
                value={content}
                onChange={e => setContent(e.target.value)}
                onMouseUp={handleGetSelection}
                placeholder="开始写作..."
              />
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="glass-card p-12 text-center space-y-4">
              <IconBook size={48} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
              <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>写作工作台</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>选择或创建一个文档开始写作</p>
              <button className="btn-gradient btn-click text-xs" onClick={() => handleNewDocument()}>
                新建文档
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Right Panel — AI Assistant */}
      {activeDoc && (
        <div className="w-72 flex-shrink-0 flex flex-col gap-2">
          <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>AI 助手</h3>

          {/* Quick Actions */}
          <div className="glass-card p-2 space-y-1.5">
            <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>快捷操作</p>
            <div className="grid grid-cols-2 gap-1.5">
              {AI_OPERATIONS.map(op => (
                <button key={op.key}
                  className="px-2 py-1.5 rounded-lg text-[11px] cursor-pointer transition-all text-left"
                  style={{ color: "var(--text-secondary)", background: "var(--hover-bg)" }}
                  onMouseEnter={e => { e.currentTarget.style.color = "var(--accent-blue)"; e.currentTarget.style.background = "rgba(59,130,246,0.08)"; }}
                  onMouseLeave={e => { e.currentTarget.style.color = "var(--text-secondary)"; e.currentTarget.style.background = "var(--hover-bg)"; }}
                  onClick={() => handleAiOperation(op.key)}
                  disabled={aiLoading}>
                  <p className="font-medium">{op.label}</p>
                  <p className="text-[9px]" style={{ color: "var(--text-muted)" }}>{op.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Prompt */}
          <div className="glass-card p-2 space-y-1.5">
            <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>自定义指令</p>
            <textarea className="w-full bg-transparent border-none outline-none resize-none text-xs"
              style={{ color: "var(--text-primary)" }}
              rows={2} placeholder="输入自定义 AI 指令..."
              value={customPrompt} onChange={e => setCustomPrompt(e.target.value)} />
            <button className="btn-ghost text-[10px] w-full py-1.5" onClick={handleCustomAi} disabled={aiLoading}>
              {aiLoading ? "生成中..." : "执行"}
            </button>
          </div>

          {/* Selected Text */}
          {selectedText && (
            <div className="glass-card p-2">
              <p className="text-[10px] font-semibold mb-1" style={{ color: "var(--text-muted)" }}>选中文本</p>
              <p className="text-[10px] line-clamp-3" style={{ color: "var(--text-secondary)" }}>{selectedText}</p>
            </div>
          )}

          {/* AI Result */}
          {(aiResult || aiLoading) && (
            <div className="glass-card p-2 flex-1 min-h-0 flex flex-col">
              <div className="flex items-center justify-between mb-1">
                <p className="text-[10px] font-semibold" style={{ color: "var(--text-muted)" }}>AI 输出</p>
                {aiResult && (
                  <div className="flex gap-1">
                    <button className="text-[10px] cursor-pointer" style={{ color: "var(--accent-blue)" }}
                      onClick={handleInsertAiResult}>插入</button>
                    <button className="text-[10px] cursor-pointer" style={{ color: "var(--text-muted)" }}
                      onClick={() => navigator.clipboard.writeText(aiResult)}>复制</button>
                  </div>
                )}
              </div>
              <div className="flex-1 overflow-y-auto text-xs" style={{ color: "var(--text-secondary)", lineHeight: 1.7 }}>
                {aiLoading ? (
                  <div className="flex items-center gap-2 py-4 justify-center">
                    <span className="stream-cursor">▊</span>
                    <span style={{ color: "var(--text-muted)" }}>生成中...</span>
                  </div>
                ) : (
                  <div className="writing-preview">
                    <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {aiResult}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  function insertMarkdown(before: string, after: string) {
    if (!editorRef.current) return;
    const start = editorRef.current.selectionStart;
    const end = editorRef.current.selectionEnd;
    const selected = content.slice(start, end);
    const newContent = content.slice(0, start) + before + selected + after + content.slice(end);
    setContent(newContent);
    // Restore cursor position
    setTimeout(() => {
      if (editorRef.current) {
        editorRef.current.selectionStart = start + before.length;
        editorRef.current.selectionEnd = start + before.length + selected.length;
        editorRef.current.focus();
      }
    }, 0);
  }
}
