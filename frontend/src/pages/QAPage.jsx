import { useState, useRef, useEffect } from 'react'
import { Send, BookOpen, Lightbulb, FileText, ExternalLink, AlertTriangle } from 'lucide-react'
import useStore from '../stores/useStore'
import styles from './QAPage.module.css'

const DEMO_QA = [
  {
    role: 'user',
    content: '这些论文在研究方法上有什么共同的局限性？',
  },
  {
    role: 'assistant',
    content: `基于选定范围内的 5 篇论文，主要研究方法的共同局限性包括：

**1. 计算资源需求过高 [1][2]**
Transformer 架构的自注意力机制具有 O(n²) 的时间复杂度，随着序列长度增加，计算成本急剧上升。这限制了模型在长文本场景下的应用。

**2. 训练数据偏差 [3][4]**
大规模预训练数据不可避免地包含社会偏见和错误信息，模型可能学习并放大这些偏差，影响输出的公平性和可靠性。

**3. 可解释性不足 [2][5]**
深度神经网络的"黑箱"特性使得模型决策过程难以理解和解释，这在高风险应用场景（如医疗、法律）中是一个严重问题。

**4. 样本效率低 [1][3]**
当前模型需要海量数据进行训练，而人类通常只需少量示例即可学习新任务。提高样本效率是一个重要的研究方向。

---

**范围声明**：以上分析仅基于选定的 5 篇论文，不包含项目库中其他论文的结论。

**不确定性说明**：局限性 1 和 2 在论文中有明确讨论；局限性 3 和 4 部分基于推断，建议查阅原文确认。`,
    sources: [
      { paper: 'Attention Is All You Need', quote: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...', page: 1 },
      { paper: 'BERT: Pre-training of Deep Bidirectional Transformers', quote: 'We introduce a new language representation model called BERT...', page: 1 },
      { paper: 'Language Models are Few-Shot Learners', quote: 'Here we show that scaling up language models greatly improves task-agnostic, few-shot performance...', page: 1 },
      { paper: 'Training Language Models to Follow Instructions', quote: 'Making language models bigger does not inherently make them better at following a user\'s intent...', page: 2 },
      { paper: 'Constitutional AI', quote: 'We experiment with methods for training a harmless AI assistant through a process we call Constitutional AI...', page: 1 },
    ],
  },
]

export default function QAPage() {
  const qaMessages = useStore((s) => s.qaMessages)
  const addQAMessage = useStore((s) => s.addQAMessage)
  const qaLoading = useStore((s) => s.qaLoading)
  const scope = useStore((s) => s.scope)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState(DEMO_QA)
  const [showSources, setShowSources] = useState(true)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    const userMsg = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    // Simulate response
    setTimeout(() => {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: '正在基于当前范围分析...\n\n（此为演示模式，实际功能需连接后端API）',
        sources: [],
      }])
    }, 1000)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.pageTitle}>研究 QA</h2>
        <div className={styles.scopeInfo}>
          <span className={styles.scopeLabel}>当前范围:</span>
          <span className={styles.scopeValue}>{scope.label}</span>
          <button className="btn btn--ghost btn--sm">修改范围</button>
        </div>
      </div>

      <div className={styles.main}>
        {/* Chat Area */}
        <div className={styles.chatArea}>
          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className="empty-state">
                <BookOpen size={48} />
                <h3>开始研究对话</h3>
                <p>基于当前范围提问，系统将引用论文和证据回答</p>
                <div className={styles.suggestions}>
                  <button className={styles.suggestionBtn} onClick={() => setInput('这些论文的共同研究主题是什么？')}>
                    这些论文的共同研究主题是什么？
                  </button>
                  <button className={styles.suggestionBtn} onClick={() => setInput('主要研究方法有哪些？各自优缺点？')}>
                    主要研究方法有哪些？各自优缺点？
                  </button>
                  <button className={styles.suggestionBtn} onClick={() => setInput('基于当前范围，有哪些可能的创新点？')}>
                    基于当前范围，有哪些可能的创新点？
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                <div className={styles.messageContent}>
                  {msg.role === 'assistant' && (
                    <div className={styles.scopeBadge}>
                      <AlertTriangle size={12} />
                      范围: {scope.label}
                    </div>
                  )}
                  <div className={styles.messageText}>
                    {msg.content.split('\n').map((line, j) => {
                      // Bold
                      const parts = line.split(/(\*\*[^*]+\*\*)/g)
                      return (
                        <p key={j}>
                          {parts.map((part, k) => {
                            if (part.startsWith('**') && part.endsWith('**')) {
                              return <strong key={k}>{part.slice(2, -2)}</strong>
                            }
                            // Citation markers [1][2]
                            const withCitations = part.replace(/\[(\d+)\]/g, (_, n) => `⟨${n}⟩`)
                            return <span key={k}>{withCitations}</span>
                          })}
                        </p>
                      )
                    })}
                  </div>

                  {msg.role === 'assistant' && (
                    <div className={styles.messageActions}>
                      <button className="btn btn--ghost btn--sm">
                        <FileText size={13} /> 加入综述素材
                      </button>
                      <button className="btn btn--ghost btn--sm">
                        <Lightbulb size={13} /> 加入创新点素材
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className={styles.inputArea}>
            <textarea
              className={styles.input}
              placeholder="输入研究问题... (Ctrl+Enter 发送)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className={styles.sendBtn}
              onClick={handleSend}
              disabled={!input.trim() || qaLoading}
            >
              <Send size={18} />
            </button>
          </div>
        </div>

        {/* Sources Panel */}
        <div className={`${styles.sourcesPanel} ${showSources ? '' : styles.collapsed}`}>
          <div className={styles.sourcesHeader}>
            <h3 className={styles.sourcesTitle}>证据来源</h3>
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => setShowSources(!showSources)}
            >
              {showSources ? '收起' : '展开'}
            </button>
          </div>

          {showSources && (
            <div className={styles.sourcesContent}>
              {/* Supporting Papers */}
              <div className={styles.section}>
                <h4 className={styles.sectionTitle}>支撑论文</h4>
                {messages
                  .filter((m) => m.role === 'assistant' && m.sources)
                  .flatMap((m) => m.sources || [])
                  .map((s, i) => (
                    <div key={i} className={styles.sourceCard}>
                      <span className={styles.sourceNum}>{i + 1}</span>
                      <div className={styles.sourceInfo}>
                        <p className={styles.sourceTitle}>{s.paper}</p>
                        <p className={styles.sourceQuote}>"{s.quote}"</p>
                        <span className={styles.sourcePage}>p.{s.page}</span>
                      </div>
                      <button className={styles.sourceLink}>
                        <ExternalLink size={12} />
                      </button>
                    </div>
                  ))}
              </div>

              {/* Evidence Records */}
              <div className={styles.section}>
                <h4 className={styles.sectionTitle}>证据记录</h4>
                <div className={styles.evidenceCard}>
                  <span className="badge badge--purple">方法比较</span>
                  <p className={styles.evidenceText}>Transformer vs RNN: 并行计算优势但二次复杂度</p>
                </div>
                <div className={styles.evidenceCard}>
                  <span className="badge badge--red">局限</span>
                  <p className={styles.evidenceText}>所有论文均未充分讨论长序列处理的计算瓶颈</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
