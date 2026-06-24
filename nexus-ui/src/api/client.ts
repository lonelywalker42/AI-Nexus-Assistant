/**
 * AI Nexus Assistant — API 客户端
 * 连接 Tauri 前端与 Python FastAPI 后端
 * v4.0.0: 添加 JWT 认证支持
 */

export const API_BASE = "http://127.0.0.1:8765";
export const APP_VERSION = "4.4.2";
const MAX_RETRIES = 30;
const RETRY_DELAY = 1000;

// ── 认证 Token 管理 ───────────────────────────────────────

let _accessToken: string | null = null;
let _refreshToken: string | null = null;

function getStoredTokens(): { access: string | null; refresh: string | null } {
  try {
    return {
      access: localStorage.getItem("nexus_access_token"),
      refresh: localStorage.getItem("nexus_refresh_token"),
    };
  } catch {
    return { access: null, refresh: null };
  }
}

function storeTokens(access: string, refresh?: string) {
  _accessToken = access;
  if (refresh) _refreshToken = refresh;
  try {
    localStorage.setItem("nexus_access_token", access);
    if (refresh) localStorage.setItem("nexus_refresh_token", refresh);
  } catch {}
}

function clearTokens() {
  _accessToken = null;
  _refreshToken = null;
  try {
    localStorage.removeItem("nexus_access_token");
    localStorage.removeItem("nexus_refresh_token");
  } catch {}
}

function getAuthHeader(): Record<string, string> {
  const token = _accessToken || getStoredTokens().access;
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

export function isLoggedIn(): boolean {
  return !!( _accessToken || getStoredTokens().access);
}

export function logout() {
  clearTokens();
}

// ── 后端就绪检测 ─────────────────────────────────────────

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

// ── 认证 API ──────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: { username: string; role: string };
}

export const authApi = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "登录失败" }));
      throw new Error(err.detail || "登录失败");
    }
    const data: AuthResponse = await res.json();
    storeTokens(data.access_token, data.refresh_token);
    return data;
  },
  refresh: async (): Promise<boolean> => {
    const refresh = _refreshToken || getStoredTokens().refresh;
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) { clearTokens(); return false; }
      const data = await res.json();
      storeTokens(data.access_token);
      return true;
    } catch {
      return false;
    }
  },
};

// ── 通用请求函数（带认证 + 自动刷新）────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  await ensureBackend();
  const isGet = !options?.method || options.method === "GET";
  const headers: Record<string, string> = {
    ...getAuthHeader(),
    ...(isGet ? {} : { "Content-Type": "application/json" }),
    ...(options?.headers as Record<string, string> || {}),
  };
  // 30 秒超时，防止请求挂起
  let mergedSignal: AbortSignal;
  try {
    const timeoutSignal = AbortSignal.timeout(30000);
    mergedSignal = options?.signal
      ? AbortSignal.any([options.signal, timeoutSignal])
      : timeoutSignal;
  } catch {
    // AbortSignal.timeout/any 不可用时忽略超时
    mergedSignal = options?.signal as AbortSignal;
  }
  let res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: mergedSignal });

  // 401 → 尝试刷新 token → 重试
  if (res.status === 401) {
    const refreshed = await authApi.refresh();
    if (refreshed) {
      const retryHeaders = {
        ...getAuthHeader(),
        ...(isGet ? {} : { "Content-Type": "application/json" }),
        ...(options?.headers as Record<string, string> || {}),
      };
      res = await fetch(`${API_BASE}${path}`, { ...options, headers: retryHeaders, signal: mergedSignal });
    }
  }

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  return res.json();
}

// ── SSE 流式请求工具 ──────────────────────────────────────

async function* streamRequest(path: string, body: Record<string, unknown>, signal?: AbortSignal) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    body: JSON.stringify(body),
    signal,
  });
  const reader = res.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";
  try {
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
          try { yield JSON.parse(data); } catch {}
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ── System ────────────────────────────────────────────────

export interface SystemInfo {
  db_size: number;
  db_size_str: string;
  db_path: string;
  data_dir: string;
}

export const systemApi = {
  info: () => request<SystemInfo>("/api/system/info"),
  mineruStatus: () => request<{ available: boolean; version: string }>("/api/system/mineru-status"),
  installMineru: async () => {
    const res = await fetch(`${API_BASE}/api/system/install-mineru`, {
      method: "POST",
      headers: { ...getAuthHeader() },
    });
    const reader = res.body?.getReader();
    if (reader) {
      while (true) {
        const { done } = await reader.read();
        if (done) break;
      }
    }
  },
  searchServiceStatus: () => request<{ running: boolean }>("/api/search-service/status"),
  searchServiceStart: () => request<{ ok: boolean; error?: string }>("/api/search-service/start", { method: "POST" }),
  searchServiceStop: () => request<{ ok: boolean }>("/api/search-service/stop", { method: "POST" }),
};

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
  update: (id: string, data: Partial<Task>) =>
    request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  completeWithDate: (id: string, date: string) =>
    request<{ id: string; completed: boolean; completed_at: string }>(`/api/tasks/${id}/complete-with-date`, {
      method: "POST", body: JSON.stringify({ date }),
    }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/tasks/${id}`, { method: "DELETE" }),
  dates: (year: number, month: number) =>
    request<Record<string, string>>(`/api/tasks/dates?year=${year}&month=${month}`),
  weekTasks: (start?: string) =>
    request<Record<string, { id: string; content: string; completed: boolean; priority: string; category: string }[]>>(
      `/api/tasks/week${start ? `?start=${start}` : ""}`),
};

// ── Weekly Plans ──────────────────────────────────────────

export interface WeeklyPlan {
  exists: boolean;
  id?: string;
  week_start?: string;
  week_end?: string;
  tasks?: { id: string; date: string; content: string; completed: boolean; priority: string; category: string; sort_order: number }[];
  total?: number;
  done?: number;
}

export const plansApi = {
  current: () => request<WeeklyPlan>("/api/plans/current"),
  create: (data?: { week_start?: string; tasks?: { date: string; content: string; priority?: string; category?: string }[] }) =>
    request<{ id: string; week_start: string }>("/api/plans", { method: "POST", body: JSON.stringify(data || {}) }),
  copy: (planId: string) =>
    request<{ id: string; week_start: string }>(`/api/plans/${planId}/copy`, { method: "POST" }),
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
  arxiv_id?: string;
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
  local_path: string;
  repo_url: string;
  readme_content: string;
  related_paper_ids: string[];
  ai_analysis: string;
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
  update: (id: string, data: Partial<Experiment>) =>
    request<{ id: string }>(`/api/experiments/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  addResult: (expId: string, data: Partial<ExperimentResult>) =>
    request<{ id: string }>(`/api/experiments/${expId}/results`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateResult: (resultId: string, data: Partial<ExperimentResult>) =>
    request<{ id: string }>(`/api/experiments/results/${resultId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteResult: (resultId: string) =>
    request<{ ok: boolean }>(`/api/experiments/results/${resultId}`, { method: "DELETE" }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/experiments/${id}`, { method: "DELETE" }),
  paramsTable: (expId: string) =>
    request<{ experiment_id: string; param_keys: string[]; rows: Array<{ result_id: string; version: number; description: string; params: Record<string, unknown>; result_data: string; conclusion: string; created_at: string }> }>(`/api/experiments/${expId}/params-table`),
  aiAnalysis: (expId: string) =>
    request<{ analysis: string }>(`/api/experiments/${expId}/ai-analysis`, { method: "POST" }),
  gitStatus: (expId: string) =>
    request<{ has_git: boolean; branch?: string; commit_hash?: string; commit_short?: string;
      commit_message?: string; commit_date?: string; dirty_files?: number; reason?: string }>(
      `/api/experiments/${expId}/git/status`),
  gitSnapshot: (expId: string, resultId: string) =>
    request<{ commit_short?: string; commit_message?: string; error?: string }>(
      `/api/experiments/${expId}/results/${resultId}/snapshot`, { method: "POST" }),
  generateReadme: (expId: string) =>
    request<{ readme: string }>(`/api/experiments/${expId}/generate-readme`, { method: "POST" }),
  archive: (expId: string) =>
    request<{ archive: Record<string, unknown> }>(`/api/experiments/${expId}/archive`, { method: "POST" }),
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
  import_group_id?: string;
  chat_session_id?: string;
  tags?: string[];
  created_at: string;
  updated_at?: string;
}

export const knowledgeApi = {
  listCards: (params?: { search?: string; category?: string; tag?: string; source_type?: string;
    sort_by?: string; sort_order?: string; star_min?: number }) => {
    const p = new URLSearchParams();
    if (params?.search) p.set("search", params.search);
    if (params?.category) p.set("category", params.category);
    if (params?.tag) p.set("tag", params.tag);
    if (params?.source_type) p.set("source_type", params.source_type);
    if (params?.sort_by) p.set("sort_by", params.sort_by);
    if (params?.sort_order) p.set("sort_order", params.sort_order);
    if (params?.star_min) p.set("star_min", String(params.star_min));
    return request<KnowledgeCard[]>(`/api/knowledge/cards?${p}`);
  },
  getCard: (id: string) => request<KnowledgeCard>(`/api/knowledge/cards/${id}`),
  createCard: (data: { title: string; summary?: string; tags?: string[]; source_type?: string }) =>
    request<{ id: string }>("/api/knowledge/cards", { method: "POST", body: JSON.stringify(data) }),
  updateCard: (id: string, data: Partial<KnowledgeCard>) =>
    request<{ id: string }>(`/api/knowledge/cards/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCard: (id: string) => request<{ ok: boolean }>(`/api/knowledge/cards/${id}`, { method: "DELETE" }),
  regenerateSummary: (id: string) =>
    request<{ card_id: string; title: string; summary: string; knowledge_domain: string[] }>(
      `/api/knowledge/cards/${id}/regenerate-summary`, { method: "POST" }
    ),
  listTags: () => request<{ name: string; usage_count: number; status: string }[]>("/api/knowledge/tags"),
};

// ── Import Groups ──────────────────────────────────────────

export interface ImportGroup {
  id: string;
  title: string;
  source_type: string;
  source_url: string;
  original_filename: string;
  message_count: number;
  summary: string;
  knowledge_domain: string[];
  card_count: number;
  chat_session_id: string | null;
  status: string;
  error: string;
  progress: string;
  created_at: string;
  cards?: KnowledgeCard[];
}

export const importGroupApi = {
  list: () => request<ImportGroup[]>("/api/knowledge/import-groups"),
  get: (id: string) => request<ImportGroup>(`/api/knowledge/import-groups/${id}`),
  getProgress: (id: string) => request<{ status: string; progress: string; card_count: number; error: string }>(
    `/api/knowledge/import-groups/${id}/progress`
  ),
  delete: (id: string) => request<{ ok: boolean; deleted_cards: number }>(
    `/api/knowledge/import-groups/${id}`, { method: "DELETE" }
  ),
  getMessages: (id: string) => request<{ group_id: string; sessions: { session_id: string; title: string; messages: { role: string; content: string }[] }[] }>(
    `/api/knowledge/import-groups/${id}/messages`
  ),
  importDeepseek: (data: any, filename?: string) => request<{ group_id: string; conversations: number; total_messages: number; status: string }>(
    "/api/knowledge/import/deepseek", {
      method: "POST",
      body: JSON.stringify({ data, filename }),
    }
  ),
};

// ── Chat ───────────────────────────────────────────────────

export interface ChatSession {
  id: string;
  title: string;
  model_name: string;
  category: string;
  import_group_id?: string;
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
  createSession: (title?: string, category?: string) =>
    request<{ id: string; title: string; category: string }>("/api/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title || "新对话", category: category || "general" }),
    }),
  deleteSession: (id: string) => request<{ ok: boolean }>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  batchDelete: (ids: string[]) =>
    request<{ deleted: number }>("/api/chat/sessions/batch-delete", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  deleteByCategory: (category: string) =>
    request<{ deleted: number }>("/api/chat/sessions/delete-by-category", {
      method: "POST",
      body: JSON.stringify({ category }),
    }),
  deduplicateSessions: (category?: string) =>
    request<{ removed: number; details: { id: string; title: string }[] }>("/api/chat/sessions/deduplicate", {
      method: "POST",
      body: JSON.stringify({ category: category || "" }),
    }),
  getMessages: (sessionId: string) => request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),
  exportSession: (sessionId: string) =>
    request<{ content: string; title: string }>(`/api/chat/sessions/${sessionId}/export`, { method: "POST" }),
  addMessage: (sessionId: string, content: string) =>
    request<ChatMessage>(`/api/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, role: "user" }),
    }),
  stream: (sessionId: string, modelId?: string, signal?: AbortSignal) =>
    streamRequest("/api/chat/stream", { session_id: sessionId, model_id: modelId }, signal),
};

// ── Agent ─────────────────────────────────────────────────

export interface AgentRequest {
  query: string;
  workflow_type: string;
  model_id?: string;
  config?: Record<string, any>;
}

export const agentApi = {
  run: (body: AgentRequest) =>
    request<any>("/api/agent/run", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listWorkflows: () =>
    request<any[]>("/api/agent/workflows"),
  deleteWorkflow: (id: string) =>
    request<any>(`/api/agent/workflows/${id}`, { method: "DELETE" }),
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

// ── Papers (文献库) ─────────────────────────────────────────

export interface PaperDetail {
  id: string;
  title: string;
  authors: string[];
  year: number;
  doi: string;
  abstract: string;
  journal: string;
  source: string;
  url: string;
  citation: string;
  paper_type: string;
  has_fulltext: boolean;
  star_rating: number;
  user_notes: string;
  ai_summary: string;
  local_path: string;
  tags: string[];
  review_id: string;
  created_at: string;
}

export const papersApi = {
  list: (params?: { search?: string; sort_by?: string; sort_order?: string;
    year_from?: number; year_to?: number; star_min?: number }) => {
    const p = new URLSearchParams();
    if (params?.search) p.set("search", params.search);
    if (params?.sort_by) p.set("sort_by", params.sort_by);
    if (params?.sort_order) p.set("sort_order", params.sort_order);
    if (params?.year_from) p.set("year_from", String(params.year_from));
    if (params?.year_to) p.set("year_to", String(params.year_to));
    if (params?.star_min) p.set("star_min", String(params.star_min));
    return request<PaperDetail[]>(`/api/papers?${p}`);
  },
  get: (id: string) => request<PaperDetail>(`/api/papers/${id}`),
  create: (data: Partial<PaperDetail>) =>
    request<PaperDetail>("/api/papers", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<PaperDetail>) =>
    request<PaperDetail>(`/api/papers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/papers/${id}`, { method: "DELETE" }),
  batchDelete: (ids: string[]) =>
    request<{ deleted: number }>("/api/papers/batch-delete", { method: "POST", body: JSON.stringify({ ids }) }),
  fromSearch: (data: Record<string, unknown>) =>
    request<PaperDetail>("/api/papers/from-search", { method: "POST", body: JSON.stringify(data) }),
  citation: (id: string, format: string = "gb7714", index: number = 1) =>
    request<{ citation: string; format: string }>(`/api/papers/${id}/citation?format=${format}&index=${index}`),
  aiSummary: (id: string) =>
    request<{ ai_summary: string }>(`/api/papers/${id}/ai-summary`, { method: "POST" }),
  stats: () => request<{ total: number; by_source: Record<string, number>; rated: number }>("/api/papers/stats"),
  searchMention: (q: string, limit: number = 10) =>
    request<{ id: string; title: string; authors: string[]; year: number }[]>(`/api/papers/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  // v3.6.0 新增: 出版社 PDF 拉取
  fetchPdf: (doi: string, title: string = "") =>
    request<PaperDetail>("/api/papers/fetch-pdf", { method: "POST", body: JSON.stringify({ doi, title }) }),
  batchFetchPdf: (dois: string[]) =>
    request<{ results: { doi: string; paper_id?: string; status: string; error?: string }[]; total: number; success: number }>(
      "/api/papers/batch-fetch-pdf", { method: "POST", body: JSON.stringify({ dois }) }),
  refetchPdf: (id: string) =>
    request<{ success: boolean; pdf_path: string }>(`/api/papers/${id}/refetch-pdf`, { method: "POST" }),

  // v3.6.0 新增: 论文笔记 CRUD
  getNotes: (paperId: string) =>
    request<{ id: string; content: string; created_at: string; updated_at?: string }[]>(`/api/papers/${paperId}/notes`),
  createNote: (paperId: string, content: string) =>
    request<{ id: string; content: string }>(`/api/papers/${paperId}/notes`, { method: "POST", body: JSON.stringify({ content }) }),
  updateNote: (paperId: string, noteId: string, content: string) =>
    request<{ id: string; content: string }>(`/api/papers/${paperId}/notes/${noteId}`, { method: "PUT", body: JSON.stringify({ content }) }),
  deleteNote: (paperId: string, noteId: string) =>
    request<{ ok: boolean }>(`/api/papers/${paperId}/notes/${noteId}`, { method: "DELETE" }),

  // v3.6.0 新增: 语义近邻推荐
  neighbors: (paperId: string, topK: number = 10) =>
    request<{ paper_id: string; neighbors: { id: string; title: string; authors: string[]; year: number; doi: string; journal: string; score: number }[] }>(
      `/api/papers/${paperId}/neighbors?top_k=${topK}`),

  // v3.6.0 新增: 元数据审计
  audit: () => request<{ papers: { paper_id: string; title: string; issues: string[]; severity: string }[]; count: number }>("/api/papers/audit"),
  auditStats: () => request<{ total: number; with_issues: number; by_issue_type: Record<string, number>; severity_counts: Record<string, number> }>("/api/papers/audit/stats"),

  // v3.6.0 新增: BibTeX/RIS 导入
  importBibtex: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/papers/import-bibtex`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Import failed: ${res.status}`);
    return res.json() as Promise<{ results: { title: string; paper_id?: string; status: string }[]; total: number; imported: number }>;
  },
  importRis: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/papers/import-ris`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Import failed: ${res.status}`);
    return res.json() as Promise<{ results: { title: string; paper_id?: string; status: string }[]; total: number; imported: number }>;
  },

  // v4.1.0 新增: 分步导入（提取元数据 → 确认入库）
  extractMetadata: async (file: File) => {
    const bytes = await file.arrayBuffer();
    const res = await fetch(`${API_BASE}/api/papers/extract-metadata`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(file.name) },
      body: bytes,
    });
    if (!res.ok) throw new Error(`Extract failed: ${res.status}`);
    return res.json() as Promise<{
      temp_id?: string; filename?: string;
      metadata?: { title: string; authors: string[]; year: number; doi: string; abstract: string; journal: string };
      has_text?: boolean; text_preview?: string;
      duplicate?: boolean; paper?: PaperDetail;
    }>;
  },
  confirmImport: (tempId: string, metadata: Record<string, unknown>, filename: string) =>
    request<PaperDetail>("/api/papers/confirm-import", {
      method: "POST", body: JSON.stringify({ temp_id: tempId, metadata, filename }),
    }),
  lookupMetadata: (doi: string, title: string) =>
    request<{ metadata: Record<string, unknown> }>("/api/papers/lookup-metadata", {
      method: "POST", body: JSON.stringify({ doi, title }),
    }),

  // v4.4.0 新增: 引用格式修正
  correctCitation: (paperId: string, method: "doi" | "title") =>
    request<{ new_citation: string; metadata: Record<string, unknown>; old_citation: string }>(
      `/api/papers/${paperId}/correct-citation`, { method: "POST", body: JSON.stringify({ method }) }),
  applyCitation: (paperId: string, metadata: Record<string, unknown>) =>
    request<PaperDetail>(`/api/papers/${paperId}/apply-citation`, {
      method: "POST", body: JSON.stringify({ metadata }),
    }),

  // v4.1.0 新增: 分类管理
  listCategories: () => request<{ id: string; name: string; parent_id: string; sort_order: number; is_system: boolean; system_key: string; paper_count: number }[]>("/api/papers/categories"),
  createCategory: (name: string, parentId?: string) =>
    request<{ id: string; name: string }>("/api/papers/categories", {
      method: "POST", body: JSON.stringify({ name, parent_id: parentId || "" }),
    }),
  updateCategory: (id: string, data: { name?: string; parent_id?: string; sort_order?: number }) =>
    request<{ ok: boolean }>(`/api/papers/categories/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteCategory: (id: string) =>
    request<{ ok: boolean }>(`/api/papers/categories/${id}`, { method: "DELETE" }),
  setPaperCategories: (paperId: string, categoryIds: string[]) =>
    request<{ ok: boolean; count: number }>(`/api/papers/${paperId}/categories`, {
      method: "PUT", body: JSON.stringify({ category_ids: categoryIds }),
    }),
};

// ── arXiv ──────────────────────────────────────────────────

export interface ArxivPaper {
  title: string;
  authors: string[];
  abstract: string;
  arxiv_id: string;
  pdf_url: string;
  published: string;
  year: number;
  categories: string[];
  primary_category: string;
  source: string;
}

export const arxivApi = {
  search: (q: string, maxResults: number = 20) =>
    request<{ papers: ArxivPaper[]; count: number }>(`/api/arxiv/search?q=${encodeURIComponent(q)}&max_results=${maxResults}`),
  import: (arxivId: string) =>
    request<PaperDetail>("/api/arxiv/import", { method: "POST", body: JSON.stringify({ arxiv_id: arxivId }) }),
};

// ── MinerU ─────────────────────────────────────────────────

export const mineruApi = {
  status: () => request<{ available: boolean; version: string }>("/api/system/mineru-status"),
  convertMarkdown: (paperId: string) =>
    request<{ success: boolean; method: string; output_path: string; pages: number }>(
      `/api/papers/${paperId}/convert-markdown`, { method: "POST" }),
};

// ── Backup ─────────────────────────────────────────────────

export interface BackupItem {
  name: string;
  path: string;
  size: number;
  time: string;
}

export const backupApi = {
  list: () => request<BackupItem[]>("/api/backups"),
  create: () => request<{ path: string }>("/api/backup", { method: "POST" }),
  restore: (path: string) => request<{ ok: boolean }>("/api/backups/restore", {
    method: "POST", body: JSON.stringify({ path }),
  }),
  exportDb: async () => {
    const res = await fetch(`${API_BASE}/api/backups/export-db`, { headers: { ...getAuthHeader() } });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
  },
  importDb: async (data: ArrayBuffer) => {
    const res = await fetch(`${API_BASE}/api/backups/import-db`, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream", ...getAuthHeader() },
      body: data,
    });
    return res.json() as Promise<{ ok: boolean; detail?: string }>;
  },
};

// ── Reviews (综述) ──────────────────────────────────────────

export interface Review {
  id: string;
  title: string;
  content: string;
  paper_ids: string[];
  created_at: string;
}

export const reviewsApi = {
  list: () => request<Review[]>("/api/reviews"),
  get: (id: string) => request<Review>(`/api/reviews/${id}`),
  delete: (id: string) => request<{ ok: boolean }>(`/api/reviews/${id}`, { method: "DELETE" }),
  generate: (paperIds: string[], title?: string) =>
    streamRequest("/api/reviews/generate", { paper_ids: paperIds, title: title || "" }),
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

// ── Writing (写作工作台) ──────────────────────────────────────

export interface WritingDocument {
  id: string;
  title: string;
  content: string;
  outline: string[];
  linked_paper_ids: string[];
  document_type: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export const writingApi = {
  list: (document_type?: string) => {
    const p = document_type ? `?document_type=${document_type}` : "";
    return request<{ documents: WritingDocument[] }>(`/api/writing/documents${p}`);
  },
  get: (id: string) => request<WritingDocument>(`/api/writing/documents/${id}`),
  create: (data: { title?: string; content?: string; document_type?: string }) =>
    request<{ id: string }>("/api/writing/documents", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<WritingDocument>) =>
    request<{ id: string; word_count: number }>(`/api/writing/documents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) => request<{ ok: boolean }>(`/api/writing/documents/${id}`, { method: "DELETE" }),
  linkPaper: (docId: string, paperId: string) =>
    request<{ id: string; linked_paper_ids: string[] }>(`/api/writing/documents/${docId}/link-paper`, { method: "POST", body: JSON.stringify({ paper_id: paperId }) }),
  aiOperation: (docId: string, operation: string, text?: string) =>
    request<{ result: string; operation: string }>(`/api/writing/documents/${docId}/ai`, { method: "POST", body: JSON.stringify({ operation, text }) }),
  exportDoc: (docId: string, fmt: string = "markdown") =>
    request<{ content: string; filename: string }>(`/api/writing/documents/${docId}/export?fmt=${fmt}`),
};

// ── Enhanced Search (布尔检索) ────────────────────────────────

export interface SearchGroup {
  keywords: string[];
  field: string; // title/abstract/all
  operator: string; // AND/OR/NOT
}

export const enhancedSearchApi = {
  search: (groups: SearchGroup[], sources?: string[], max_results?: number) =>
    request<{ papers: Record<string, unknown>[]; count: number; query: string }>("/api/search/enhanced", {
      method: "POST",
      body: JSON.stringify({ groups, sources, max_results }),
    }),
  batchImport: (papers: Record<string, unknown>[]) =>
    request<{ imported: number; skipped: number }>("/api/papers/batch-import", {
      method: "POST",
      body: JSON.stringify({ papers }),
    }),
};

// ── Smart Review (智能综述) ───────────────────────────────────

export const smartReviewApi = {
  generate: (paperIds: string[], title?: string, sections?: string[]) =>
    request<{ id: string; title: string; content: string }>("/api/reviews/smart-generate", {
      method: "POST",
      body: JSON.stringify({ paper_ids: paperIds, title: title || "文献综述", sections }),
    }),
};

// ── Knowledge URL Import ─────────────────────────────────────

export const knowledgeImportApi = {
  fromUrl: (url: string) =>
    request<{ id: string; title: string; error?: string }>("/api/knowledge/import/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  fromJson: (data: unknown) =>
    request<{ imported: number }>("/api/knowledge/import/json", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  fromMarkdown: (content: string, filename: string) =>
    request<{ imported: number }>("/api/knowledge/import/md", {
      method: "POST",
      body: JSON.stringify({ content, filename }),
    }),
  fromPdf: async (file: File) => {
    const arrayBuffer = await file.arrayBuffer();
    const res = await fetch(`${API_BASE}/api/knowledge/import/pdf`, {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Filename": encodeURIComponent(file.name),
        ...getAuthHeader(),
      },
      body: arrayBuffer,
    });
    if (!res.ok) throw new Error(`Import failed: ${res.status}`);
    return res.json() as Promise<{ title?: string; error?: string }>;
  },
};
