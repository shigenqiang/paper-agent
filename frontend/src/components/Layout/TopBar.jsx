import { Search, Command } from 'lucide-react'
import useStore from '../../stores/useStore'
import styles from './TopBar.module.css'

export default function TopBar() {
  const toggleCommandPalette = useStore((s) => s.toggleCommandPalette)
  const currentProject = useStore((s) => s.currentProject)

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <h1 className={styles.projectName}>
          {currentProject?.name || '论文知识库分析 Agent'}
        </h1>
      </div>

      <button className={styles.searchBtn} onClick={toggleCommandPalette}>
        <Search size={15} />
        <span>搜索论文、命令...</span>
        <kbd className={styles.kbd}>
          <Command size={11} />K
        </kbd>
      </button>

      <div className={styles.right}>
        <span className={styles.hint}>Ctrl+K 命令面板</span>
      </div>
    </header>
  )
}
