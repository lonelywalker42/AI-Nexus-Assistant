import { useState, useEffect, useRef, useCallback } from "react";
import { IconBookOpen, IconBook, IconSearch, IconFolder, IconArrowLeft, IconChevronLeft, IconChevronRight, IconSun } from "../components/Icons";
import JSZip from "jszip";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import * as pdfjsLib from "pdfjs-dist";

// Set pdf.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

// Safe base64 conversion — avoids call stack overflow for large buffers
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, chunk as unknown as number[]);
  }
  return btoa(binary);
}

// EPUB parser using JSZip (no iframe/blob URL issues)
interface EpubChapter {
  title: string;
  content: string; // HTML content
}

interface EpubData {
  title: string;
  author: string;
  description: string;
  coverUrl: string | null;
  chapters: EpubChapter[];
}

async function parseEpub(file: File): Promise<EpubData> {
  const zip = await JSZip.loadAsync(await file.arrayBuffer());

  // 1. Find container.xml to locate OPF
  const containerXml = await zip.file("META-INF/container.xml")?.async("text");
  if (!containerXml) throw new Error("Invalid EPUB: no container.xml");

  const opfPathMatch = containerXml.match(/full-path="([^"]+)"/);
  if (!opfPathMatch) throw new Error("Invalid EPUB: no OPF path");
  const opfPath = opfPathMatch[1];
  const opfDir = opfPath.substring(0, opfPath.lastIndexOf("/") + 1);

  // 2. Parse OPF
  const opfContent = await zip.file(opfPath)?.async("text");
  if (!opfContent) throw new Error("Invalid EPUB: no OPF file");

  // Extract metadata
  const titleMatch = opfContent.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/);
  const authorMatch = opfContent.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/);
  const descMatch = opfContent.match(/<dc:description[^>]*>([^<]+)<\/dc:description>/);

  // Extract cover image
  let coverUrl: string | null = null;
  const coverMetaMatch = opfContent.match(/name="cover"\s+content="([^"]+)"/);
  if (coverMetaMatch) {
    const coverId = coverMetaMatch[1];
    const coverItemMatch = opfContent.match(new RegExp(`id="${coverId}"[^>]*href="([^"]+)"`));
    if (coverItemMatch) {
      const coverPath = opfDir + coverItemMatch[1];
      const coverFile = zip.file(coverPath);
      if (coverFile) {
        try {
          const coverBuf = await coverFile.async("arraybuffer");
          const ext = coverPath.split(".").pop()?.toLowerCase() || "jpg";
          const mime = ext === "png" ? "image/png" : "image/jpeg";
          coverUrl = `data:${mime};base64,${arrayBufferToBase64(coverBuf)}`;
        } catch {}
      }
    }
  }

  // Extract spine (reading order) and manifest — attribute-order agnostic
  const manifestItems: Record<string, string> = {};
  const itemTagRegex = /<item\s[^>]*?\/>/g;
  let m;
  while ((m = itemTagRegex.exec(opfContent)) !== null) {
    const tag = m[0];
    const idMatch = tag.match(/\bid="([^"]+)"/);
    const hrefMatch = tag.match(/\bhref="([^"]+)"/);
    if (idMatch && hrefMatch) {
      manifestItems[idMatch[1]] = opfDir + hrefMatch[1];
    }
  }

  const spineIds: string[] = [];
  const spineRegex = /<itemref\s[^>]*?idref="([^"]+)"[^>]*?\/?>/g;
  while ((m = spineRegex.exec(opfContent)) !== null) {
    spineIds.push(m[1]);
  }

  // 3. Load chapters
  const chapters: EpubChapter[] = [];
  for (const id of spineIds) {
    const href = manifestItems[id];
    if (!href) continue;
    const ext = href.split(".").pop()?.toLowerCase();
    if (ext !== "xhtml" && ext !== "html" && ext !== "htm") continue;

    const zipFile = zip.file(href);
    if (!zipFile) continue;

    let html = await zipFile.async("text");

    // Extract chapter title from <title> or first <h1>-<h3>
    const titleTagMatch = html.match(/<title[^>]*>([^<]+)<\/title>/);
    const hMatch = html.match(/<h[1-3][^>]*>([^<]+)<\/h[1-3]>/);
    const chapterTitle = hMatch?.[1] || titleTagMatch?.[1] || `Chapter ${chapters.length + 1}`;

    // Convert relative image paths to data URLs (chunked to avoid stack overflow)
    const imgRegex = /src="([^"]+)"/g;
    let imgMatch;
    const imgReplacements: [string, string][] = [];
    while ((imgMatch = imgRegex.exec(html)) !== null) {
      const imgSrc = imgMatch[1];
      if (imgSrc.startsWith("http") || imgSrc.startsWith("data:")) continue;
      const imgPath = opfDir + imgSrc;
      const imgFile = zip.file(imgPath);
      if (imgFile) {
        try {
          const imgBuf = await imgFile.async("arraybuffer");
          const imgExt = imgPath.split(".").pop()?.toLowerCase() || "jpg";
          const imgMime = imgExt === "png" ? "image/png" : imgExt === "gif" ? "image/gif" : "image/jpeg";
          imgReplacements.push([imgSrc, `data:${imgMime};base64,${arrayBufferToBase64(imgBuf)}`]);
        } catch {}
      }
    }
    for (const [orig, dataUrl] of imgReplacements) {
      html = html.replace(new RegExp(`src="${orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`, 'g'), `src="${dataUrl}"`);
    }

    // Strip <html>, <head>, <body> tags to get just the content
    // Use non-greedy match to avoid capturing nested body tags
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    let chapterContent = bodyMatch ? bodyMatch[1].trim() : html;

    // If content is empty or too short, try to extract meaningful content
    if (!chapterContent || chapterContent.replace(/<[^>]*>/g, '').trim().length < 10) {
      // Try extracting from <div> or <section> if body is empty
      const divMatch = html.match(/<(?:div|section)[^>]*>([\s\S]*?)<\/(?:div|section)>/i);
      chapterContent = divMatch ? divMatch[1].trim() : html;
    }

    // Only add chapter if it has meaningful content
    if (chapterContent && chapterContent.replace(/<[^>]*>/g, '').trim().length > 0) {
      chapters.push({ title: chapterTitle, content: chapterContent });
    }
  }

  // If no chapters were extracted, try a fallback approach
  if (chapters.length === 0) {
    throw new Error("No readable chapters found in EPUB");
  }

  return {
    title: titleMatch?.[1] || file.name.replace(/\.epub$/i, ""),
    author: authorMatch?.[1] || "Unknown",
    description: descMatch?.[1] || "",
    coverUrl,
    chapters,
  };
}

interface Book {
  name: string;
  file: File;
  path?: string;
  type: string;
  size: number;
  title?: string;
  author?: string;
  description?: string;
  coverUrl?: string;
}

type ViewMode = "shelf" | "detail" | "reader";

// Text/Markdown file data for reader
interface TextFileData {
  content: string;
  isMarkdown: boolean;
}

// IndexedDB helpers — Promise-based, lazy loading
const DB_NAME = "nexus-books";
const DB_VER = 1;
const META_KEY = "nexus-books-meta";

function getDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = (e) => {
      const d = (e.target as IDBOpenDBRequest).result;
      if (!d.objectStoreNames.contains("books")) d.createObjectStore("books", { keyPath: "name" });
    };
    req.onsuccess = (e) => resolve((e.target as IDBOpenDBRequest).result);
    req.onerror = () => reject(req.error);
  });
}

async function saveBooksToDB(books: Book[]) {
  const entries = await Promise.all(books.map(async (b) => ({
    name: b.name, type: b.type, size: b.size, data: await b.file.arrayBuffer(),
  })));
  const db = await getDB();
  const tx = db.transaction("books", "readwrite");
  const store = tx.objectStore("books");
  store.clear();
  for (const entry of entries) {
    store.put(entry);
  }
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(new Error("transaction aborted"));
  });
  // Save metadata to localStorage for fast mount
  const meta = books.map(b => ({ name: b.name, type: b.type, size: b.size }));
  localStorage.setItem(META_KEY, JSON.stringify(meta));
}

// Fast load: metadata from localStorage (no ArrayBuffer)
function loadBookMetaFromStorage(): Array<{name: string; type: string; size: number}> {
  try { return JSON.parse(localStorage.getItem(META_KEY) || "[]"); } catch { return []; }
}

// Load single book's file from IndexedDB (on-demand)
async function loadBookFile(name: string): Promise<File | null> {
  const db = await getDB();
  const tx = db.transaction("books", "readonly");
  const store = tx.objectStore("books");
  return new Promise((resolve) => {
    const req = store.get(name);
    req.onsuccess = () => {
      const e = req.result;
      resolve(e ? new File([e.data], e.name, { type: e.type }) : null);
    };
    req.onerror = () => resolve(null);
  });
}

async function extractBookMetadata(book: Book): Promise<Partial<Book>> {
  if (!book.name.toLowerCase().endsWith(".epub")) return {};
  try {
    const epub = await parseEpub(book.file);
    return {
      title: epub.title || undefined,
      author: epub.author || undefined,
      description: epub.description ? epub.description.slice(0, 500) : undefined,
      coverUrl: epub.coverUrl || undefined,
    };
  } catch { return {}; }
}

// Book Spine Component — glassmorphism + theme-aware
const SPINE_PALETTES = [
  { bg: 'linear-gradient(135deg, #3b82f6, #2563eb)', glow: 'rgba(59,130,246,0.3)' },
  { bg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)', glow: 'rgba(139,92,246,0.3)' },
  { bg: 'linear-gradient(135deg, #ec4899, #db2777)', glow: 'rgba(236,72,153,0.3)' },
  { bg: 'linear-gradient(135deg, #f59e0b, #d97706)', glow: 'rgba(245,158,11,0.3)' },
  { bg: 'linear-gradient(135deg, #10b981, #059669)', glow: 'rgba(16,185,129,0.3)' },
  { bg: 'linear-gradient(135deg, #06b6d4, #0891b2)', glow: 'rgba(6,182,212,0.3)' },
  { bg: 'linear-gradient(135deg, #ef4444, #dc2626)', glow: 'rgba(239,68,68,0.3)' },
  { bg: 'linear-gradient(135deg, #6366f1, #4f46e5)', glow: 'rgba(99,102,241,0.3)' },
];

function BookSpine({ book, index, onClick }: { book: Book; index: number; onClick: () => void }) {
  const palette = SPINE_PALETTES[index % SPINE_PALETTES.length];
  const shortTitle = (book.title || book.name.replace(/\.[^.]+$/, "")).slice(0, 12);

  return (
    <div className="book-spine-wrapper cursor-pointer group" onClick={onClick}
      tabIndex={0} role="button"
      onKeyDown={e => { if (e.key === 'Enter') onClick(); }}>
      <div className="book-spine" style={{ background: palette.bg }}>
        <div className="book-spine-title">{shortTitle}</div>
        <div className="book-spine-shine" />
      </div>
      <div className="book-spine-shadow" style={{ background: palette.glow }} />
    </div>
  );
}

// PDF Viewer Component — renders PDF pages directly using canvas
function PdfViewer({ file, pageNum, onTotalPages }: { file: File; pageNum: number; onTotalPages: (n: number) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [rendering, setRendering] = useState(false);

  // Load PDF document
  useEffect(() => {
    let cancelled = false;
    const loadPdf = async () => {
      try {
        const arrayBuffer = await file.arrayBuffer();
        if (cancelled) return;
        const doc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        if (cancelled) return;
        setPdfDoc(doc);
        onTotalPages(doc.numPages);
      } catch (err) {
        console.error("Failed to load PDF:", err);
      }
    };
    loadPdf();
    return () => { cancelled = true; };
  }, [file]);

  // Render current page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current || rendering) return;
    let cancelled = false;

    const renderPage = async () => {
      setRendering(true);
      try {
        const page = await pdfDoc.getPage(pageNum + 1); // 1-indexed
        if (cancelled) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const container = canvas.parentElement;
        if (!container) return;

        const containerWidth = container.clientWidth;
        const viewport = page.getViewport({ scale: 1 });
        const scale = containerWidth / viewport.width;
        const scaledViewport = page.getViewport({ scale });

        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        await page.render({ canvasContext: ctx, viewport: scaledViewport, canvas } as any).promise;
      } catch (err) {
        console.error("Failed to render PDF page:", err);
      }
      setRendering(false);
    };

    renderPage();
    return () => { cancelled = true; };
  }, [pdfDoc, pageNum]);

  return (
    <div className="w-full h-full flex items-center justify-center overflow-auto">
      <canvas ref={canvasRef} style={{ maxWidth: "100%", height: "auto" }} />
    </div>
  );
}

export default function BookshelfPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("shelf");
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [epubData, setEpubData] = useState<EpubData | null>(null);
  const [textFileData, setTextFileData] = useState<TextFileData | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfTotalPages, setPdfTotalPages] = useState(0);
  const [chapterIdx, setChapterIdx] = useState(0);
  const [fontSize, setFontSize] = useState(100);
  const [pageIdx, setPageIdx] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [eyeProtection, setEyeProtection] = useState(() => localStorage.getItem("nexus-reader-eye-protect") === "true");
  const [flipDirection, setFlipDirection] = useState<"left" | "right" | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const readerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Calculate total pages when content changes (for EPUB/TXT/MD only)
  useEffect(() => {
    if (pdfFile) return; // PDF handles its own pagination
    setPageIdx(0);
    const timer = setTimeout(() => {
      if (contentRef.current && readerRef.current) {
        const contentH = contentRef.current.scrollHeight;
        const containerH = readerRef.current.clientHeight;
        const pages = Math.max(1, Math.ceil(contentH / containerH));
        setTotalPages(pages);
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [chapterIdx, epubData, textFileData, fontSize, pdfFile]);

  // Scroll to current page
  useEffect(() => {
    if (pdfFile) return; // PDF uses canvas, no scrolling
    if (readerRef.current) {
      const containerH = readerRef.current.clientHeight;
      readerRef.current.scrollTo({ top: pageIdx * containerH, behavior: 'smooth' });
    }
  }, [pageIdx, pdfFile]);

  // Persist eye protection mode
  useEffect(() => {
    localStorage.setItem("nexus-reader-eye-protect", String(eyeProtection));
  }, [eyeProtection]);

  // Page flip animation handler
  const flipPage = useCallback((direction: "left" | "right") => {
    if (direction === "right" && pageIdx >= totalPages - 1) return;
    if (direction === "left" && pageIdx === 0) return;
    setFlipDirection(direction);
    setTimeout(() => {
      if (direction === "right") setPageIdx(p => Math.min(totalPages - 1, p + 1));
      else setPageIdx(p => Math.max(0, p - 1));
      setFlipDirection(null);
    }, 300);
  }, [pageIdx, totalPages]);

  // Keyboard navigation for page flip
  useEffect(() => {
    if (viewMode !== "reader") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); flipPage("left"); }
      if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === " ") { e.preventDefault(); flipPage("right"); }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [viewMode, pageIdx, totalPages, flipPage]);

  // Load book metadata from localStorage on mount (fast)
  useEffect(() => {
    const meta = loadBookMetaFromStorage();
    if (meta.length > 0) {
      const placeholderBooks: Book[] = meta.map(m => ({
        name: m.name, file: null as any, type: m.type, size: m.size,
      }));
      setBooks(placeholderBooks);
    }
  }, []);

  const handleFolderLoad = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
      .filter((f) => /\.(epub|pdf|txt|md)$/i.test(f.name))
      .sort((a, b) => a.name.localeCompare(b.name, "zh"));
    if (files.length === 0) return;
    const newBooks: Book[] = files.map((f) => ({
      name: f.name, file: f, type: f.type, size: f.size,
    }));
    setBooks(newBooks);
    saveBooksToDB(newBooks);
    // Extract metadata
    for (let i = 0; i < newBooks.length; i++) {
      const meta = await extractBookMetadata(newBooks[i]);
      setBooks((prev) => prev.map((b, j) => j === i ? { ...b, ...meta } : b));
    }
    e.target.value = "";
  };

  const openDetail = async (book: Book) => {
    // Load file from IndexedDB if placeholder
    if (!book.file) {
      const file = await loadBookFile(book.name);
      if (file) {
        book = { ...book, file };
        setBooks(prev => prev.map(b => b.name === book.name ? book : b));
      }
    }
    setSelectedBook(book);
    setViewMode("detail");
  };

  const openReader = async () => {
    if (!selectedBook) return;

    // Load file from IndexedDB if placeholder (fixes no-content bug)
    let book = selectedBook;
    if (!book.file) {
      const file = await loadBookFile(book.name);
      if (file) {
        book = { ...book, file };
        setBooks(prev => prev.map(b => b.name === book.name ? book : b));
        setSelectedBook(book);
      } else {
        alert("无法加载文件，请重新导入书籍文件夹。");
        return;
      }
    }

    const nameLower = book.name.toLowerCase();

    if (nameLower.endsWith(".epub")) {
      // Parse EPUB using JSZip
      try {
        const data = await parseEpub(book.file);
        if (data.chapters.length === 0) {
          alert("未能从 EPUB 中提取到章节内容，文件可能格式异常。");
          return;
        }
        setEpubData(data);
        setTextFileData(null);
        setPdfFile(null);
        setChapterIdx(0);
        setViewMode("reader");
      } catch (err) {
        console.error("EPUB parse error:", err);
        alert("Failed to parse EPUB: " + (err instanceof Error ? err.message : String(err)));
      }
    } else if (nameLower.endsWith(".pdf")) {
      // PDF — use canvas renderer for direct page display
      setPdfFile(book.file);
      setPdfTotalPages(0);
      setEpubData(null);
      setTextFileData(null);
      setChapterIdx(0);
      setViewMode("reader");
    } else if (nameLower.endsWith(".txt") || nameLower.endsWith(".md")) {
      // Read text/markdown file
      try {
        const content = await book.file.text();
        setTextFileData({ content, isMarkdown: nameLower.endsWith(".md") });
        setEpubData(null);
        setPdfFile(null);
        setViewMode("reader");
      } catch (err) {
        console.error("Text file read error:", err);
        alert("Failed to read file: " + err);
      }
    } else {
      alert("内置阅读器支持 EPUB、PDF、TXT 和 MD 格式。");
    }
  };

  const closeReader = () => {
    setEpubData(null);
    setTextFileData(null);
    setPdfFile(null);
    setPdfTotalPages(0);
    setChapterIdx(0);
    setViewMode("detail");
  };

  const handleFontSize = (delta: number) => {
    setFontSize(prev => Math.max(80, Math.min(200, prev + delta)));
  };

  const filteredBooks = searchQuery
    ? books.filter((b) => (b.title || b.name).toLowerCase().includes(searchQuery.toLowerCase()) || (b.author || "").toLowerCase().includes(searchQuery.toLowerCase()))
    : books;

  // Determine if we have content to show in reader
  const hasReaderContent = epubData || textFileData || pdfFile;

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {viewMode !== "shelf" && (
            <button className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer transition-colors"
              style={{ color: "var(--text-secondary)" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--hover-bg)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              onClick={() => { if (viewMode === "reader") closeReader(); else setViewMode("shelf"); setSelectedBook(null); }}>
              <IconArrowLeft size={16} />
            </button>
          )}
          <IconBookOpen size={22} style={{ color: "var(--accent-blue)" }} />
          <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            {viewMode === "reader" ? selectedBook?.title || "Reader" : viewMode === "detail" ? selectedBook?.title || "Book Detail" : "Bookshelf"}
          </h2>
        </div>
        {viewMode === "shelf" && (
          <div className="flex gap-2 items-center">
            <div className="relative">
              <IconSearch size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
              <input className="input-glass text-xs pl-8 w-48" placeholder="Search books..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
            </div>
            <button className="btn-ghost text-xs flex items-center gap-1.5" onClick={() => fileInputRef.current?.click()}>
              <IconFolder size={13} /> Load Folder
            </button>
            <input ref={fileInputRef} type="file" accept=".epub,.pdf,.txt,.md" className="hidden"
              {...({ webkitdirectory: "" } as any)} onChange={handleFolderLoad} />
          </div>
        )}
        {viewMode === "reader" && !pdfFile && (
          <div className="flex items-center gap-2">
            <button className="btn-ghost text-xs py-1" onClick={() => handleFontSize(-10)}>A-</button>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{fontSize}%</span>
            <button className="btn-ghost text-xs py-1" onClick={() => handleFontSize(10)}>A+</button>
            <button className="text-xs py-1 px-2 rounded-lg cursor-pointer transition-colors"
              style={{
                background: eyeProtection ? "rgba(245,158,11,0.2)" : "transparent",
                color: eyeProtection ? "#d97706" : "var(--text-muted)",
                border: "1px solid",
                borderColor: eyeProtection ? "rgba(245,158,11,0.3)" : "var(--border-color)",
              }}
              onClick={() => setEyeProtection(!eyeProtection)}
              title="护眼模式">
              <IconSun size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      {viewMode === "shelf" && (
        <>
          {books.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="glass-card p-12 text-center space-y-4">
                <IconBookOpen size={48} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>Load a folder of ebooks to get started</p>
                <button className="btn-gradient btn-click text-xs" onClick={() => fileInputRef.current?.click()}>Select Book Folder</button>
              </div>
            </div>
          ) : (
            /* Bookshelf Grid */
            <div className="flex-1 overflow-y-auto">
              {/* Shelf Row */}
              <div className="bookshelf-row">
                <div className="bookshelf-books">
                  {filteredBooks.map((book, i) => (
                    <BookSpine key={i} book={book} index={i} onClick={() => openDetail(book)} />
                  ))}
                </div>
                <div className="bookshelf-plank" />
              </div>
            </div>
          )}
        </>
      )}

      {viewMode === "detail" && selectedBook && (
        /* Book Detail */
        <div className="flex-1 overflow-y-auto">
          <div className="glass-card p-6 max-w-2xl mx-auto">
            <div className="flex gap-6">
              {/* Cover */}
              <div className="w-48 flex-shrink-0">
                {selectedBook.coverUrl ? (
                  <img src={selectedBook.coverUrl} alt={selectedBook.title} className="w-full rounded-xl shadow-lg" />
                ) : (
                  <div className="w-full h-64 rounded-xl flex items-center justify-center" style={{ background: "var(--hover-bg)" }}>
                    <IconBook size={40} style={{ color: "var(--text-muted)" }} />
                  </div>
                )}
              </div>
              {/* Info */}
              <div className="flex-1 space-y-3">
                <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                  {selectedBook.title || selectedBook.name.replace(/\.[^.]+$/, "")}
                </h3>
                {selectedBook.author && (
                  <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{selectedBook.author}</p>
                )}
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {selectedBook.name} · {(selectedBook.size / 1024 / 1024).toFixed(1)} MB
                </p>
                {selectedBook.description && (
                  <p className="text-sm leading-relaxed line-clamp-6" style={{ color: "var(--text-secondary)" }}>
                    {selectedBook.description}
                  </p>
                )}
                <div className="flex gap-2 pt-2">
                  {/\.(epub|pdf|txt|md)$/i.test(selectedBook.name) && (
                    <button className="btn-gradient btn-click text-xs" onClick={openReader}>Read</button>
                  )}
                  <button className="btn-ghost text-xs" onClick={() => { setViewMode("shelf"); setSelectedBook(null); }}>Back</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewMode === "reader" && hasReaderContent && (
        /* Reader — page-based view with left/right navigation */
        <div className="flex-1 flex flex-col min-h-0 gap-2">
          {/* Top bar: chapter nav + page info */}
          <div className="flex items-center justify-between px-1">
            {epubData ? (
              <>
                <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
                  onClick={() => { setChapterIdx(Math.max(0, chapterIdx - 1)); setPageIdx(0); }}
                  style={{ opacity: chapterIdx === 0 ? 0.3 : 1, pointerEvents: chapterIdx === 0 ? "none" : "auto" }}>
                  <IconChevronLeft size={14} /> 上一章
                </button>
                <span className="text-xs font-medium truncate max-w-[200px]" style={{ color: "var(--text-primary)" }}>
                  {epubData.chapters[chapterIdx]?.title || `Chapter ${chapterIdx + 1}`}
                </span>
                <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
                  onClick={() => { setChapterIdx(Math.min(epubData.chapters.length - 1, chapterIdx + 1)); setPageIdx(0); }}
                  style={{ opacity: chapterIdx >= epubData.chapters.length - 1 ? 0.3 : 1, pointerEvents: chapterIdx >= epubData.chapters.length - 1 ? "none" : "auto" }}>
                  下一章 <IconChevronRight size={14} />
                </button>
              </>
            ) : pdfFile ? (
              <>
                <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
                  onClick={() => setChapterIdx(Math.max(0, chapterIdx - 1))}
                  style={{ opacity: chapterIdx === 0 ? 0.3 : 1, pointerEvents: chapterIdx === 0 ? "none" : "auto" }}>
                  <IconChevronLeft size={14} /> 上一页
                </button>
                <span className="text-xs font-medium truncate max-w-[200px]" style={{ color: "var(--text-primary)" }}>
                  第 {chapterIdx + 1} 页 {pdfTotalPages > 0 ? `/ 共 ${pdfTotalPages} 页` : ""}
                </span>
                <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
                  onClick={() => setChapterIdx(Math.min((pdfTotalPages || 1) - 1, chapterIdx + 1))}
                  style={{ opacity: chapterIdx >= (pdfTotalPages || 1) - 1 ? 0.3 : 1, pointerEvents: chapterIdx >= (pdfTotalPages || 1) - 1 ? "none" : "auto" }}>
                  下一页 <IconChevronRight size={14} />
                </button>
              </>
            ) : (
              <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                {selectedBook?.title || "Reader"}
              </span>
            )}
          </div>

          {/* Content area — book-style layout with page flip */}
          <div className="flex-1 flex min-h-0 relative" style={{
            perspective: "1200px",
          }}>
            {/* Book container */}
            <div className="flex-1 flex relative overflow-hidden rounded-2xl" ref={readerRef}
              style={{
                background: eyeProtection
                  ? "linear-gradient(135deg, #f5e6d0, #ede0cc)"
                  : "var(--glass-bg)",
                border: "1px solid var(--glass-border)",
                fontSize: `${fontSize}%`,
                lineHeight: 1.8,
                color: eyeProtection ? "#5b4636" : "var(--text-primary)",
                boxShadow: "inset 0 0 30px rgba(0,0,0,0.05), 0 4px 20px rgba(0,0,0,0.08)",
                transition: "background 0.5s ease, color 0.5s ease",
              }}>
              {/* Eye protection overlay */}
              {eyeProtection && (
                <div className="absolute inset-0 pointer-events-none" style={{
                  background: "rgba(255,248,230,0.15)",
                  mixBlendMode: "multiply",
                }} />
              )}
              {/* Page flip shadow */}
              {flipDirection && (
                <div className="absolute inset-0 pointer-events-none" style={{
                  background: flipDirection === "right"
                    ? "linear-gradient(to left, rgba(0,0,0,0.08), transparent 40%)"
                    : "linear-gradient(to right, rgba(0,0,0,0.08), transparent 40%)",
                  animation: "fadeIn 0.3s ease",
                }} />
              )}
              {/* Content */}
              {pdfFile ? (
                <PdfViewer file={pdfFile} pageNum={chapterIdx} onTotalPages={setPdfTotalPages} />
              ) : (
                <div ref={contentRef} className="p-8 max-w-3xl mx-auto w-full"
                  dangerouslySetInnerHTML={epubData ? { __html: epubData.chapters[chapterIdx]?.content || "<p>No content</p>" } : undefined}
                  style={{
                    fontFamily: "'Noto Serif SC', 'Source Han Serif SC', 'SimSun', serif",
                    wordWrap: "break-word",
                    overflowWrap: "break-word",
                    transition: "transform 0.3s ease",
                    transform: flipDirection === "right" ? "translateX(-5px)" : flipDirection === "left" ? "translateX(5px)" : "none",
                  }}>
                  {textFileData && (
                    textFileData.isMarkdown ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                        {textFileData.content}
                      </ReactMarkdown>
                    ) : (
                      <pre className="whitespace-pre-wrap" style={{ fontFamily: "inherit" }}>{textFileData.content}</pre>
                    )
                  )}
                </div>
              )}
              {/* Book fold line (center) */}
              <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-px pointer-events-none"
                style={{ background: "rgba(0,0,0,0.04)" }} />
              {/* Left page click zone */}
              <div className="absolute top-0 bottom-0 left-0 w-1/3 cursor-pointer" onClick={() => flipPage("left")} />
              {/* Right page click zone */}
              <div className="absolute top-0 bottom-0 right-0 w-1/3 cursor-pointer" onClick={() => flipPage("right")} />
            </div>
          </div>

          {/* Bottom: chapter selector + page indicator */}
          <div className="flex items-center justify-between px-1">
            {/* Chapter list — simplified */}
            {epubData && epubData.chapters.length > 1 && (
              <select className="text-[10px] bg-transparent border-none outline-none cursor-pointer"
                style={{ color: "var(--text-muted)" }}
                value={chapterIdx}
                onChange={e => { setChapterIdx(Number(e.target.value)); setPageIdx(0); }}>
                {epubData.chapters.map((ch, i) => (
                  <option key={i} value={i}>{i + 1}. {ch.title?.slice(0, 30) || `Chapter ${i + 1}`}</option>
                ))}
              </select>
            )}
            {/* PDF page selector */}
            {pdfFile && pdfTotalPages > 1 && (
              <select className="text-[10px] bg-transparent border-none outline-none cursor-pointer"
                style={{ color: "var(--text-muted)" }}
                value={chapterIdx}
                onChange={e => { setChapterIdx(Number(e.target.value)); }}>
                {Array.from({ length: pdfTotalPages }, (_, i) => (
                  <option key={i} value={i}>第 {i + 1} 页</option>
                ))}
              </select>
            )}
            <span className="flex-1" />
            {!pdfFile && (
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                {pageIdx + 1} / {totalPages}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
