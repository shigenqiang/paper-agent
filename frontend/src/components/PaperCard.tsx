import { ExternalLink } from 'lucide-react'
import type { Paper } from '@/types'
import clsx from 'clsx'

export default function PaperCard({ paper, detailed = false }: { paper: Paper; detailed?: boolean }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm leading-snug">{paper.title}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {paper.authors.slice(0, 3).join(', ')}
            {paper.authors.length > 3 && ' et al.'}
            {' · '}{paper.year}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {paper.relevance_score != null && (
            <span className={clsx(
              'text-xs px-2 py-0.5 rounded-full font-medium',
              paper.relevance_score > 0.8 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
              paper.relevance_score > 0.5 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
              'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
            )}>
              {(paper.relevance_score * 100).toFixed(0)}%
            </span>
          )}
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-brand-500">
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </div>

      {detailed && paper.abstract && (
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-4">{paper.abstract}</p>
      )}

      {detailed && paper.themes && paper.themes.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {paper.themes.map((t) => (
            <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
        <span className="capitalize">{paper.source}</span>
        {paper.citations != null && <span>{paper.citations} 引用</span>}
      </div>
    </div>
  )
}
