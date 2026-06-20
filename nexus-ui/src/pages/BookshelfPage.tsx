import { useState, useEffect, useRef } from "react";
import { IconBookOpen, IconBook, IconSearch, IconFolder, IconArrowLeft, IconChevronLeft, IconChevronRight } from "../components/Icons";
import JSZip from "jszip";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

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
        const coverBuf = await coverFile.async("arraybuffer");
        const ext = coverPath.split(".").pop()?.toLowerCase() || "jpg";
        const mime = ext === "png" ? "image/png" : "image/jpeg";
        coverUrl = `data:${mime};base64,${btoa(String.fromCharCode(...new Uint8Array(coverBuf)))}`;
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

    const file = zip.file(href);
    if (!file) continue;

    let html = await file.async("text");

    // Extract chapter title from <title> or first <h1>-<h3>
    const titleTagMatch = html.match(/<title[^>]*>([^<]+)<\/title>/);
    const hMatch = html.match(/<h[1-3][^>]*>([^<]+)<\/h[1-3]>/);
    const chapterTitle = hMatch?.[1] || titleTagMatch?.[1] || `Chapter ${chapters.length + 1}`;

    // Convert relative image paths to data URLs
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
          const imgB64 = btoa(String.fromCharCode(...new Uint8Array(imgBuf)));
          imgReplacements.push([imgSrc, `data:${imgMime};base64,${imgB64}`]);
        } catch {}
      }
    }
    for (const [orig, dataUrl] of imgReplacements) {
      html = html.replace(new RegExp(`src="${orig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`, 'g'), `src="${dataUrl}"`);
    }

    // Strip <html>, <head>, <body> tags to get just the content
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
    const chapterContent = bodyMatch ? bodyMatch[1] : html;

    chapters.push({ title: chapterTitle, content: chapterContent });
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

// Book Spine Component
function BookSpine({ book, index, onClick }: { book: Book; index: number; onClick: () => void }) {
  const colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];
  const color = colors[index % colors.length];

  return (
    <div className="book-spine-wrapper cursor-pointer group" onClick={onClick}>
      <div className="book-spine" style={{ background: color }}>
        <div className="book-spine-title">{book.title || book.name.replace(/\.[^.]+$/, "")}</div>
      </div>
      <div className="book-spine-shadow" style={{ background: color }} />
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
  const [chapterIdx, setChapterIdx] = useState(0);
  const [fontSize, setFontSize] = useState(100);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const readerRef = useRef<HTMLDivElement>(null);

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
        setChapterIdx(0);
        setViewMode("reader");
      } catch (err) {
        console.error("EPUB parse error:", err);
        alert("Failed to parse EPUB: " + err);
      }
    } else if (nameLower.endsWith(".txt") || nameLower.endsWith(".md")) {
      // Read text/markdown file
      try {
        const content = await book.file.text();
        setTextFileData({ content, isMarkdown: nameLower.endsWith(".md") });
        setEpubData(null);
        setViewMode("reader");
      } catch (err) {
        console.error("Text file read error:", err);
        alert("Failed to read file: " + err);
      }
    } else {
      alert("内置阅读器支持 EPUB、TXT 和 MD 格式。");
    }
  };

  const closeReader = () => {
    setEpubData(null);
    setTextFileData(null);
    setChapterIdx(0);
    setViewMode("detail");
  };

  const handleFontSize = (delta: number) => {
    setFontSize(prev => Math.max(80, Math.min(200, prev + delta)));
  };

  const filteredBooks = searchQuery
    ? books.filter((b) => (b.title || b.name).toLowerCase().includes(searchQuery.toLowerCase()) || (b.author || "").toLowerCase().includes(searchQuery.toLowerCase()))
    : books;

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
        {viewMode === "reader" && (
          <div className="flex items-center gap-2">
            <button className="btn-ghost text-xs py-1" onClick={() => handleFontSize(-10)}>A-</button>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{fontSize}%</span>
            <button className="btn-ghost text-xs py-1" onClick={() => handleFontSize(10)}>A+</button>
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
                  {/\.(epub|txt|md)$/i.test(selectedBook.name) && (
                    <button className="btn-gradient btn-click text-xs" onClick={openReader}>Read</button>
                  )}
                  <button className="btn-ghost text-xs" onClick={() => { setViewMode("shelf"); setSelectedBook(null); }}>Back</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewMode === "reader" && epubData && (
        /* EPUB Reader — direct HTML rendering (no iframe) */
        <div className="flex-1 flex flex-col min-h-0 gap-2">
          {/* Chapter nav bar */}
          <div className="flex items-center justify-between px-1">
            <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
              onClick={() => setChapterIdx(Math.max(0, chapterIdx - 1))}
              style={{ opacity: chapterIdx === 0 ? 0.3 : 1, pointerEvents: chapterIdx === 0 ? "none" : "auto" }}>
              <IconChevronLeft size={14} /> Prev
            </button>
            <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
              {epubData.chapters[chapterIdx]?.title || `Chapter ${chapterIdx + 1}`}
            </span>
            <button className="btn-ghost text-xs py-1.5 flex items-center gap-1"
              onClick={() => setChapterIdx(Math.min(epubData.chapters.length - 1, chapterIdx + 1))}
              style={{ opacity: chapterIdx >= epubData.chapters.length - 1 ? 0.3 : 1, pointerEvents: chapterIdx >= epubData.chapters.length - 1 ? "none" : "auto" }}>
              Next <IconChevronRight size={14} />
            </button>
          </div>
          {/* Chapter content */}
          <div className="flex-1 rounded-2xl overflow-y-auto" ref={readerRef}
            style={{
              background: "var(--glass-bg)",
              border: "1px solid var(--glass-border)",
              fontSize: `${fontSize}%`,
              lineHeight: 1.8,
              color: "var(--text-primary)",
            }}>
            <div className="p-6 max-w-3xl mx-auto"
              dangerouslySetInnerHTML={{ __html: epubData.chapters[chapterIdx]?.content || "<p>No content</p>" }}
              style={{
                fontFamily: "'Open Sans', system-ui, sans-serif",
                wordWrap: "break-word",
                overflowWrap: "break-word",
              }}
            />
          </div>
          {/* Chapter list */}
          <div className="flex items-center gap-2 overflow-x-auto py-1">
            {epubData.chapters.map((_ch, i) => (
              <button key={i}
                className="px-2 py-1 rounded text-[10px] cursor-pointer flex-shrink-0 transition-colors"
                style={i === chapterIdx
                  ? { background: "var(--accent-blue)", color: "#fff" }
                  : { background: "var(--hover-bg)", color: "var(--text-muted)" }}
                onClick={() => setChapterIdx(i)}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}

      {viewMode === "reader" && textFileData && (
        /* Text/Markdown Reader */
        <div className="flex-1 flex flex-col min-h-0 gap-2">
          <div className="flex-1 rounded-2xl overflow-y-auto" ref={readerRef}
            style={{
              background: "var(--glass-bg)",
              border: "1px solid var(--glass-border)",
              fontSize: `${fontSize}%`,
              lineHeight: 1.8,
              color: "var(--text-primary)",
            }}>
            <div className="p-6 max-w-3xl mx-auto reader-content"
              style={{
                fontFamily: "'Open Sans', system-ui, sans-serif",
                wordWrap: "break-word",
                overflowWrap: "break-word",
              }}>
              {textFileData.isMarkdown ? (
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                  {textFileData.content}
                </ReactMarkdown>
              ) : (
                <pre className="whitespace-pre-wrap" style={{ fontFamily: "inherit" }}>{textFileData.content}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
