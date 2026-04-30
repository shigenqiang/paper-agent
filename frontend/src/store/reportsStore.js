import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useReportsStore = create(
  persist(
    (set) => ({
      activeTab: 'daily',
      selectedDigest: null,
      digests: [],
      keywords: [],

      setActiveTab: (tab) => set({ activeTab: tab }),
      setSelectedDigest: (digest) => set({ selectedDigest: digest }),
      setDigests: (digests) => set({ digests }),
      setKeywords: (keywords) => set({ keywords }),
    }),
    {
      name: 'paper-reports-storage',
      partialize: (state) => ({
        activeTab: state.activeTab,
        selectedDigest: state.selectedDigest,
        digests: state.digests,
        keywords: state.keywords,
      }),
    }
  )
)
