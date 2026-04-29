import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const DEFAULT_SECTIONS = [
  { id: '1', title: '第1章 引言', parentId: null, content: '' },
  { id: '1-1', title: '1.1 研究背景', parentId: '1', content: '' },
  { id: '1-2', title: '1.2 研究意义', parentId: '1', content: '' },
  { id: '1-3', title: '1.3 研究目标', parentId: '1', content: '' },
  { id: '2', title: '第2章 文献综述', parentId: null, content: '' },
  { id: '2-1', title: '2.1 国内研究现状', parentId: '2', content: '' },
  { id: '2-2', title: '2.2 国外研究现状', parentId: '2', content: '' },
  { id: '3', title: '第3章 研究方法', parentId: null, content: '' },
  { id: '4', title: '第4章 实验结果', parentId: null, content: '' },
  { id: '5', title: '第5章 讨论', parentId: null, content: '' },
  { id: '6', title: '第6章 结论', parentId: null, content: '' },
]

export const usePaperStore = create(
  persist(
    (set, get) => ({
  project: {
    id: null,
    title: '',
    sections: DEFAULT_SECTIONS,
    citations: [],
    status: 'idle'
  },
  messages: [],
  isStreaming: false,
  literature: [],
  sidebarCollapsed: false,
  theme: 'light',

  setProject: (project) => set({ project }),

  setTitle: (title) => set((state) => ({
    project: { ...state.project, title }
  })),

  addSection: (section) => set((state) => ({
    project: {
      ...state.project,
      sections: [...state.project.sections, section]
    }
  })),

  updateSection: (id, content) => set((state) => ({
    project: {
      ...state.project,
      sections: state.project.sections.map(s =>
        s.id === id ? { ...s, content } : s
      )
    }
  })),

  deleteSection: (id) => set((state) => ({
    project: {
      ...state.project,
      sections: state.project.sections.filter(s => s.id !== id)
    }
  })),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(m =>
      m.id === id ? { ...m, ...updates } : m
    )
  })),

  setStreaming: (isStreaming) => set({ isStreaming }),

  addCitation: (citation) => set((state) => ({
    project: {
      ...state.project,
      citations: [...state.project.citations, citation]
    }
  })),

  addLiterature: (item) => set((state) => ({
    literature: [...state.literature, item]
  })),

  deleteLiterature: (id) => set((state) => ({
    literature: state.literature.filter(item => item.id !== id)
  })),

  setLiterature: (items) => set({ literature: items }),

  updateLiterature: (id, updates) => set((state) => ({
    literature: state.literature.map(l =>
      l.id === id ? { ...l, ...updates } : l
    )
  })),

  removeCitation: (id) => set((state) => ({
    project: {
      ...state.project,
      citations: state.project.citations.filter(c => c.id !== id)
    }
  })),

  toggleSidebar: () => set((state) => ({
    sidebarCollapsed: !state.sidebarCollapsed
  })),

  setTheme: (theme) => set({ theme }),

  resetProject: () => set({
    project: {
      id: null,
      title: '',
      sections: DEFAULT_SECTIONS,
      citations: [],
      status: 'idle'
    },
    messages: [],
    isStreaming: false
  })
}),
    {
      name: 'paper-agent-storage', // storage key
      partialize: (state) => ({
        literature: state.literature,
        project: state.project,
        messages: state.messages,
        theme: state.theme,
      }), // only persist these fields
    }
  )
)
