import { Layers, ChevronRight } from 'lucide-react'
import useStore from '../../stores/useStore'
import styles from './ScopeBar.module.css'

export default function ScopeBar() {
  const scope = useStore((s) => s.scope)
  const papers = useStore((s) => s.papers)

  return (
    <footer className={styles.scopeBar}>
      <div className={styles.scopeInfo}>
        <Layers size={14} className={styles.icon} />
        <span className={styles.scopeType}>{scope.label}</span>
        <ChevronRight size={12} className={styles.divider} />
        <span className={styles.count}>
          {scope.paperIds.length > 0 ? `${scope.paperIds.length}篇论文` : `${papers.length}篇论文`}
        </span>
      </div>
      <button className={styles.changeBtn}>修改范围</button>
    </footer>
  )
}
