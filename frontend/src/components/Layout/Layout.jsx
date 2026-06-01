import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import ScopeBar from './ScopeBar'
import CommandPalette from '../CommandPalette/CommandPalette'
import Drawer from '../Drawer/Drawer'
import useStore from '../../stores/useStore'
import styles from './Layout.module.css'

export default function Layout() {
  const commandPaletteOpen = useStore((s) => s.commandPaletteOpen)
  const drawerOpen = useStore((s) => s.drawerOpen)

  return (
    <div className={styles.layout}>
      <Sidebar />
      <div className={styles.main}>
        <TopBar />
        <div className={styles.content}>
          <Outlet />
        </div>
        <ScopeBar />
      </div>
      {drawerOpen && <Drawer />}
      {commandPaletteOpen && <CommandPalette />}
    </div>
  )
}
