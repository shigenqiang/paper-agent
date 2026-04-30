import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useLiteratureStore = create(
  persist(
    (set) => ({
      // 文献库
      literature: [],

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

      clearLiterature: () => set({ literature: [] }),

      // 搜索状态（持久化，切换页面不丢失）
      searchResults: [],
      searchQuery: '',
      searchLoading: false,
      hasMore: false,
      currentPage: 1,
      activeTab: 'library',
      graphVisible: false,

      setSearchResults: (results) => set({ searchResults: results }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setSearchLoading: (loading) => set({ searchLoading: loading }),
      setHasMore: (hasMore) => set({ hasMore }),
      setCurrentPage: (page) => set({ currentPage: page }),
      setActiveTab: (tab) => set({ activeTab: tab }),
      setGraphVisible: (visible) => set({ graphVisible: visible }),
    }),
    {
      name: 'paper-literature-storage',
      partialize: (state) => ({
        literature: state.literature,
        searchResults: state.searchResults,
        searchQuery: state.searchQuery,
        hasMore: state.hasMore,
        currentPage: state.currentPage,
        activeTab: state.activeTab,
      }),
    }
  )
)
