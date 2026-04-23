import { useCallback } from 'react'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import { useSSE } from './useSSE'

/**
 * Orchestrates the full research lifecycle:
 *  1. POST /research/start
 *  2. Open SSE stream
 *  3. Store task_id in global state
 */
export function useResearch() {
  const { taskId, startTask, status } = useAppStore((s) => ({
    taskId: s.taskId,
    query: s.query,
    startTask: s.startTask,
    status: s.status,
  }))
  const { connect } = useSSE(taskId)

  const start = useCallback(async (query: string) => {
    try {
      const { task_id } = await api.startResearch(query)
      startTask(task_id, query)
      // SSE auto-connects when taskId changes via useEffect in useSSE
    } catch (e: unknown) {
      useAppStore.getState().setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  return { start, taskId, status }
}
