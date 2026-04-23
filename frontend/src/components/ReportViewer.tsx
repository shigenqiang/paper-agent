import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download, Copy, Check } from 'lucide-react'
import { useState } from 'react'

export default function ReportViewer({ content }: { content: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      {/* toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-sm font-semibold">研究报告</h2>
        <div className="flex items-center gap-2">
          <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500">
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
          <button onClick={handleDownload} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500">
            <Download size={16} />
          </button>
        </div>
      </div>
      {/* content */}
      <div className="p-6 prose-report max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </section>
  )
}
