import { create } from 'zustand'
import type { AgentEvent, Paper, ResearchStatus, ChatMessage } from '@/types'

interface AppState {
  // current research session
  taskId: string | null
  query: string
  status: ResearchStatus
  events: AgentEvent[]
  papers: Paper[]
  report: string | null
  error: string | null

  // chat
  messages: ChatMessage[]

  // ui
  sidebarOpen: boolean
  darkMode: boolean

  // actions
  setQuery: (q: string) => void
  startTask: (taskId: string, query: string) => void
  pushEvent: (e: AgentEvent) => void
  addPaper: (p: Paper) => void
  setReport: (r: string) => void
  setStatus: (s: ResearchStatus) => void
  setError: (e: string) => void
  resetSession: () => void
  addMessage: (m: ChatMessage) => void
  toggleSidebar: () => void
  toggleDarkMode: () => void
}

const sessionDefaults = {
  taskId: null,
  query: '',
  status: 'idle' as ResearchStatus,
  events: [],
  papers: [],
  report: null,
  error: null,
}

export const useAppStore = create<AppState>((set) => ({
  ...sessionDefaults,
  messages: [],
  sidebarOpen: true,
  darkMode: false,

  setQuery: (query) => set({ query }),

  startTask: (taskId, query) =>
    set({ ...sessionDefaults, taskId, query, status: 'planning' }),

  pushEvent: (e) =>
    set((s) => ({ events: [...s.events, e] })),

  addPaper: (p) =>
    set((s) => ({
      papers: s.papers.find((x) => x.id === p.id) ? s.papers : [...s.papers, p],
    })),

  setReport: (report) => set({ report }),

  setStatus: (status) => set({ status }),

  setError: (error) => set({ error, status: 'error' }),

  resetSession: () => set(sessionDefaults),

  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  toggleDarkMode: () =>
    set((s) => {
      const next = !s.darkMode
      document.documentElement.classList.toggle('dark', next)
      return { darkMode: next }
    }),
}))
