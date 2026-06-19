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
  } catch { return null; }
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

// IndexedDB helpers
const DB_NAME = "nexus-books";
const DB_VER = 1;

function openDB(cb: (db: IDBDatabase | null) => void) {
  const req = indexedDB.open(DB_NAME, DB_VER);
  req.onupgradeneeded = (e) => {
    const d = (e.target as IDBOpenDBRequest).result;
    if (!d.objectStoreNames.contains("books")) d.createObjectStore("books", { keyPath: "name" });
  };
  req.onsuccess = (e) => cb((e.target as IDBOpenDBRequest).result);
  req.onerror = () => cb(null);
}

function saveBooksToDB(books: Book[]) {
  openDB((db) => {
    if (!db) return;
    const tx = db.transaction("books", "readwrite");
    const store = tx.objectStore("books");
    store.clear();
    books.forEach((b) => {
      b.file.arrayBuffer().then((buf) => {
        store.put({ name: b.name, type: b.type, size: b.size, data: buf });
      });
    });
  });
}

function loadBooksFromDB(cb: (books: Book[]) => void) {
  openDB((db) => {
    if (!db) { cb([]); return; }
    const tx = db.transaction("books", "readonly");
    const req = tx.objectStore("books").getAll();
    req.onsuccess = () => {
      const items = (req.result || []).map((e: any) => ({
        name: e.name, file: new File([e.data], e.name, { type: e.type }), type: e.type, size: e.size,
      } as Book)).sort((a: Book, b: Book) => a.name.localeCompare(b.name, "zh"));
      cb(items);
    };
    req.onerror = () => cb([]);
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

  // Load from IndexedDB on mount
  useEffect(() => {
    loadBooksFromDB((items) => {
      if (items.length > 0) {
        setBooks(items);
        items.forEach((book, i) => {
          extractBookMetadata(book).then((meta) => {
            setBooks((prev) => prev.map((b, j) => j === i ? { ...b, ...meta } : b));
          });
        });
      }
    });
  }, []);

  // Cleanup rendition on unmount
  useEffect(() => {
    return () => { if (rendition) rendition.destroy(); };
  }, [rendition]);

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

  const openDetail = (book: Book) => {
    setSelectedBook(book);
    setViewMode("detail");
  };

  const openReader = async () => {
    if (!selectedBook) return;
    if (!selectedBook.name.toLowerCase().endsWith(".epub")) {
      alert("Only EPUB format is supported for the built-in reader.");
      return;
    }
    setViewMode("reader");

    // Wait for DOM update
    setTimeout(async () => {
      if (!readerRef.current) return;
      const epubLib = await loadEpub();
      if (!epubLib) return;

      const url = URL.createObjectURL(selectedBook.file);
      const book = epubLib(url);

      const rend = book.renderTo(readerRef.current, {
        width: "100%",
        height: "100%",
        spread: "none",
      });

      // Restore saved position
      const savedCfi = localStorage.getItem(`book-progress-${selectedBook.name}`);
      if (savedCfi) {
        await rend.display(savedCfi);
      } else {
        await rend.display();
      }

      // Track position
      rend.on("relocated", (location: any) => {
        if (location?.start?.cfi) {
          localStorage.setItem(`book-progress-${selectedBook.name}`, location.start.cfi);
          setCurrentPage(location.start.displayed?.page || "");
        }
      });

      setRendition(rend);
    }, 100);
  };

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
        <div className="flex-1 flex flex-col min-h-0">
          <div ref={readerRef} className="flex-1 glass-card overflow-hidden" />
          <div className="flex items-center justify-between py-2">
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
