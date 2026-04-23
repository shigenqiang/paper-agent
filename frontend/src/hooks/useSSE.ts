import { useEffect, useRef, useCallback } from 'react'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import type { AgentEvent, Paper } from '@/types'

/**
 * SSE hook — connects to the research stream endpoint
 * and pushes events / papers into the global store.
 */
export function useSSE(taskId: string | null) {
  const esRef = useRef<EventSource | null>(null)
  const pushEvent = useAppStore((s) => s.pushEvent)
  const addPaper = useAppStore((s) => s.addPaper)
  const setReport = useAppStore((s) => s.setReport)
  const setStatus = useAppStore((s) => s.setStatus)
  const setError = useAppStore((s) => s.setError)

  const connect = useCallback(() => {
    if (!taskId) return
    disconnect()

    const url = api.streamUrl(taskId)
    const es = new EventSource(url)
    esRef.current = es

    es.addEventListener('agent_event', (raw) => {
      const e = JSON.parse(raw.data) as AgentEvent
      pushEvent(e)

      switch (e.type) {
        case 'paper_found':
          addPaper(e.data as Paper)
          break
        case 'writing_update':
          if ((e.data as any)?.report) setReport((e.data as any).report)
          break
        case 'done':
          setStatus('done')
          es.close()
          break
        case 'error':
          setError(e.message)
          es.close()
          break
      }
    })

    es.onerror = () => {
      console.warn('[SSE] connection lost')
      // don't auto-reconnect for finished tasks
    }
  }, [taskId])

  const disconnect = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  useEffect(() => {
    if (taskId) connect()
    return () => disconnect()
  }, [taskId, connect, disconnect])

  return { connect, disconnect }
}
