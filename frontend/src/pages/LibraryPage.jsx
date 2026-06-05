import { useState, useEffect, useRef } from 'react'
import { Upload, Search, Filter, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import PaperCard from '../components/PaperCard/PaperCard'
import useStore from '../stores/useStore'
import { api } from '../api/client'
import styles from './LibraryPage.module.css'

export default function LibraryPage() {
  const papers = useStore((s) => s.papers)
  const setPapers = useStore((s) => s.setPapers)
  const openDrawer = useStore((s) => s.openDrawer)
  const currentProject = useStore((s) => s.currentProject)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!currentProject) return
    setLoading(true)
    setError(null)
    api.listPapers(currentProject.project_id)
      .then((res) => {
        const data = res.data || res
        setPapers(Array.isArray(data) ? data : [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [currentProject])

  const handleUpload = async (e) => {
    const files = e.target.files
    if (!files.length || !currentProject) return
    const formData = new FormData()
    for (const f of files) formData.append('files', f)
    try {
      await api.uploadPapersBatch(currentProject.project_id, formData)
      const res = await api.listPapers(currentProject.project_id)
      setPapers(res.data || res || [])
    } catch (err) {
      setError(err.message)
    }
    e.target.value = ''
  }

  const handleExclude = async (paperId) => {
    try {
      await api.excludePaper(paperId)
      const res = await api.listPapers(currentProject.project_id)
      setPapers(res.data || res || [])
      openDrawer(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const filtered = papers.filter((p) => {
    const matchSearch = !searchQuery ||
      (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.authors?.some((a) => a.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchStatus = filterStatus === 'all' || p.status === filterStatus
    return matchSearch && matchStatus
  })

  const stats = {
    total: papers.length,
    parsed: papers.filter((p) => p.status === 'parsed' || p.status === 'card_ready').length,
    excluded: papers.filter((p) => p.status === 'excluded').length,
    pending: papers.filter((p) => p.status === 'imported' || p.status === 'uploaded').length,
  }

  const handleViewCard = (paper) => {
    openDrawer(
      <div>
        <h3 style={{ fontFamily: 'var(--font-display)', marginBottom: '16px', fontSize: '1.1rem' }}>
          {paper.title}
        </h3>
        <div style={{ marginBottom: '12px' }}>
          <span className="badge badge--accent">{paper.venue || paper.source}</span>
          <span className="badge badge--blue" style={{ marginLeft: '6px' }}>{paper.year}</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
          {paper.authors?.join(', ')}
        </p>
        <div style={{ background: 'var(--bg-elevated)', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
          <h4 style={{ color: 'var(--accent)', fontSize: '0.82rem', marginBottom: '8px' }}>论文卡片</h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            状态: {paper.status}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn--primary btn--sm">查看PDF</button>
          <button className="btn btn--secondary btn--sm" onClick={() => handleExclude(paper.paper_id)}>
            排除论文
          </button>
        </div>
      </div>
    )
  }

  if (!currentProject) {
    return (
      <div className="empty-state">
        <Search size={48} />
        <h3>请先选择或创建项目</h3>
        <p>在顶部导航栏选择一个项目</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2 className={styles.pageTitle}>论文库</h2>
          <span className={styles.count}>{filtered.length} 篇</span>
        </div>
        <div className={styles.headerActions}>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={handleUpload}
          />
          <button className="btn btn--primary" onClick={() => fileInputRef.current?.click()}>
            <Upload size={15} /> 上传 PDF
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.searchBox}>
          <Search size={15} />
          <input
            className={styles.searchInput}
            placeholder="搜索论文标题、作者..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className={styles.filters}>
          <button
            className={`${styles.filterBtn} ${filterStatus === 'all' ? styles.filterActive : ''}`}
            onClick={() => setFilterStatus('all')}
          >
            全部 <span className={styles.filterCount}>{stats.total}</span>
          </button>
          <button
            className={`${styles.filterBtn} ${filterStatus === 'parsed' ? styles.filterActive : ''}`}
            onClick={() => setFilterStatus('parsed')}
          >
            <CheckCircle size={13} /> 已解析 <span className={styles.filterCount}>{stats.parsed}</span>
          </button>
          <button
            className={`${styles.filterBtn} ${filterStatus === 'excluded' ? styles.filterActive : ''}`}
            onClick={() => setFilterStatus('excluded')}
          >
            <XCircle size={13} /> 已排除 <span className={styles.filterCount}>{stats.excluded}</span>
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className={styles.statsBar}>
        <div className={styles.stat}>
          <CheckCircle size={14} className={styles.statIconGreen} />
          <span>已纳入 {stats.parsed}</span>
        </div>
        <div className={styles.stat}>
          <XCircle size={14} className={styles.statIconRed} />
          <span>已排除 {stats.excluded}</span>
        </div>
        <div className={styles.stat}>
          <AlertCircle size={14} className={styles.statIconAmber} />
          <span>待处理 {stats.pending}</span>
        </div>
      </div>

      {loading && <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '32px' }}>加载中...</p>}
      {error && <p style={{ color: 'var(--red)', textAlign: 'center', padding: '16px' }}>错误: {error}</p>}

      {/* Paper Grid */}
      <div className={styles.grid}>
        {filtered.map((paper, i) => (
          <div key={paper.paper_id} style={{ animationDelay: `${i * 40}ms` }}>
            <PaperCard
              paper={paper}
              onViewCard={handleViewCard}
              onQA={(p) => window.location.href = '/qa'}
            />
          </div>
        ))}
      </div>

      {filtered.length === 0 && !loading && (
        <div className="empty-state">
          <Search size={48} />
          <h3>未找到匹配的论文</h3>
          <p>尝试修改搜索条件或上传 PDF 文件</p>
        </div>
      )}
    </div>
  )
}
