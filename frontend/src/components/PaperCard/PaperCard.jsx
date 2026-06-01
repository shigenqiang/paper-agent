import { FileText, CheckCircle, Clock, XCircle, MessageSquare, Eye } from 'lucide-react'
import useStore from '../../stores/useStore'
import styles from './PaperCard.module.css'

const STATUS_MAP = {
  uploaded: { label: '已上传', icon: Clock, color: 'var(--text-muted)' },
  parsed: { label: '已解析', icon: CheckCircle, color: 'var(--green)' },
  excluded: { label: '已排除', icon: XCircle, color: 'var(--red)' },
  included: { label: '已纳入', icon: CheckCircle, color: 'var(--accent)' },
}

export default function PaperCard({ paper, onViewCard, onQA }) {
  const selectedPaperIds = useStore((s) => s.selectedPaperIds)
  const togglePaperSelection = useStore((s) => s.togglePaperSelection)

  const status = STATUS_MAP[paper.status] || STATUS_MAP.uploaded
  const StatusIcon = status.icon
  const isSelected = selectedPaperIds.includes(paper.paper_id)

  return (
    <div
      className={`${styles.card} ${isSelected ? styles.selected : ''}`}
      onClick={() => togglePaperSelection(paper.paper_id)}
    >
      <div className={styles.statusBar} style={{ background: status.color }} />

      <div className={styles.header}>
        <FileText size={16} className={styles.fileIcon} />
        <span className={styles.year}>{paper.year || '—'}</span>
      </div>

      <h3 className={styles.title}>{paper.title || 'Untitled'}</h3>

      <p className={styles.authors}>
        {paper.authors?.slice(0, 3).join(', ')}
        {paper.authors?.length > 3 && ` +${paper.authors.length - 3}`}
      </p>

      {paper.venue && (
        <span className={styles.venue}>{paper.venue}</span>
      )}

      <div className={styles.footer}>
        <span className={styles.status} style={{ color: status.color }}>
          <StatusIcon size={13} />
          {status.label}
        </span>

        <div className={styles.actions}>
          <button
            className={styles.actionBtn}
            onClick={(e) => { e.stopPropagation(); onViewCard?.(paper) }}
            title="查看卡片"
          >
            <Eye size={14} />
          </button>
          <button
            className={styles.actionBtn}
            onClick={(e) => { e.stopPropagation(); onQA?.(paper) }}
            title="基于此论文QA"
          >
            <MessageSquare size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
