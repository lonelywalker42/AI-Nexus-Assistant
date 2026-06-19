import { useState, useEffect, useRef, useCallback } from "react";
import { IconMusic, IconDisc, IconPlay, IconPause, IconSkipBack, IconSkipForward, IconShuffle, IconRepeat, IconVolume2, IconVolumeX, IconFolder, IconList } from "../components/Icons";

// jsmediatags for metadata extraction
let jsmediatags: any = null;
async function loadJsmediatags() {
  if (jsmediatags) return jsmediatags;
  try {
    const mod = await import("jsmediatags");
    jsmediatags = mod.default || mod;
    return jsmediatags;
  } catch { return null; }
}

interface Track {
  name: string;
  file: File;
  path?: string;
  type: string;
  size: number;
  title?: string;
  artist?: string;
  album?: string;
  coverUrl?: string;
  lyrics?: string;
  duration?: number;
}

// IndexedDB helpers
const DB_NAME = "nexus-music";
const DB_VER = 1;

function openDB(cb: (db: IDBDatabase | null) => void) {
  const req = indexedDB.open(DB_NAME, DB_VER);
  req.onupgradeneeded = (e) => {
    const d = (e.target as IDBOpenDBRequest).result;
    if (!d.objectStoreNames.contains("tracks")) d.createObjectStore("tracks", { keyPath: "name" });
  };
  req.onsuccess = (e) => cb((e.target as IDBOpenDBRequest).result);
  req.onerror = () => cb(null);
}

function saveTracksToDB(tracks: Track[]) {
  openDB((db) => {
    if (!db) return;
    const tx = db.transaction("tracks", "readwrite");
    const store = tx.objectStore("tracks");
    store.clear();
    tracks.forEach((t) => {
      t.file.arrayBuffer().then((buf) => {
        store.put({ name: t.name, type: t.type, size: t.size, data: buf });
      });
    });
  });
}

function loadTracksFromDB(cb: (tracks: Track[]) => void) {
  openDB((db) => {
    if (!db) { cb([]); return; }
    const tx = db.transaction("tracks", "readonly");
    const req = tx.objectStore("tracks").getAll();
    req.onsuccess = () => {
      const items = (req.result || []).map((e: any) => ({
        name: e.name, file: new File([e.data], e.name, { type: e.type }), type: e.type, size: e.size,
      } as Track)).sort((a: Track, b: Track) => a.name.localeCompare(b.name, "zh"));
      cb(items);
    };
    req.onerror = () => cb([]);
  });
}

function extractMetadata(track: Track, cb: (meta: Partial<Track>) => void) {
  loadJsmediatags().then((jmt) => {
    if (!jmt) { cb({}); return; }
    jmt.read(track.file, {
      onSuccess: (tag: any) => {
        const t = tag.tags;
        const meta: Partial<Track> = {};
        if (t.title) meta.title = t.title;
        if (t.artist) meta.artist = t.artist;
        if (t.album) meta.album = t.album;
        if (t.lyrics && t.lyrics.lyrics) meta.lyrics = t.lyrics.lyrics;
        if (t.picture) {
          try {
            const pic = t.picture;
            const base64 = btoa(pic.data.reduce((d: string, byte: number) => d + String.fromCharCode(byte), ""));
            meta.coverUrl = `data:${pic.format};base64,${base64}`;
          } catch {}
        }
        cb(meta);
      },
      onError: () => cb({}),
    });
  });
}

// Vinyl Disc Component
function VinylDisc({ coverUrl, spinning, size = 200 }: { coverUrl?: string; spinning: boolean; size?: number }) {
  return (
    <div className="vinyl-container" style={{ width: size, height: size }}>
      <div className={`vinyl-disc ${spinning ? "spinning" : ""}`} style={{ width: size, height: size }}>
        <div className="vinyl-grooves" />
        <div className="vinyl-label">
          {coverUrl ? (
            <img src={coverUrl} alt="Album art" className="vinyl-cover" />
          ) : (
            <div className="vinyl-default"><IconMusic size={size * 0.15} style={{ color: "var(--text-muted)" }} /></div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MusicPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playMode, setPlayMode] = useState<"sequential" | "repeat" | "shuffle">("sequential");
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showLyrics, setShowLyrics] = useState(false);

  const audioRef = useRef<HTMLAudioElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  const currentTrack = currentIdx >= 0 && currentIdx < tracks.length ? tracks[currentIdx] : null;

  // Load from IndexedDB on mount
  useEffect(() => {
    loadTracksFromDB((items) => {
      if (items.length > 0) {
        setTracks(items);
        // Extract metadata for each track
        items.forEach((track, i) => {
          extractMetadata(track, (meta) => {
            setTracks((prev) => prev.map((t, j) => j === i ? { ...t, ...meta } : t));
          });
        });
      }
    });
  }, []);

  // Audio time update
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => { setCurrentTime(audio.currentTime); setDuration(audio.duration || 0); };
    const onEnd = () => handleNext();
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnd);
    return () => { audio.removeEventListener("timeupdate", onTime); audio.removeEventListener("ended", onEnd); };
  }, [currentIdx, playMode, tracks]);

  // Spectrum visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      const analyser = analyserRef.current;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      if (!analyser) {
        // Idle state: draw baseline bars
        ctx.fillStyle = "rgba(204,102,0,0.15)";
        for (let i = 0; i < 32; i++) {
          ctx.fillRect(i * (w / 32 + 1), h - 1, w / 32 - 1, 1);
        }
        return;
      }

      const bufLen = analyser.frequencyBinCount;
      const data = new Uint8Array(bufLen);
      analyser.getByteFrequencyData(data);
      const barW = Math.max(1, w / bufLen - 1);
      for (let i = 0; i < bufLen; i++) {
        const v = data[i] / 255;
        const barH = Math.max(1, v * h);
        const r = 204 + Math.floor(51 * v);
        const g = 85 + Math.floor(170 * v);
        ctx.fillStyle = `rgba(${r},${g},0,${0.5 + v * 0.5})`;
        ctx.fillRect(i * (barW + 1), h - barH, barW, barH);
      }
    };
    draw();
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  const initAudioContext = useCallback(() => {
    if (audioCtxRef.current) return;
    const audio = audioRef.current;
    if (!audio) return;
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.8;
    const source = ctx.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(ctx.destination);
    audioCtxRef.current = ctx;
    analyserRef.current = analyser;
  }, []);

  const loadAndPlay = useCallback((idx: number) => {
    if (idx < 0 || idx >= tracks.length) return;
    setCurrentIdx(idx);
    const track = tracks[idx];
    const audio = audioRef.current;
    if (!audio) return;
    const url = URL.createObjectURL(track.file);
    audio.src = url;
    audio.volume = isMuted ? 0 : volume;
    audio.play().then(() => {
      initAudioContext();
      if (audioCtxRef.current?.state === "suspended") audioCtxRef.current.resume();
      setIsPlaying(true);
    }).catch(() => {});
  }, [tracks, volume, isMuted, initAudioContext]);

  const handlePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) { audio.pause(); setIsPlaying(false); }
    else {
      if (currentIdx < 0 && tracks.length > 0) loadAndPlay(0);
      else { audio.play().then(() => setIsPlaying(true)).catch(() => {}); }
    }
  };

  const handleNext = () => {
    if (tracks.length === 0) return;
    let next: number;
    if (playMode === "shuffle") {
      next = Math.floor(Math.random() * tracks.length);
      if (tracks.length > 1) while (next === currentIdx) next = Math.floor(Math.random() * tracks.length);
    } else if (playMode === "repeat") {
      next = currentIdx;
    } else {
      next = (currentIdx + 1) % tracks.length;
    }
    loadAndPlay(next);
  };

  const handlePrev = () => {
    if (tracks.length === 0) return;
    let prev: number;
    if (playMode === "shuffle") {
      prev = Math.floor(Math.random() * tracks.length);
    } else {
      prev = (currentIdx - 1 + tracks.length) % tracks.length;
    }
    loadAndPlay(prev);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = parseFloat(e.target.value);
    setCurrentTime(audio.currentTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    setVolume(v);
    if (audioRef.current) audioRef.current.volume = isMuted ? 0 : v;
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (audioRef.current) audioRef.current.volume = isMuted ? volume : 0;
  };

  const cyclePlayMode = () => {
    const modes: Array<"sequential" | "repeat" | "shuffle"> = ["sequential", "repeat", "shuffle"];
    const next = modes[(modes.indexOf(playMode) + 1) % 3];
    setPlayMode(next);
  };

  // Folder load
  const handleFolderLoad = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
      .filter((f) => /\.(mp3|flac|wav|ogg|m4a|aac)$/i.test(f.name))
      .sort((a, b) => a.name.localeCompare(b.name, "zh"));
    if (files.length === 0) return;
    const newTracks: Track[] = files.map((f) => ({
      name: f.name, file: f, type: f.type, size: f.size,
    }));
    setTracks(newTracks);
    setCurrentIdx(-1);
    setIsPlaying(false);
    saveTracksToDB(newTracks);
    // Extract metadata
    newTracks.forEach((track, i) => {
      extractMetadata(track, (meta) => {
        setTracks((prev) => prev.map((t, j) => j === i ? { ...t, ...meta } : t));
      });
    });
    e.target.value = "";
  };

  const formatTime = (s: number) => {
    if (!s || isNaN(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const playModeIcon = playMode === "repeat" ? <IconRepeat size={14} /> : playMode === "shuffle" ? <IconShuffle size={14} /> : <IconList size={14} />;
  const playModeLabel = playMode === "repeat" ? "单曲循环" : playMode === "shuffle" ? "随机播放" : "顺序播放";

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <IconMusic size={22} style={{ color: "var(--accent-blue)" }} />
          <h2 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>Music</h2>
          {tracks.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--hover-bg)", color: "var(--text-muted)" }}>
              {tracks.length} tracks
            </span>
          )}
        </div>
        <button className="btn-ghost text-xs flex items-center gap-1.5" onClick={() => fileInputRef.current?.click()}>
          <IconFolder size={13} /> Load Folder
        </button>
        <input ref={fileInputRef} type="file" accept=".mp3,.flac,.wav,.ogg,.m4a,.aac" className="hidden"
          {...({ webkitdirectory: "" } as any)} onChange={handleFolderLoad} />
      </div>

      {tracks.length === 0 ? (
        /* Empty State */
        <div className="flex-1 flex items-center justify-center">
          <div className="glass-card p-12 text-center space-y-4">
            <IconDisc size={48} style={{ color: "var(--text-muted)", margin: "0 auto" }} />
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>Load a folder of music to get started</p>
            <button className="btn-gradient btn-click text-xs" onClick={() => fileInputRef.current?.click()}>
              Select Music Folder
            </button>
          </div>
        </div>
      ) : (
        /* Main Layout */
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Left: Vinyl + Now Playing */}
          <div className="w-80 flex-shrink-0 flex flex-col gap-4">
            {/* Vinyl Disc */}
            <div className="glass-card p-6 flex flex-col items-center gap-4">
              <VinylDisc coverUrl={currentTrack?.coverUrl} spinning={isPlaying} size={180} />
              <div className="text-center w-full">
                <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                  {currentTrack?.title || currentTrack?.name || "No track selected"}
                </p>
                <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                  {currentTrack?.artist || "Unknown artist"}{currentTrack?.album ? ` · ${currentTrack.album}` : ""}
                </p>
              </div>
            </div>

            {/* Spectrum */}
            <div className="glass-card p-3">
              <canvas ref={canvasRef} width={280} height={32} className="w-full" style={{ height: 32 }} />
            </div>

            {/* Controls */}
            <div className="glass-card p-4 space-y-3">
              {/* Progress */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] w-8 text-right" style={{ color: "var(--text-muted)" }}>{formatTime(currentTime)}</span>
                <input type="range" min={0} max={duration || 0} step={0.1} value={currentTime}
                  onChange={handleSeek} className="flex-1 h-1 accent-blue-500 cursor-pointer" />
                <span className="text-[10px] w-8" style={{ color: "var(--text-muted)" }}>{formatTime(duration)}</span>
              </div>
              {/* Buttons */}
              <div className="flex items-center justify-center gap-3">
                <button className="p-2 rounded-full cursor-pointer transition-colors" style={{ color: "var(--text-secondary)" }}
                  onClick={cyclePlayMode} title={playModeLabel}>
                  {playModeIcon}
                </button>
                <button className="p-2 rounded-full cursor-pointer transition-colors" style={{ color: "var(--text-primary)" }}
                  onClick={handlePrev}><IconSkipBack size={18} /></button>
                <button className="p-3 rounded-full cursor-pointer transition-all" onClick={handlePlayPause}
                  style={{ background: "linear-gradient(135deg, var(--accent-blue), var(--accent-green))", color: "#fff" }}>
                  {isPlaying ? <IconPause size={20} /> : <IconPlay size={20} />}
                </button>
                <button className="p-2 rounded-full cursor-pointer transition-colors" style={{ color: "var(--text-primary)" }}
                  onClick={handleNext}><IconSkipForward size={18} /></button>
                <button className="p-2 rounded-full cursor-pointer transition-colors" style={{ color: "var(--text-secondary)" }}
                  onClick={toggleMute}>
                  {isMuted ? <IconVolumeX size={16} /> : <IconVolume2 size={16} />}
                </button>
              </div>
              {/* Volume */}
              <div className="flex items-center gap-2 px-2">
                <IconVolume2 size={12} style={{ color: "var(--text-muted)" }} />
                <input type="range" min={0} max={1} step={0.01} value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange} className="flex-1 h-1 accent-blue-500 cursor-pointer" />
              </div>
            </div>

            {/* Lyrics Toggle */}
            {currentTrack?.lyrics && (
              <button className="btn-ghost text-xs" onClick={() => setShowLyrics(!showLyrics)}>
                {showLyrics ? "Hide Lyrics" : "Show Lyrics"}
              </button>
            )}
          </div>

          {/* Right: Track List or Lyrics */}
          <div className="flex-1 min-w-0 flex flex-col gap-4">
            {showLyrics && currentTrack?.lyrics ? (
              /* Lyrics View */
              <div className="glass-card p-6 flex-1 overflow-y-auto">
                <h3 className="text-sm font-semibold mb-4" style={{ color: "var(--text-primary)" }}>
                  Lyrics — {currentTrack.title}
                </h3>
                <pre className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: "var(--text-secondary)", fontFamily: "inherit" }}>
                  {currentTrack.lyrics}
                </pre>
              </div>
            ) : (
              /* Track List */
              <div className="glass-card flex-1 overflow-y-auto">
                <div className="divide-y" style={{ borderColor: "var(--border-color)" }}>
                  {tracks.map((track, i) => (
                    <div key={i}
                      className="flex items-center gap-3 px-4 py-3 cursor-pointer transition-all"
                      style={{
                        background: currentIdx === i ? "rgba(59,130,246,0.08)" : "transparent",
                      }}
                      onMouseEnter={(e) => { if (currentIdx !== i) e.currentTarget.style.background = "var(--hover-bg)"; }}
                      onMouseLeave={(e) => { if (currentIdx !== i) e.currentTarget.style.background = "transparent"; }}
                      onClick={() => loadAndPlay(i)}
                    >
                      {/* Track Number / Playing Indicator */}
                      <div className="w-6 text-center flex-shrink-0">
                        {currentIdx === i && isPlaying ? (
                          <div className="flex items-end justify-center gap-0.5 h-4">
                            <div className="w-0.5 bg-blue-500 rounded-full animate-pulse" style={{ height: 12 }} />
                            <div className="w-0.5 bg-blue-500 rounded-full animate-pulse" style={{ height: 8, animationDelay: "0.15s" }} />
                            <div className="w-0.5 bg-blue-500 rounded-full animate-pulse" style={{ height: 14, animationDelay: "0.3s" }} />
                          </div>
                        ) : (
                          <span className="text-xs" style={{ color: currentIdx === i ? "var(--accent-blue)" : "var(--text-muted)" }}>
                            {i + 1}
                          </span>
                        )}
                      </div>

                      {/* Cover Thumbnail */}
                      <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0" style={{ background: "var(--hover-bg)" }}>
                        {track.coverUrl ? (
                          <img src={track.coverUrl} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <IconMusic size={16} style={{ color: "var(--text-muted)" }} />
                          </div>
                        )}
                      </div>

                      {/* Track Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: currentIdx === i ? "var(--accent-blue)" : "var(--text-primary)" }}>
                          {track.title || track.name.replace(/\.[^.]+$/, "")}
                        </p>
                        <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
                          {track.artist || "Unknown artist"}{track.album ? ` · ${track.album}` : ""}
                        </p>
                      </div>

                      {/* Duration */}
                      <span className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                        {track.duration ? formatTime(track.duration) : ""}
                      </span>

                      {/* Lyrics indicator */}
                      {track.lyrics && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded flex-shrink-0"
                          style={{ background: "rgba(59,130,246,0.1)", color: "var(--accent-blue)" }}>LYRICS</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <audio ref={audioRef} preload="auto" />
    </div>
  );
}
