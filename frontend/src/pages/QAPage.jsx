import { useState, useRef, useEffect } from 'react'
import { Send, BookOpen, Lightbulb, FileText, ExternalLink, AlertTriangle } from 'lucide-react'
import useStore from '../stores/useStore'
import { api } from '../api/client'
import styles from './QAPage.module.css'

export default function QAPage() {
  const scope = useStore((s) => s.scope)
  const currentProject = useStore((s) => s.currentProject)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [showSources, setShowSources] = useState(true)
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || !currentProject) return
    const userMsg = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.askQuestion(currentProject.project_id, {
        question: input,
        scope: scope || { type: 'all_project' },
      })
      const data = res.data || res
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.answer || data.content || JSON.stringify(data),
        sources: data.sources || [],
      }])
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `请求失败: ${err.message}`,
        sources: [],
      }])
    } finally {
      setLoading(false)
    }
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
              disabled={!input.trim() || loading || !currentProject}
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
