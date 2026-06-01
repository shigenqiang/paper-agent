import { X } from 'lucide-react'
import useStore from '../../stores/useStore'
import styles from './Drawer.module.css'

export default function Drawer() {
  const drawerContent = useStore((s) => s.drawerContent)
  const closeDrawer = useStore((s) => s.closeDrawer)

  return (
    <div className={styles.overlay} onClick={closeDrawer}>
      <aside className={styles.drawer} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>论文详情</h2>
          <button className={styles.closeBtn} onClick={closeDrawer}>
            <X size={18} />
          </button>
        </div>
        <div className={styles.content}>
          {drawerContent || (
            <div className={styles.placeholder}>
              <p>选择一篇论文查看详情</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
