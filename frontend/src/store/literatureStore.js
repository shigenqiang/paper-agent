import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useLiteratureStore = create(
  persist(
    (set) => ({
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
    }),
    {
      name: 'paper-literature-storage',
      partialize: (state) => ({
        literature: state.literature,
      }),
    }
  )
)
