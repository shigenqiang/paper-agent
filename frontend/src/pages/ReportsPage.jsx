import { useState, useEffect } from 'react'
import { FileText, Lightbulb, Download, Clock, BookOpen, ChevronRight, Star } from 'lucide-react'
import useStore from '../stores/useStore'
import { api } from '../api/client'
import styles from './ReportsPage.module.css'

export default function ReportsPage() {
  const reports = useStore((s) => s.reports)
  const setReports = useStore((s) => s.setReports)
  const scope = useStore((s) => s.scope)
  const currentProject = useStore((s) => s.currentProject)
  const [selectedReport, setSelectedReport] = useState(null)
  const [activeTab, setActiveTab] = useState('review')
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (!currentProject) return
    api.listReports(currentProject.project_id)
      .then((res) => {
        const data = res.data || res
        setReports(Array.isArray(data) ? data : [])
      })
      .catch(() => {})
  }, [currentProject])

  const handleGenerate = async (type) => {
    if (!currentProject) return
    setGenerating(true)
    try {
      const scopePayload = scope || { type: 'all_project' }
      if (type === 'review') {
        await api.generateLiteratureReview(currentProject.project_id, scopePayload)
      } else {
        await api.generateInnovationReport(currentProject.project_id, scopePayload)
      }
      const res = await api.listReports(currentProject.project_id)
      setReports(res.data || res || [])
    } catch (err) {
      console.error('Generate failed:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleExport = async (reportId) => {
    try {
      const res = await api.exportReportMarkdown(reportId)
      const content = res.content || res.data?.content || ''
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${reportId}.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  const reviewReports = reports.filter((r) => r.type === 'literature_review')
  const innovationReports = reports.filter((r) => r.type === 'innovation_report')
  const currentList = activeTab === 'review' ? reviewReports : innovationReports

  const displayReport = selectedReport || currentList[0]

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.pageTitle}>成果报告</h2>
        <div className={styles.headerActions}>
          <button
            className="btn btn--primary"
            disabled={generating || !currentProject}
            onClick={() => handleGenerate('review')}
          >
            <FileText size={15} /> {generating ? '生成中...' : '生成文献综述'}
          </button>
          <button
            className="btn btn--secondary"
            disabled={generating || !currentProject}
            onClick={() => handleGenerate('innovation')}
          >
            <Lightbulb size={15} /> {generating ? '生成中...' : '生成创新点报告'}
          </button>
        </div>
      </div>

      <div className={styles.main}>
        {/* Report List */}
        <div className={styles.listPanel}>
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${activeTab === 'review' ? styles.tabActive : ''}`}
              onClick={() => { setActiveTab('review'); setSelectedReport(null) }}
            >
              <FileText size={14} /> 文献综述
            </button>
            <button
              className={`${styles.tab} ${activeTab === 'innovation' ? styles.tabActive : ''}`}
              onClick={() => { setActiveTab('innovation'); setSelectedReport(null) }}
            >
              <Lightbulb size={14} /> 创新点
            </button>
          </div>

          <div className={styles.list}>
            {currentList.map((report) => (
              <button
                key={report.report_id}
                className={`${styles.listItem} ${displayReport?.report_id === report.report_id ? styles.listItemActive : ''}`}
                onClick={() => setSelectedReport(report)}
              >
                <div className={styles.listItemIcon}>
                  {report.type === 'literature_review' ? <FileText size={16} /> : <Lightbulb size={16} />}
                </div>
                <div className={styles.listItemInfo}>
                  <p className={styles.listItemTitle}>{report.title}</p>
                  <div className={styles.listItemMeta}>
                    <span><Clock size={11} /> {report.created_at}</span>
                    <span><BookOpen size={11} /> {report.paper_count}篇</span>
                  </div>
                </div>
                <ChevronRight size={14} className={styles.listItemArrow} />
              </button>
            ))}

            {currentList.length === 0 && (
              <div className={styles.emptyList}>
                <p>暂无{activeTab === 'review' ? '文献综述' : '创新点报告'}</p>
                <p className={styles.emptyHint}>点击上方按钮生成</p>
              </div>
            )}
          </div>
        </div>

        {/* Report Preview */}
        <div className={styles.previewPanel}>
          {displayReport ? (
            <>
              <div className={styles.previewHeader}>
                <div>
                  <h3 className={styles.previewTitle}>{displayReport.title}</h3>
                  <div className={styles.previewMeta}>
                    <span className="badge badge--accent">v{displayReport.version}</span>
                    <span className="badge badge--blue">{displayReport.paper_count}篇论文</span>
                    <span className="badge badge--purple">{displayReport.evidence_count}条证据</span>
                    <span className={styles.previewTime}>{displayReport.created_at}</span>
                  </div>
                </div>
                <div className={styles.previewActions}>
                  <button className="btn btn--secondary btn--sm" onClick={() => handleExport(displayReport.report_id)}>
                    <Download size={14} /> 导出Markdown
                  </button>
                </div>
              </div>

              <div className={styles.previewContent}>
                {displayReport.type === 'literature_review' && displayReport.content && (
                  <div className={styles.markdown}>
                    {displayReport.content.split('\n').map((line, i) => {
                      if (line.startsWith('# ')) return <h1 key={i} className={styles.mdH1}>{line.slice(2)}</h1>
                      if (line.startsWith('## ')) return <h2 key={i} className={styles.mdH2}>{line.slice(3)}</h2>
                      if (line.startsWith('### ')) return <h3 key={i} className={styles.mdH3}>{line.slice(4)}</h3>
                      if (line.startsWith('| ')) return <p key={i} className={styles.mdTable}>{line}</p>
                      if (line.startsWith('- ')) return <li key={i} className={styles.mdLi}>{line.slice(2)}</li>
                      if (line.match(/^\[\d+\]/)) return <p key={i} className={styles.mdRef}>{line}</p>
                      if (line.trim() === '') return <br key={i} />
                      return <p key={i} className={styles.mdP}>{line}</p>
                    })}
                  </div>
                )}

                {displayReport.type === 'innovation_report' && displayReport.innovations && (
                  <div className={styles.innovations}>
                    {displayReport.innovations.map((inn, i) => (
                      <div key={i} className={styles.innovationCard}>
                        <div className={styles.innovationHeader}>
                          <span className={styles.innovationNum}>#{i + 1}</span>
                          <h4 className={styles.innovationName}>{inn.name}</h4>
                        </div>
                        <p className={styles.innovationDesc}>{inn.description}</p>

                        <div className={styles.scores}>
                          <ScoreBar label="新颖性" value={inn.novelty} color="var(--accent)" />
                          <ScoreBar label="证据" value={inn.evidence} color="var(--blue)" />
                          <ScoreBar label="可行性" value={inn.feasibility} color="var(--green)" />
                          <ScoreBar label="风险" value={inn.risk} color="var(--red)" inverted />
                          <ScoreBar label="匹配度" value={inn.fit} color="var(--purple)" />
                        </div>

                        <div className={styles.innovationFooter}>
                          <span className={styles.innovationStat}>
                            <BookOpen size={12} /> 支撑: {inn.supportingPapers}篇
                          </span>
                          <span className={styles.innovationStat}>
                            限制: {inn.limitingPapers}篇
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <FileText size={48} />
              <h3>选择一份报告查看</h3>
              <p>或点击上方按钮生成新报告</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ScoreBar({ label, value, color, inverted }) {
  const displayValue = inverted ? 10 - value : value
  return (
    <div className={styles.scoreRow}>
      <span className={styles.scoreLabel}>{label}</span>
      <div className={styles.scoreBarBg}>
        <div
          className={styles.scoreBarFill}
          style={{ width: `${displayValue * 10}%`, background: color }}
        />
      </div>
      <span className={styles.scoreValue} style={{ color }}>{value}/10</span>
    </div>
  )
}
