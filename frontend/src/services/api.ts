import type { KnowledgeGraph, Paper, Report, ResearchTask, ChatMessage } from '@/types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ─── Research ────────────────────────────────────────────────────────────────

export const api = {
  startResearch: (query: string) =>
    request<{ task_id: string }>('/research/start', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  getTask: (taskId: string) =>
    request<ResearchTask>(`/research/${taskId}`),

  listTasks: () =>
    request<ResearchTask[]>('/research'),

  // SSE stream — caller manages EventSource lifecycle
  streamUrl: (taskId: string) => `${BASE}/research/stream/${taskId}`,

  // ─── Papers ──────────────────────────────────────────────────────────────
  listPapers: (params?: { query?: string; theme?: string; page?: number }) => {
    const qs = new URLSearchParams(
      Object.entries(params ?? {}).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])
    ).toString()
    return request<{ papers: Paper[]; total: number }>(`/papers${qs ? `?${qs}` : ''}`)
  },

  getPaper: (id: string) => request<Paper>(`/papers/${id}`),

  // ─── Reports ─────────────────────────────────────────────────────────────
  listReports: () => request<Report[]>('/reports'),

  getReport: (id: string) => request<Report>(`/reports/${id}`),

  // ─── Knowledge graph ─────────────────────────────────────────────────────
  getKnowledgeGraph: (taskId?: string) =>
    request<KnowledgeGraph>(`/knowledge-graph${taskId ? `?task_id=${taskId}` : ''}`),

  // ─── Chat ─────────────────────────────────────────────────────────────────
  chat: (message: string, taskId?: string) =>
    request<ChatMessage>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, task_id: taskId }),
    }),
}
