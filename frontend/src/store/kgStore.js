import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useKGStore = create(
  persist(
    (set) => ({
      viewMode: 'year',
      showFilters: true,
      sortBy: 'citations',
      queryText: '',
      queryResult: null,
      showQueryPanel: false,

      setViewMode: (mode) => set({ viewMode: mode }),
      setShowFilters: (show) => set({ showFilters: show }),
      setSortBy: (sortBy) => set({ sortBy }),
      setQueryText: (text) => set({ queryText: text }),
      setQueryResult: (result) => set({ queryResult: result }),
      setShowQueryPanel: (show) => set({ showQueryPanel: show }),
    }),
    {
      name: 'paper-kg-storage',
      partialize: (state) => ({
        viewMode: state.viewMode,
        showFilters: state.showFilters,
        sortBy: state.sortBy,
        queryText: state.queryText,
        queryResult: state.queryResult,
        showQueryPanel: state.showQueryPanel,
      }),
    }
  )
)
