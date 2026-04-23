import { useState } from 'react'
import { Search, Loader2, BookOpen } from 'lucide-react'
import { useResearch } from '@/hooks/useResearch'
import { useAppStore } from '@/stores/appStore'
import ProgressTracker from '@/components/ProgressTracker'
import PaperCard from '@/components/PaperCard'
import ReportViewer from '@/components/ReportViewer'

export default function ResearchPage() {
  const [input, setInput] = useState('')
  const { start, status } = useResearch()
  const papers = useAppStore((s) => s.papers)
  const report = useAppStore((s) => s.report)
  const events = useAppStore((s) => s.events)
  const error = useAppStore((s) => s.error)
  const running = status !== 'idle' && status !== 'done' && status !== 'error'

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || running) return
    start(input.trim())
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      {/* query input */}
      <section className="text-center space-y-4">
        <h1 className="text-3xl font-bold">
          智能论文研究助手
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          输入研究主题，自动搜索、阅读、分析并生成综述报告
        </p>
        <form onSubmit={handleSubmit} className="flex gap-2 max-w-2xl mx-auto">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="例如：大语言模型的幻觉问题"
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-brand-500 focus:outline-none text-sm"
              disabled={running}
            />
          </div>
          <button
            type="submit"
            disabled={running || !input.trim()}
            className="px-6 py-3 rounded-xl bg-brand-600 text-white font-medium text-sm hover:bg-brand-700 disabled:opacity-50 flex items-center gap-2 transition-colors"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            {running ? '研究中…' : '开始研究'}
          </button>
        </form>
      </section>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* progress tracker */}
      {running && <ProgressTracker />}

      {/* papers discovered */}
      {papers.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BookOpen size={18} />
            发现论文 ({papers.length})
          </h2>
          <div className="grid gap-3">
            {papers.map((p) => <PaperCard key={p.id} paper={p} />)}
          </div>
        </section>
      )}

      {/* report */}
      {report && <ReportViewer content={report} />}

      {/* event log (collapsible) */}
      {events.length > 0 && (
        <details className="text-xs text-gray-500 dark:text-gray-400">
          <summary className="cursor-pointer mb-2">事件日志 ({events.length})</summary>
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 max-h-64 overflow-auto space-y-1 font-mono">
            {events.map((e, i) => (
              <div key={i}>[{e.agent}] {e.message}</div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
