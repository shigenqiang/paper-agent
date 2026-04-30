/**
 * Paper Store - 统一导出
 *
 * 为了保持向后兼容，此文件重新导出各个拆分后的store。
 * 新代码应直接从对应的store文件导入。
 *
 * 拆分后的store：
 * - useProjectStore: 项目管理（sections, citations, status）
 * - useChatStore: 对话消息（messages, isStreaming）
 * - useLiteratureStore: 文献管理（literature）
 * - useUIStore: UI状态（sidebarCollapsed, theme）
 */

import { useProjectStore } from './projectStore'
import { useChatStore } from './chatStore'
import { useLiteratureStore } from './literatureStore'
import { useUIStore } from './uiStore'

// 向后兼容：保留原始的usePaperStore接口
// @deprecated 请使用上述各个专门的store
export const usePaperStore = () => {
  console.warn('usePaperStore is deprecated. Please use useProjectStore, useChatStore, useLiteratureStore, or useUIStore instead.')

  // 返回一个合并的对象，保持原有接口
  const projectStore = useProjectStore()
  const chatStore = useChatStore()
  const literatureStore = useLiteratureStore()
  const uiStore = useUIStore()

  return {
    // Project state
    project: projectStore.project,
    setProject: projectStore.setProject,
    setTitle: projectStore.setTitle,
    addSection: projectStore.addSection,
    updateSection: projectStore.updateSection,
    deleteSection: projectStore.deleteSection,
    addCitation: projectStore.addCitation,
    removeCitation: projectStore.removeCitation,
    resetProject: () => {
      projectStore.resetProject()
      chatStore.resetChat()
    },

    // Chat state
    messages: chatStore.messages,
    addMessage: chatStore.addMessage,
    updateMessage: chatStore.updateMessage,
    isStreaming: chatStore.isStreaming,
    setStreaming: chatStore.setStreaming,

    // Literature state
    literature: literatureStore.literature,
    addLiterature: literatureStore.addLiterature,
    deleteLiterature: literatureStore.deleteLiterature,
    setLiterature: literatureStore.setLiterature,
    updateLiterature: literatureStore.updateLiterature,

    // UI state
    sidebarCollapsed: uiStore.sidebarCollapsed,
    toggleSidebar: uiStore.toggleSidebar,
    theme: uiStore.theme,
    setTheme: uiStore.setTheme,
  }
}

// 导出各个独立的store供新代码使用
export { useProjectStore } from './projectStore'
export { useChatStore } from './chatStore'
export { useLiteratureStore } from './literatureStore'
export { useUIStore } from './uiStore'
