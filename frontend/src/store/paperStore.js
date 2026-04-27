import { create } from 'zustand'

export const usePaperStore = create((set, get) => ({
  // 项目状态
  project: {
    id: null,
    title: '',
    sections: [],
    citations: [],
    status: 'idle'
  },

  // AI对话状态
  messages: [],
  isStreaming: false,

  // 文献库
  literature: [],

  // UI状态
  sidebarCollapsed: false,
  theme: 'light',

  // 操作方法
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

  toggleSidebar: () => set((state) => ({
    sidebarCollapsed: !state.sidebarCollapsed
  })),

  setTheme: (theme) => set({ theme }),

  resetProject: () => set({
    project: {
      id: null,
      title: '',
      sections: [],
      citations: [],
      status: 'idle'
    },
    messages: [],
    isStreaming: false
  })
}))