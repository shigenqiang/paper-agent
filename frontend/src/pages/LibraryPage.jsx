import { useState, useEffect } from 'react'
import { Upload, Search, Filter, SortAsc, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import PaperCard from '../components/PaperCard/PaperCard'
import useStore from '../stores/useStore'
import styles from './LibraryPage.module.css'

// Demo data for MVP
const DEMO_PAPERS = [
  { paper_id: 'p1', title: 'Attention Is All You Need', authors: ['Vaswani, A.', 'Shazeer, N.', 'Parmar, N.'], year: 2017, venue: 'NeurIPS', status: 'parsed', topic: 'Transformer' },
  { paper_id: 'p2', title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding', authors: ['Devlin, J.', 'Chang, M.', 'Lee, K.'], year: 2019, venue: 'NAACL', status: 'parsed', topic: 'Pre-training' },
  { paper_id: 'p3', title: 'Language Models are Few-Shot Learners', authors: ['Brown, T.', 'Mann, B.', 'Ryder, N.'], year: 2020, venue: 'NeurIPS', status: 'parsed', topic: 'Few-shot' },
  { paper_id: 'p4', title: 'Training Language Models to Follow Instructions with Human Feedback', authors: ['Ouyang, L.', 'Wu, J.', 'Jiang, X.'], year: 2022, venue: 'NeurIPS', status: 'parsed', topic: 'RLHF' },
  { paper_id: 'p5', title: 'Constitutional AI: Harmlessness from AI Feedback', authors: ['Bai, Y.', 'Kadavath, S.', 'Kundu, S.'], year: 2022, venue: 'arXiv', status: 'parsed', topic: 'RLHF' },
  { paper_id: 'p6', title: 'Self-Instruct: Aligning Language Models with Self-Generated Instructions', authors: ['Wang, Y.', 'Kordi, Y.', 'Mishra, S.'], year: 2023, venue: 'ACL', status: 'parsed', topic: 'Instruction Tuning' },
  { paper_id: 'p7', title: 'LLaMA: Open and Efficient Foundation Language Models', authors: ['Touvron, H.', 'Lavril, T.', 'Izacard, G.'], year: 2023, venue: 'arXiv', status: 'parsed', topic: 'Open LLM' },
  { paper_id: 'p8', title: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks', authors: ['Lewis, P.', 'Perez, E.', 'Piktus, A.'], year: 2020, venue: 'NeurIPS', status: 'parsed', topic: 'RAG' },
  { paper_id: 'p9', title: 'Improving Language Models by Retrieving from Trillions of Tokens', authors: ['Borgeaud, S.', 'Mensch, A.', 'Hoffmann, J.'], year: 2022, venue: 'ICML', status: 'parsed', topic: 'RAG' },
  { paper_id: 'p10', title: 'Deep Reinforcement Learning from Human Feedback', authors: ['Christiano, P.', 'Leike, J.', 'Brown, T.'], year: 2017, venue: 'NeurIPS', status: 'parsed', topic: 'RLHF' },
  { paper_id: 'p11', title: 'Scaling Laws for Neural Language Models', authors: ['Kaplan, J.', 'McCandlish, S.', 'Henighan, T.'], year: 2020, venue: 'arXiv', status: 'parsed', topic: 'Scaling' },
  { paper_id: 'p12', title: 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models', authors: ['Wei, J.', 'Wang, X.', 'Schuurmans, D.'], year: 2022, venue: 'NeurIPS', status: 'parsed', topic: 'Prompting' },
  { paper_id: 'p13', title: 'Tree of Thoughts: Deliberate Problem Solving with Large Language Models', authors: ['Yao, S.', 'Yu, D.', 'Zhao, J.'], year: 2023, venue: 'NeurIPS', status: 'parsed', topic: 'Prompting' },
  { paper_id: 'p14', title: 'ReAct: Synergizing Reasoning and Acting in Language Models', authors: ['Yao, S.', 'Zhao, J.', 'Yu, D.'], year: 2023, venue: 'ICLR', status: 'parsed', topic: 'Agents' },
  { paper_id: 'p15', title: 'Toolformer: Language Models Can Teach Themselves to Use Tools', authors: ['Schick, T.', 'Dwivedi-Yu, J.', 'Dessì, R.'], year: 2023, venue: 'NeurIPS', status: 'parsed', topic: 'Agents' },
]

export default function LibraryPage() {
  const papers = useStore((s) => s.papers)
  const setPapers = useStore((s) => s.setPapers)
  const openDrawer = useStore((s) => s.openDrawer)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [viewMode, setViewMode] = useState('grid')

  useEffect(() => {
    if (papers.length === 0) setPapers(DEMO_PAPERS)
  }, [])

  const filtered = papers.filter((p) => {
    const matchSearch = !searchQuery ||
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.authors?.some((a) => a.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchStatus = filterStatus === 'all' || p.status === filterStatus
    return matchSearch && matchStatus
  })

  const stats = {
    total: papers.length,
    parsed: papers.filter((p) => p.status === 'parsed').length,
    excluded: papers.filter((p) => p.status === 'excluded').length,
    pending: papers.filter((p) => p.status === 'uploaded').length,
  }

  const handleViewCard = (paper) => {
    openDrawer(
      <div>
        <h3 style={{ fontFamily: 'var(--font-display)', marginBottom: '16px', fontSize: '1.1rem' }}>
          {paper.title}
        </h3>
        <div style={{ marginBottom: '12px' }}>
          <span className="badge badge--accent">{paper.venue}</span>
          <span className="badge badge--blue" style={{ marginLeft: '6px' }}>{paper.year}</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
          {paper.authors?.join(', ')}
        </p>
        <div style={{ background: 'var(--bg-elevated)', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
          <h4 style={{ color: 'var(--accent)', fontSize: '0.82rem', marginBottom: '8px' }}>论文卡片</h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            主题: {paper.topic || '—'}<br/>
            状态: {paper.status === 'parsed' ? '已解析，可进行QA和报告生成' : '待解析'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn--primary btn--sm">查看PDF</button>
          <button className="btn btn--secondary btn--sm">排除论文</button>
        </div>
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
          <button className="btn btn--primary">
            <Upload size={15} /> 上传 PDF
          </button>
          <button className="btn btn--secondary">导入 BibTeX</button>
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

      {filtered.length === 0 && (
        <div className="empty-state">
          <Search size={48} />
          <h3>未找到匹配的论文</h3>
          <p>尝试修改搜索条件或筛选器</p>
        </div>
      )}
    </div>
  )
}
