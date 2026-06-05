import { useState, useEffect } from 'react'
import { Search, Command, ChevronDown } from 'lucide-react'
import useStore from '../../stores/useStore'
import { api } from '../../api/client'
import styles from './TopBar.module.css'

export default function TopBar() {
  const toggleCommandPalette = useStore((s) => s.toggleCommandPalette)
  const currentProject = useStore((s) => s.currentProject)
  const setCurrentProject = useStore((s) => s.setCurrentProject)
  const [projects, setProjects] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)

  useEffect(() => {
    api.listProjects().then((res) => {
      setProjects(res.data || res || [])
    }).catch(() => {})
  }, [])

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <div style={{ position: 'relative' }}>
          <h1
            className={styles.projectName}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
            onClick={() => setShowDropdown(!showDropdown)}
          >
            {currentProject?.name || '论文知识库分析 Agent'}
            <ChevronDown size={14} />
          </h1>
          {showDropdown && projects.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, zIndex: 100,
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: '8px', padding: '4px', minWidth: '200px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            }}>
              {projects.map((p) => (
                <button
                  key={p.project_id}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '8px 12px', background: 'none', border: 'none',
                    color: p.project_id === currentProject?.project_id ? 'var(--accent)' : 'var(--text)',
                    cursor: 'pointer', borderRadius: '4px', fontSize: '0.85rem',
                  }}
                  onClick={() => { setCurrentProject(p); setShowDropdown(false) }}
                  onMouseEnter={(e) => e.target.style.background = 'var(--bg-hover)'}
                  onMouseLeave={(e) => e.target.style.background = 'none'}
                >
                  {p.name}
                </button>
              ))}
            </div>
          )}
        </div>
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
