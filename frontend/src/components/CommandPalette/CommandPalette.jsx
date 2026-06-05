import { useState, useEffect, useRef } from 'react'
import { Search, BookOpen, Network, MessageSquare, FileText, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import useStore from '../../stores/useStore'
import { api } from '../../api/client'
import styles from './CommandPalette.module.css'

const COMMANDS = [
  { id: 'library', label: '论文库', icon: BookOpen, path: '/library', type: 'page' },
  { id: 'graph', label: '知识图谱', icon: Network, path: '/graph', type: 'page' },
  { id: 'qa', label: '研究 QA', icon: MessageSquare, path: '/qa', type: 'page' },
  { id: 'reports', label: '成果报告', icon: FileText, path: '/reports', type: 'page' },
  { id: 'upload', label: '上传 PDF', icon: BookOpen, action: 'upload', type: 'action' },
  { id: 'build-kg', label: '构建知识图谱', icon: Network, action: 'buildKg', type: 'action' },
  { id: 'gen-review', label: '生成文献综述', icon: FileText, action: 'genReview', type: 'action' },
  { id: 'gen-innovation', label: '生成创新点报告', icon: FileText, action: 'genInnovation', type: 'action' },
]

export default function CommandPalette() {
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const closeCommandPalette = useStore((s) => s.closeCommandPalette)

  const filtered = COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') closeCommandPalette()
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1))
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIdx((i) => Math.max(i - 1, 0))
      }
      if (e.key === 'Enter' && filtered[selectedIdx]) {
        execute(filtered[selectedIdx])
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [filtered, selectedIdx])

  const currentProject = useStore((s) => s.currentProject)
  const scope = useStore((s) => s.scope)

  const execute = (cmd) => {
    if (cmd.path) {
      navigate(cmd.path)
    } else if (cmd.action && currentProject) {
      const pid = currentProject.project_id
      switch (cmd.action) {
        case 'upload':
          navigate('/library')
          break
        case 'buildKg':
          api.buildGraph(pid).catch(() => {})
          break
        case 'genReview':
          api.generateLiteratureReview(pid, scope || { type: 'all_project' }).catch(() => {})
          navigate('/reports')
          break
        case 'genInnovation':
          api.generateInnovationReport(pid, scope || { type: 'all_project' }).catch(() => {})
          navigate('/reports')
          break
      }
    }
    closeCommandPalette()
  }

  return (
    <div className={styles.overlay} onClick={closeCommandPalette}>
      <div className={styles.palette} onClick={(e) => e.stopPropagation()}>
        <div className={styles.inputRow}>
          <Search size={18} className={styles.searchIcon} />
          <input
            ref={inputRef}
            className={styles.input}
            placeholder="搜索命令..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIdx(0) }}
          />
        </div>

        <div className={styles.results}>
          {filtered.map((cmd, i) => {
            const Icon = cmd.icon
            return (
              <button
                key={cmd.id}
                className={`${styles.result} ${i === selectedIdx ? styles.selected : ''}`}
                onClick={() => execute(cmd)}
                onMouseEnter={() => setSelectedIdx(i)}
              >
                <Icon size={16} className={styles.resultIcon} />
                <span className={styles.resultLabel}>{cmd.label}</span>
                <span className={styles.resultType}>{cmd.type === 'page' ? '页面' : '操作'}</span>
                <ArrowRight size={14} className={styles.arrow} />
              </button>
            )
          })}
          {filtered.length === 0 && (
            <div className={styles.empty}>无匹配命令</div>
          )}
        </div>
      </div>
    </div>
  )
}
