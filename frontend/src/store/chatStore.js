import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useChatStore = create(
  persist(
    (set) => ({
      messages: [],
      isStreaming: false,

      addMessage: (message) => set((state) => ({
        messages: [...state.messages, message]
      })),

      updateMessage: (id, updates) => set((state) => ({
        messages: state.messages.map(m =>
          m.id === id ? { ...m, ...updates } : m
        )
      })),

      clearMessages: () => set({ messages: [] }),

      setStreaming: (isStreaming) => set({ isStreaming }),

      resetChat: () => set({
        messages: [],
        isStreaming: false
      }),
    }),
    {
      name: 'paper-chat-storage',
      partialize: (state) => ({
        messages: state.messages,
      }),
    }
  )
)
