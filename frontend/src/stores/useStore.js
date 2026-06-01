import { create } from 'zustand'

const useStore = create((set, get) => ({
  // ── Project ──
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  // ── Papers ──
  papers: [],
  selectedPaperIds: [],
  setPapers: (papers) => set({ papers }),
  togglePaperSelection: (id) => set((s) => ({
    selectedPaperIds: s.selectedPaperIds.includes(id)
      ? s.selectedPaperIds.filter((i) => i !== id)
      : [...s.selectedPaperIds, id],
  })),
  clearSelection: () => set({ selectedPaperIds: [] }),

  // ── Scope ──
  scope: { type: 'project', label: '全项目', paperIds: [] },
  setScope: (scope) => set({ scope }),

  // ── Knowledge Graph ──
  graph: { nodes: [], edges: [] },
  selectedNodeIds: [],
  setGraph: (graph) => set({ graph }),
  toggleNodeSelection: (id) => set((s) => ({
    selectedNodeIds: s.selectedNodeIds.includes(id)
      ? s.selectedNodeIds.filter((i) => i !== id)
      : [...s.selectedNodeIds, id],
  })),
  clearNodeSelection: () => set({ selectedNodeIds: [] }),

  // ── QA ──
  qaMessages: [],
  qaLoading: false,
  addQAMessage: (msg) => set((s) => ({ qaMessages: [...s.qaMessages, msg] })),
  setQALoading: (loading) => set({ qaLoading: loading }),
  clearQAMessages: () => set({ qaMessages: [] }),

  // ── Reports ──
  reports: [],
  setReports: (reports) => set({ reports }),

  // ── UI State ──
  drawerOpen: false,
  drawerContent: null,
  commandPaletteOpen: false,
  openDrawer: (content) => set({ drawerOpen: true, drawerContent: content }),
  closeDrawer: () => set({ drawerOpen: false, drawerContent: null }),
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
}))

export default useStore
