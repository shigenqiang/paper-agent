import { useAppStore } from '@/stores/appStore'
import type { ResearchStatus } from '@/types'
import clsx from 'clsx'

const steps: { key: ResearchStatus; label: string; icon: string }[] = [
  { key: 'planning', label: '规划研究方案', icon: '🎯' },
  { key: 'searching', label: '搜索论文', icon: '🔍' },
  { key: 'reading', label: '阅读分析', icon: '📖' },
  { key: 'analysing', label: '深度分析', icon: '🧠' },
  { key: 'writing', label: '撰写报告', icon: '✍️' },
  { key: 'reviewing', label: '审校完善', icon: '✅' },
]

export default function ProgressTracker() {
  const status = useAppStore((s) => s.status)

  const currentIdx = steps.findIndex((s) => s.key === status)

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-4">研究进度</h2>
      <div className="flex items-center gap-1">
        {steps.map((step, i) => {
          const done = i < currentIdx
          const active = i === currentIdx
          return (
            <div key={step.key} className="flex-1 flex flex-col items-center gap-1.5">
              {/* bar */}
              <div className="w-full flex items-center gap-1">
                <div
                  className={clsx(
                    'h-1.5 flex-1 rounded-full transition-colors',
                    done || active ? 'bg-brand-500' : 'bg-gray-200 dark:bg-gray-700'
                  )}
                />
              </div>
              {/* label */}
              <div className={clsx('text-xs', active ? 'text-brand-600 font-medium' : done ? 'text-gray-500' : 'text-gray-300')}>
                <span className="mr-1">{step.icon}</span>
                {step.label}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
