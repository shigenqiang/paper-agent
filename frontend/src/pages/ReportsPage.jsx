import { useState } from 'react'
import { FileText, Lightbulb, Download, Clock, BookOpen, ChevronRight, Star } from 'lucide-react'
import useStore from '../stores/useStore'
import styles from './ReportsPage.module.css'

const DEMO_REPORTS = [
  {
    report_id: 'r1',
    type: 'literature_review',
    title: '文献综述: 大语言模型与自主学习',
    created_at: '2026-06-01 14:30',
    paper_count: 23,
    evidence_count: 45,
    version: 2,
    content: `# 大语言模型与自主学习：文献综述

## 1. 研究背景

近年来，大语言模型（LLM）在自然语言处理领域取得了突破性进展。从Transformer架构的提出到GPT系列模型的发布，LLM展现出了强大的语言理解和生成能力。然而，如何让这些模型具备自主学习和持续改进的能力，仍然是一个开放性问题。

## 2. 主题划分

本综述将相关研究划分为以下主题：

### 2.1 预训练与基础架构
- Transformer架构 [1]
- 自注意力机制 [1][2]
- 位置编码方法 [1]

### 2.2 指令微调与对齐
- RLHF方法 [4][5]
- Constitutional AI [5]
- Self-Instruct [6]

### 2.3 检索增强生成
- RAG架构 [8][9]
- 知识检索与融合 [9]

## 3. 代表性文献和研究脉络

Vaswani等人(2017)提出的Transformer架构[1]奠定了现代LLM的基础。该架构通过自注意力机制实现了高效的并行计算，在机器翻译任务上取得了当时的最优结果。

Devlin等人(2019)的BERT[2]引入了双向预训练策略，显著提升了多项NLP任务的性能。这一工作证明了大规模预训练的重要性。

## 4. 主要研究方法

| 方法 | 代表论文 | 优势 | 局限 |
|------|---------|------|------|
| 自注意力 | [1] | 并行计算、长距离依赖 | O(n²)复杂度 |
| 预训练+微调 | [2][3] | 任务无关、迁移性强 | 需要大量数据 |
| RLHF | [4][5] | 人类偏好对齐 | 标注成本高 |

## 5. 主要研究结论

1. 规模定律（Scaling Laws）表明模型性能与参数量、数据量、计算量呈幂律关系[11]
2. 涌现能力（Emergent Abilities）在模型规模超过阈值后突然出现[3]
3. 指令微调能显著提升模型的可用性[4][6]

## 6. 现有研究不足

- 计算资源需求过高，限制了研究的可重复性
- 训练数据偏差导致模型输出存在公平性问题
- 模型可解释性不足，难以理解决策过程
- 样本效率低，需要海量数据

## 7. 未来研究趋势

- 高效训练方法（如LoRA、QLoRA）
- 多模态融合（文本+图像+音频）
- 自主学习与持续学习
- 安全对齐与价值对齐

## 8. 参考文献

[1] Vaswani et al. (2017). Attention Is All You Need. NeurIPS.
[2] Devlin et al. (2019). BERT: Pre-training of Deep Bidirectional Transformers. NAACL.
[3] Brown et al. (2020). Language Models are Few-Shot Learners. NeurIPS.
[4] Ouyang et al. (2022). Training Language Models to Follow Instructions. NeurIPS.
[5] Bai et al. (2022). Constitutional AI. arXiv.
[6] Wang et al. (2023). Self-Instruct. ACL.
[7] Touvron et al. (2023). LLaMA. arXiv.
[8] Lewis et al. (2020). Retrieval-Augmented Generation. NeurIPS.
[9] Borgeaud et al. (2022). Improving Language Models by Retrieving. ICML.
[10] Christiano et al. (2017). Deep RL from Human Feedback. NeurIPS.
[11] Kaplan et al. (2020). Scaling Laws for Neural Language Models. arXiv.
[12] Wei et al. (2022). Chain-of-Thought Prompting. NeurIPS.
[13] Yao et al. (2023). Tree of Thoughts. NeurIPS.
[14] Yao et al. (2023). ReAct. ICLR.
[15] Schick et al. (2023). Toolformer. NeurIPS.`,
  },
  {
    report_id: 'r2',
    type: 'innovation_report',
    title: '创新点报告: 大语言模型研究机会',
    created_at: '2026-06-01 15:00',
    paper_count: 23,
    evidence_count: 32,
    version: 1,
    innovations: [
      {
        name: '基于强化学习的自适应反馈策略',
        description: '将强化学习引入LLM的反馈循环，使模型能够根据用户交互自动调整输出策略，而非依赖固定的RLHF奖励模型。',
        novelty: 8, evidence: 6, feasibility: 9, risk: 4, fit: 8,
        supportingPapers: 3, limitingPapers: 1,
      },
      {
        name: '多模态知识图谱增强的RAG',
        description: '将文本、图像、表格等多模态信息统一编码到知识图谱中，在检索时同时考虑结构化关系和语义相似度。',
        novelty: 7, evidence: 5, feasibility: 7, risk: 5, fit: 7,
        supportingPapers: 4, limitingPapers: 2,
      },
      {
        name: '轻量级持续学习框架',
        description: '设计一种参数高效的持续学习方法，使LLM能够在不遗忘旧知识的前提下学习新领域知识。',
        novelty: 9, evidence: 4, feasibility: 6, risk: 6, fit: 8,
        supportingPapers: 2, limitingPapers: 3,
      },
    ],
  },
]

export default function ReportsPage() {
  const reports = useStore((s) => s.reports)
  const setReports = useStore((s) => s.setReports)
  const scope = useStore((s) => s.scope)
  const [selectedReport, setSelectedReport] = useState(null)
  const [activeTab, setActiveTab] = useState('review')

  useState(() => {
    if (reports.length === 0) setReports(DEMO_REPORTS)
  })

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
          <button className="btn btn--primary">
            <FileText size={15} /> 生成文献综述
          </button>
          <button className="btn btn--secondary">
            <Lightbulb size={15} /> 生成创新点报告
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
                  <button className="btn btn--secondary btn--sm">
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
