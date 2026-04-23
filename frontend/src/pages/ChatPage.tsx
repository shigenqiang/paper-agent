import { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, Loader2 } from 'lucide-react'
import { api } from '@/services/api'
import { useAppStore } from '@/stores/appStore'
import type { ChatMessage } from '@/types'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function ChatPage() {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const messages = useAppStore((s) => s.messages)
  const addMessage = useAppStore((s) => s.addMessage)
  const taskId = useAppStore((s) => s.taskId)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)
    setInput('')
    setSending(true)

    try {
      const reply = await api.chat(userMsg.content, taskId ?? undefined)
      addMessage(reply)
    } catch {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '抱歉，请求失败，请稍后重试。',
        timestamp: new Date().toISOString(),
      })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      {/* header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <MessageSquare size={18} /> 论文对话
        </h1>
        <p className="text-xs text-gray-400 mt-1">基于已有研究内容进行问答</p>
      </div>

      {/* messages */}
      <div className="flex-1 overflow-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">输入问题开始对话</div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={clsx(
              'flex',
              m.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={clsx(
                'max-w-[80%] px-4 py-3 rounded-2xl text-sm',
                m.role === 'user'
                  ? 'bg-brand-600 text-white rounded-br-md'
                  : 'bg-gray-100 dark:bg-gray-800 rounded-bl-md'
              )}
            >
              {m.role === 'assistant' ? (
                <div className="prose-report">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                </div>
              ) : (
                m.content
              )}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200/30 text-xs opacity-70">
                  引用: {m.sources.map((s) => s.title).join(', ')}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* input */}
      <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend() }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="提问关于研究内容的问题…"
            className="flex-1 px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-brand-500 focus:outline-none"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="px-4 py-2 rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </form>
      </div>
    </div>
  )
}
