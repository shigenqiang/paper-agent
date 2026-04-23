import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAppStore } from '@/stores/appStore'
import clsx from 'clsx'

export default function Layout() {
  const open = useAppStore((s) => s.sidebarOpen)
  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar />
      <main className={clsx('flex-1 overflow-auto transition-all', open ? 'ml-60' : 'ml-16')}>
        <Outlet />
      </main>
    </div>
  )
}
