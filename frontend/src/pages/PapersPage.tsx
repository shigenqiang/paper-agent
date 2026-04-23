import { useState, useEffect } from 'react'
import { BookOpen, Search as SearchIcon } from 'lucide-react'
import { api } from '@/services/api'
import PaperCard from '@/components/PaperCard'
import type { Paper } from '@/types'

export default function PapersPage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.listPapers().then(({ papers: p }) => setPapers(p)).finally(() => setLoading(false))
  }, [])

  const filtered = q
    ? papers.filter((p) =>
        p.title.toLowerCase().includes(q.toLowerCase()) ||
        p.authors.some((a) => a.toLowerCase().includes(q.toLowerCase()))
      )
    : papers

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2"><BookOpen size={22} /> 论文库</h1>

      <div className="relative max-w-md">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜索论文标题或作者…"
          className="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
        />
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-12">加载中…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-400 py-12">暂无论文</div>
      ) : (
        <div className="grid gap-3">
          {filtered.map((p) => <PaperCard key={p.id} paper={p} detailed />)}
        </div>
      )}
    </div>
  )
}
