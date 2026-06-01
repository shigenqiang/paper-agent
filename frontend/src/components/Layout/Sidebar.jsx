import { NavLink } from 'react-router-dom'
import { BookOpen, Network, MessageSquare, FileText, Settings, Sparkles } from 'lucide-react'
import styles from './Sidebar.module.css'

const navItems = [
  { path: '/library', icon: BookOpen, label: '论文库' },
  { path: '/graph', icon: Network, label: '知识图谱' },
  { path: '/qa', icon: MessageSquare, label: '研究 QA' },
  { path: '/reports', icon: FileText, label: '成果报告' },
]

export default function Sidebar() {
  return (
    <nav className={styles.sidebar}>
      <div className={styles.logo}>
        <Sparkles size={24} className={styles.logoIcon} />
      </div>

      <div className={styles.nav}>
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.active : ''}`
            }
          >
            <Icon size={20} />
            <span className={styles.label}>{label}</span>
          </NavLink>
        ))}
      </div>

      <div className={styles.bottom}>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `${styles.navItem} ${isActive ? styles.active : ''}`
          }
        >
          <Settings size={20} />
          <span className={styles.label}>设置</span>
        </NavLink>
      </div>
    </nav>
  )
}
