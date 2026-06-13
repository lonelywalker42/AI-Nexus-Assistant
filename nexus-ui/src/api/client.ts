/**
 * AI Nexus Assistant — API 客户端
 * 连接 Tauri 前端与 Python FastAPI 后端
 */

const API_BASE = "http://127.0.0.1:8765";
const MAX_RETRIES = 30;
const RETRY_DELAY = 1000;

async function waitForBackend(): Promise<void> {
  for (let i = 0; i < MAX_RETRIES; i++) {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) return;
    } catch {}
    await new Promise(r => setTimeout(r, RETRY_DELAY));
  }
  throw new Error("Backend not ready after 30 seconds");
}

let backendReady = false;

async function ensureBackend() {
  if (!backendReady) {
    await waitForBackend();
    backendReady = true;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  await ensureBackend();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Dashboard ──────────────────────────────────────────────

export interface DashboardData {
  tasks: { total: number; done: number; pending: number };
  monthly: { total: number; done: number };
  experiments: Record<string, number>;
  knowledge: { total: number; by_source: Record<string, number>; tag_count: number };
  activities: { type: string; text: string; time: string }[];
}

export const dashboardApi = {
  get: () => request<DashboardData>("/api/dashboard"),
};

// ── Tasks ──────────────────────────────────────────────────

export interface Task {
  id: string;
  date: string;
  content: string;
  completed: boolean;
  priority: string;
  category: string;  // general/main/literature/experiment
  created_at: string | null;
  completed_at: string | null;
}

export const tasksApi = {
  list: (date: string) => request<Task[]>(`/api/tasks?date=${date}`),
  listMain: () => request<Task[]>("/api/tasks/main"),
  listIncomplete: () => request<Task[]>("/api/tasks/incomplete"),
  create: (data: { date: string; content: string; priority?: string; category?: string }) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  toggle: (id: string) => request<Task>(`/api/tasks/${id}/toggle`, { method: "POST" }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/tasks/${id}`, { method: "DELETE" }),
  dates: (year: number, month: number) =>
    request<Record<string, string>>(`/api/tasks/dates?year=${year}&month=${month}`),
};

// ── Search ─────────────────────────────────────────────────

export interface Paper {
  title: string;
  authors: string[];
  year: number;
  doi: string;
  abstract: string;
  journal: string;
  source: string;
  url: string;
  paper_type: string;
}

export const searchApi = {
  search: (query: string, sources: string[], maxResults: number = 50) =>
    request<{ papers: Paper[]; count: number }>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, sources, max_results: maxResults }),
    }),
};

// ── Experiments ────────────────────────────────────────────

export interface ExperimentResult {
  id: string;
  version: number;
  description: string;
  parameters: Record<string, unknown>;
  code_snippets: { file: string; code: string; diff: string }[];
  result_data: string;
  conclusion: string;
  created_at: string;
}

export interface Experiment {
  id: string;
  title: string;
  status: string;
  background: string;
  objective: string;
  setup: string;
  created_at: string;
  updated_at: string;
  results: ExperimentResult[];
}

export const experimentsApi = {
  list: (search?: string, status?: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    return request<Experiment[]>(`/api/experiments?${params}`);
  },
  create: (data: { title: string; background?: string; objective?: string; setup?: string }) =>
    request<{ id: string }>("/api/experiments", { method: "POST", body: JSON.stringify(data) }),
  addResult: (expId: string, data: Partial<ExperimentResult>) =>
    request<{ id: string }>(`/api/experiments/${expId}/results`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/experiments/${id}`, { method: "DELETE" }),
};

// ── Knowledge ──────────────────────────────────────────────

export interface KnowledgeCard {
  id: string;
  title: string;
  summary: string;
  key_points: string[];
  source_type: string;
  category_path: string;
  star_rating: number;
  user_notes: string;
  created_at: string;
}

export const knowledgeApi = {
  listCards: (params?: { search?: string; category?: string; tag?: string; source_type?: string }) => {
    const p = new URLSearchParams();
    if (params?.search) p.set("search", params.search);
    if (params?.category) p.set("category", params.category);
    if (params?.tag) p.set("tag", params.tag);
    if (params?.source_type) p.set("source_type", params.source_type);
    return request<KnowledgeCard[]>(`/api/knowledge/cards?${p}`);
  },
  getCard: (id: string) => request<KnowledgeCard>(`/api/knowledge/cards/${id}`),
  createCard: (data: { title: string; summary?: string; tags?: string[]; source_type?: string }) =>
    request<{ id: string }>("/api/knowledge/cards", { method: "POST", body: JSON.stringify(data) }),
  updateCard: (id: string, data: Partial<KnowledgeCard>) =>
    request<{ id: string }>(`/api/knowledge/cards/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCard: (id: string) => request<{ ok: boolean }>(`/api/knowledge/cards/${id}`, { method: "DELETE" }),
  listTags: () => request<{ name: string; usage_count: number; status: string }[]>("/api/knowledge/tags"),
};

// ── Chat ───────────────────────────────────────────────────

export interface ChatSession {
  id: string;
  title: string;
  model_name: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  thinking_content: string;
  created_at: string;
}

export const chatApi = {
  listSessions: () => request<ChatSession[]>("/api/chat/sessions"),
  createSession: (title?: string) =>
    request<{ id: string }>("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title || "新对话" }),
    }),
  deleteSession: (id: string) => request<{ ok: boolean }>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  getMessages: (sessionId: string) => request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),
  addMessage: (sessionId: string, content: string) =>
    request<ChatMessage>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, role: "user" }),
    }),
  stream: async function* (sessionId: string, modelId?: string) {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, model_id: modelId }),
    });
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();
          if (data === "[DONE]") return;
          try {
            yield JSON.parse(data);
          } catch {}
        }
      }
    }
  },
};

// ── Models ─────────────────────────────────────────────────

export interface ModelConfig {
  id: string;
  name: string;
  base_url: string;
  model_name: string;
  protocol: string;
  purpose: string;
  is_active: boolean;
}

export const modelsApi = {
  list: () => request<ModelConfig[]>("/api/models"),
  create: (data: Omit<ModelConfig, "id" | "is_active">) =>
    request<{ id: string }>("/api/models", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<ModelConfig>) =>
    request<{ id: string }>(`/api/models/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/models/${id}`, { method: "DELETE" }),
};

// ── History ────────────────────────────────────────────────

export interface HistoryRecord {
  id: string;
  query: string;
  type: string;
  result_count: number;
  data: string;
  created_at: string;
}

export const historyApi = {
  list: (limit?: number) => request<HistoryRecord[]>(`/api/history?limit=${limit || 50}`),
  create: (data: { query: string; type: string; result_count?: number; data?: string }) =>
    request<{ id: string }>("/api/history", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/history/${id}`, { method: "DELETE" }),
};
