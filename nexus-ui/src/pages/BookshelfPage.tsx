import { useState, useEffect, useRef } from "react";
import { IconBookOpen, IconBook, IconSearch, IconFolder, IconArrowLeft, IconChevronLeft, IconChevronRight } from "../components/Icons";

// epubjs for EPUB rendering
let ePub: any = null;
async function loadEpub() {
  if (ePub) return ePub;
  try {
    const mod = await import("epubjs");
    ePub = mod.default || mod;
    return ePub;
  } catch (err) {
    console.error("Failed to load epubjs:", err);
    return null;
  }
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
    const epubLib = await loadEpub();
    if (!epubLib) return {};
    const url = URL.createObjectURL(book.file);
    const bookObj = epubLib(url);
    const metadata = await bookObj.loaded.metadata;
    const coverUrl = await bookObj.coverUrl();
    const desc = metadata.description || "";
    bookObj.destroy();
    URL.revokeObjectURL(url);
    return {
      title: metadata.title || undefined,
      author: metadata.creator || undefined,
      description: typeof desc === "string" ? desc.slice(0, 500) : undefined,
      coverUrl: coverUrl || undefined,
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
  const [rendition, setRendition] = useState<any>(null);
  const [currentPage, setCurrentPage] = useState("");
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

  const openReader = () => {
    if (!selectedBook) return;
    if (!selectedBook.name.toLowerCase().endsWith(".epub")) {
      alert("Only EPUB format is supported for the built-in reader.");
      return;
    }
    setViewMode("reader");
  };

  // Initialize EPUB reader when viewMode changes to "reader"
  useEffect(() => {
    if (viewMode !== "reader" || !selectedBook || !selectedBook.file) return;
    let active = true;
    let rend: any = null;
    let resizeObs: ResizeObserver | null = null;

    const initReader = async () => {
      // Step 1: Wait for container to have stable dimensions via ResizeObserver
      const container = readerRef.current;
      if (!container) return;

      await new Promise<void>((resolve) => {
        if (container.offsetWidth > 100 && container.offsetHeight > 50) {
          resolve();
          return;
        }
        resizeObs = new ResizeObserver((entries) => {
          for (const entry of entries) {
            if (entry.contentRect.width > 100 && entry.contentRect.height > 50) {
              resizeObs?.disconnect();
              resizeObs = null;
              resolve();
            }
          }
        });
        resizeObs.observe(container);
        // Timeout fallback
        setTimeout(() => { resizeObs?.disconnect(); resizeObs = null; resolve(); }, 3000);
      });

      if (!active || !readerRef.current) return;

      // Step 2: Load epubjs library
      const epubLib = await loadEpub();
      if (!epubLib) {
        if (readerRef.current) {
          readerRef.current.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);"><p>Failed to load EPUB library</p></div>';
        }
        return;
      }
      if (!active || !readerRef.current) return;

      // Step 3: Create book from ArrayBuffer directly (avoids blob URL iframe issues in Tauri)
      try {
        const buf = await selectedBook.file.arrayBuffer();
        if (!active) return;

        const book = epubLib(buf);
        const c = readerRef.current;
        const w = c.offsetWidth || 600;
        const h = c.offsetHeight || 500;

        // Step 4: Render with paginated flow and auto spread
        rend = book.renderTo(c, { width: w, height: h, spread: "auto" });

        // Apply theme to make text readable and adaptive
        rend.themes.default({
          "body": {
            "color": "var(--text-primary, #1e293b)",
            "font-family": "'Open Sans', system-ui, -apple-system, sans-serif",
            "line-height": "1.7",
            "padding": "0 16px",
          },
          "p": { "margin": "0.5em 0" },
          "a": { "color": "var(--accent-blue, #3b82f6)" },
        });

        const savedCfi = localStorage.getItem(`book-progress-${selectedBook.name}`);
        await rend.display(savedCfi || undefined);

        rend.on("relocated", (location: any) => {
          if (location?.start?.cfi) {
            localStorage.setItem(`book-progress-${selectedBook.name}`, location.start.cfi);
            setCurrentPage(location.start.displayed?.page || "");
          }
        });

        // Resize rendition when container resizes
        const resizeHandler = () => {
          if (rend && c.offsetWidth > 0) {
            rend.resize(c.offsetWidth, c.offsetHeight);
          }
        };
        window.addEventListener("resize", resizeHandler);
        if (active) setRendition(rend);
      } catch (err) {
        console.error("EPUB render error:", err);
        // Fallback: show error message in the container
        if (readerRef.current) {
          readerRef.current.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);"><p>Failed to load EPUB: ${err}</p></div>`;
        }
      }
    };

    // Use requestAnimationFrame to ensure DOM is painted before measuring
    const raf = requestAnimationFrame(() => {
      setTimeout(initReader, 50);
    });

    return () => {
      active = false;
      cancelAnimationFrame(raf);
      if (resizeObs) resizeObs.disconnect();
      if (rend) { try { rend.destroy(); } catch {} setRendition(null); }
    };
  }, [viewMode, selectedBook]);

  const closeReader = () => {
    if (rendition) {
      rendition.destroy();
      setRendition(null);
    }
    setViewMode("detail");
  };

  const handleFontSize = (delta: number) => {
    const newSize = Math.max(80, Math.min(200, fontSize + delta));
    setFontSize(newSize);
    if (rendition) rendition.themes.fontSize(`${newSize}%`);
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
                  {selectedBook.name.toLowerCase().endsWith(".epub") && (
                    <button className="btn-gradient btn-click text-xs" onClick={openReader}>Read</button>
                  )}
                  <button className="btn-ghost text-xs" onClick={() => { setViewMode("shelf"); setSelectedBook(null); }}>Back</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewMode === "reader" && (
        /* EPUB Reader */
        <div className="flex-1 flex flex-col min-h-0 gap-2">
          <div ref={readerRef} className="flex-1 rounded-2xl overflow-hidden" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)", minHeight: "400px" }} />
          <div className="flex items-center justify-between py-1">
            <button className="btn-ghost text-xs py-1.5" onClick={() => rendition?.prev()}>
              <IconChevronLeft size={14} /> Prev
            </button>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{currentPage}</span>
            <button className="btn-ghost text-xs py-1.5" onClick={() => rendition?.next()}>
              Next <IconChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
