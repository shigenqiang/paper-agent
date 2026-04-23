import { NavLink } from 'react-router-dom'
import {
  Search, BookOpen, FileText, GitBranch, MessageSquare, ChevronLeft, ChevronRight
} from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import clsx from 'clsx'

const links = [
  { to: '/', icon: Search, label: '研究' },
  { to: '/papers', icon: BookOpen, label: '论文库' },
  { to: '/reports', icon: FileText, label: '报告' },
  { to: '/graph', icon: GitBranch, label: '知识图谱' },
  { to: '/chat', icon: MessageSquare, label: '对话' },
]

export default function Sidebar() {
  const open = useAppStore((s) => s.sidebarOpen)
  const toggle = useAppStore((s) => s.toggleSidebar)
  const dark = useAppStore((s) => s.darkMode)
  const toggleDark = useAppStore((s) => s.toggleDarkMode)

  return (
    <aside
      className={clsx(
        'fixed inset-y-0 left-0 z-30 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all',
        open ? 'w-60' : 'w-16'
      )}
    >
      {/* brand */}
      <div className="h-14 flex items-center px-4 gap-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xl">📄</span>
        {open && <span className="font-semibold text-sm whitespace-nowrap">Paper Agent</span>}
      </div>

      {/* nav links */}
      <nav className="flex-1 py-4 flex flex-col gap-1 px-2">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              )
            }
          >
            <Icon size={18} />
            {open && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* footer */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-2 flex flex-col gap-1">
        <button
          onClick={toggleDark}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 w-full"
        >
          <span>{dark ? '☀️' : '🌙'}</span>
          {open && <span>{dark ? '亮色模式' : '暗色模式'}</span>}
        </button>
        <button
          onClick={toggle}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 w-full"
        >
          {open ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          {open && <span>收起侧栏</span>}
        </button>
      </div>
    </aside>
  )
}
