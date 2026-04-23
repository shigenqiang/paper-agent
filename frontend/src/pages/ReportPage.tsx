import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'
import { api } from '@/services/api'
import ReportViewer from '@/components/ReportViewer'
import type { Report } from '@/types'
import clsx from 'clsx'

export default function ReportPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [selected, setSelected] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listReports().then(setReports).finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex h-full">
      {/* list */}
      <aside className="w-72 border-r border-gray-200 dark:border-gray-700 overflow-auto p-4 space-y-2">
        <h2 className="text-lg font-bold flex items-center gap-2 mb-4"><FileText size={18} /> 报告列表</h2>
        {loading ? (
          <div className="text-gray-400 text-sm">加载中…</div>
        ) : reports.length === 0 ? (
          <div className="text-gray-400 text-sm">暂无报告</div>
        ) : (
          reports.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelected(r)}
              className={clsx(
                'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
                selected?.id === r.id
                  ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700'
              )}
            >
              <div className="font-medium truncate">{r.query}</div>
              <div className="text-xs text-gray-400 mt-0.5">{r.paper_count} 篇论文 · {new Date(r.created_at).toLocaleDateString()}</div>
            </button>
          ))
        )}
      </aside>

      {/* viewer */}
      <main className="flex-1 overflow-auto">
        {selected ? (
          <ReportViewer content={selected.content} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            选择一份报告查看
          </div>
        )}
      </main>
    </div>
  )
}
