import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { DEFAULT_SECTIONS, INITIAL_PROJECT_STATE } from '../constants/paper'

export const useProjectStore = create(
  persist(
    (set) => ({
      project: { ...INITIAL_PROJECT_STATE },

      setProject: (project) => set({ project }),

      setTitle: (title) => set((state) => ({
        project: { ...state.project, title }
      })),

      setStatus: (status) => set((state) => ({
        project: { ...state.project, status }
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

      addCitation: (citation) => set((state) => ({
        project: {
          ...state.project,
          citations: [...state.project.citations, citation]
        }
      })),

      removeCitation: (id) => set((state) => ({
        project: {
          ...state.project,
          citations: state.project.citations.filter(c => c.id !== id)
        }
      })),

      resetProject: () => set({
        project: { ...INITIAL_PROJECT_STATE }
      }),
    }),
    {
      name: 'paper-project-storage',
      partialize: (state) => ({
        project: state.project,
      }),
    }
  )
)
