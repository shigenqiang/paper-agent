import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// 默认分类文件夹
const DEFAULT_FOLDERS = [
  { id: 'default', name: '我的论文', icon: 'folder' },
  { id: 'research', name: '研究笔记', icon: 'folder' },
  { id: 'reference', name: '参考文献', icon: 'folder' },
]

export const useAssistantStore = create(
  persist(
    (set) => ({
      mode: 'write',
      folders: DEFAULT_FOLDERS,
      papers: [], // [{ id, title, topic, folderId, sections: [], createdAt }]
      selectedPaperId: null,
      expandedPaperIds: [],
      chatMessages: [],
      chatInput: '',
      contextText: '',
      reviseType: 'polish',

      setMode: (mode) => set({ mode }),
      setFolders: (folders) => set({ folders }),
      addFolder: (folder) => set((state) => ({ folders: [...state.folders, { ...folder, id: 'folder_' + Date.now() }] })),
      deleteFolder: (folderId) => set((state) => ({
        folders: state.folders.filter(f => f.id !== folderId),
        papers: state.papers.filter(p => p.folderId !== folderId),
      })),
      setPapers: (papers) => set({ papers }),
      setSelectedPaperId: (id) => set({ selectedPaperId: id }),
      togglePaperExpand: (id) => set((state) => ({
        expandedPaperIds: state.expandedPaperIds.includes(id)
          ? state.expandedPaperIds.filter(x => x !== id)
          : [...state.expandedPaperIds, id]
      })),
      setChatMessages: (messages) => set({ chatMessages: messages }),
      addChatMsg: (message) => set((state) => ({
        chatMessages: [...state.chatMessages, message]
      })),
      setChatInput: (input) => set({ chatInput: input }),
      setContextText: (text) => set({ contextText: text }),
      setReviseType: (type) => set({ reviseType: type }),
      clearChat: () => set({ chatMessages: [] }),
    }),
    {
      name: 'paper-assistant-storage-v2',
      version: 2,
      partialize: (state) => ({
        mode: state.mode,
        folders: state.folders,
        papers: state.papers,
        selectedPaperId: state.selectedPaperId,
        expandedPaperIds: state.expandedPaperIds,
        chatMessages: state.chatMessages,
        contextText: state.contextText,
        reviseType: state.reviseType,
      }),
      merge: (persistedState, currentState) => {
        const safe = { ...currentState }
        if (persistedState && typeof persistedState === 'object') {
          safe.mode = persistedState.mode ?? currentState.mode
          safe.folders = Array.isArray(persistedState.folders) ? persistedState.folders : currentState.folders
          safe.papers = Array.isArray(persistedState.papers) ? persistedState.papers : currentState.papers
          safe.selectedPaperId = persistedState.selectedPaperId ?? currentState.selectedPaperId
          safe.expandedPaperIds = Array.isArray(persistedState.expandedPaperIds) ? persistedState.expandedPaperIds : []
          safe.chatMessages = Array.isArray(persistedState.chatMessages) ? persistedState.chatMessages : currentState.chatMessages
          safe.contextText = typeof persistedState.contextText === 'string' ? persistedState.contextText : currentState.contextText
          safe.reviseType = persistedState.reviseType ?? currentState.reviseType
        }
        return safe
      },
    }
  )
)
