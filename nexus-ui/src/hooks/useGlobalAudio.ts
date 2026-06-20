// Global audio singleton — persists across page navigations
// The audio element is created once and never destroyed

let globalAudio: HTMLAudioElement | null = null;
let globalAudioCtx: AudioContext | null = null;
let globalAnalyser: AnalyserNode | null = null;

export function getGlobalAudio(): HTMLAudioElement {
  if (!globalAudio) {
    globalAudio = new Audio();
    globalAudio.preload = "auto";
  }
  return globalAudio;
}

export function getGlobalAudioContext(): { ctx: AudioContext; analyser: AnalyserNode } | null {
  if (!globalAudioCtx) {
    try {
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.8;
      const source = ctx.createMediaElementSource(getGlobalAudio());
      source.connect(analyser);
      analyser.connect(ctx.destination);
      globalAudioCtx = ctx;
      globalAnalyser = analyser;
    } catch {
      return null;
    }
  }
  return globalAudioCtx && globalAnalyser ? { ctx: globalAudioCtx, analyser: globalAnalyser } : null;
}

// Playback state that persists across page switches
interface PersistentState {
  currentIdx: number;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  playMode: "sequential" | "repeat" | "shuffle";
  trackName: string;
}

const listeners = new Set<() => void>();
let state: PersistentState = {
  currentIdx: -1,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: 0.7,
  isMuted: false,
  playMode: "sequential",
  trackName: "",
};

export function getMusicState(): PersistentState {
  return state;
}

export function setMusicState(partial: Partial<PersistentState>) {
  state = { ...state, ...partial };
  listeners.forEach(fn => fn());
}

export function subscribeMusicState(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
