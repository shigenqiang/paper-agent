import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useWritingStore = create(
  persist(
    (set) => ({
      selectedSection: '1-1',
      sectionContent: '',
      paperTitle: '未命名论文',
      citeStyle: 'APA',
      editorMode: 'split',
      showFullPreview: false,
      showFullEdit: false,

      setSelectedSection: (section) => set({ selectedSection: section }),
      setSectionContent: (content) => set({ sectionContent: content }),
      setPaperTitle: (title) => set({ paperTitle: title }),
      setCiteStyle: (style) => set({ citeStyle: style }),
      setEditorMode: (mode) => set({ editorMode: mode }),
      setShowFullPreview: (show) => set({ showFullPreview: show }),
      setShowFullEdit: (show) => set({ showFullEdit: show }),
    }),
    {
      name: 'paper-writing-storage',
      partialize: (state) => ({
        selectedSection: state.selectedSection,
        sectionContent: state.sectionContent,
        paperTitle: state.paperTitle,
        citeStyle: state.citeStyle,
        editorMode: state.editorMode,
        showFullPreview: state.showFullPreview,
        showFullEdit: state.showFullEdit,
      }),
    }
  )
)
