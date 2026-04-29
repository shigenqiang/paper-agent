import React, { useState, useEffect, useMemo } from 'react'
import { Card, Tabs, Button, Space, Typography, List, Tag, Empty, Spin, message, Row, Col, Alert, Badge, Collapse, Tooltip } from 'antd'
import ReactMarkdown from 'react-markdown'
import {
  ReloadOutlined,
  FileTextOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  FilterOutlined,
  SettingOutlined,
  CopyOutlined,
  PlusCircleOutlined,
  TagOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { reportsAPI, settingsAPI } from '../services/api'
import { usePaperStore } from '../store/paperStore'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography
const { Panel } = Collapse

const REPORT_TYPES = {
  DAILY: 'daily',
  WEEKLY: 'weekly',
  MONTHLY: 'monthly'
}

const SOURCE_CONFIG = {
  arxiv: { color: '#e84a25', label: 'arXiv' },
  pubmed: { color: '#3e84c8', label: 'PubMed' },
  semantic_scholar: { color: '#5c7fdd', label: 'Semantic' },
  openalex: { color: '#ff6b35', label: 'OpenAlex' },
}

const MarkdownContent = ({ digest }) => {
  const content = useMemo(() => {
    if (!digest) return { text: '', references: [] }
    const lines = (digest.summary || digest.content || '').split('\n')
    const references = []
    const filtered = lines.filter(line => {
      const match = line.match(/^\[(\d+)\]:\s*(https?:\/\/[^\s]+)/)
      if (match) {
        references.push({ num: match[1], url: match[2] })
        return false
      }
      return true
    })
    return { text: filtered.join('\n'), references }
  }, [digest])

  return (
    <div className="flex-1 overflow-auto p-4">
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown>{content.text || '暂无内容'}</ReactMarkdown>
      </div>
    </div>
  )
}

const ReportsPage = () => {
  const navigate = useNavigate()
  const { literature, addLiterature, deleteLiterature } = usePaperStore()
  const [activeTab, setActiveTab] = useState(REPORT_TYPES.DAILY)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [selectedDigest, setSelectedDigest] = useState(null)
  const [digests, setDigests] = useState([])
  const [lastUpdate, setLastUpdate] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [stats, setStats] = useState({ totalPapers: 0, newToday: 0, sources: [] })

  const loadDigests = async () => {
    setLoading(true)
    try {
      let response
      if (activeTab === REPORT_TYPES.DAILY) response = await reportsAPI.getDailyReports()
      else if (activeTab === REPORT_TYPES.WEEKLY) response = await reportsAPI.getWeeklyReports()
      else response = await reportsAPI.getMonthlyReports()
      if (response.success) setDigests(response.data || [])
      else setDigests([])
      setLastUpdate(new Date())
    } catch (error) {
      setDigests([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { setSelectedDigest(null); loadDigests() }, [activeTab])
  useEffect(() => { loadKeywords() }, [])

  const loadKeywords = async () => {
    try {
      const response = await settingsAPI.getSettings()
      if (response.success && response.data) setKeywords(response.data.keywords || [])
    } catch (e) {}
  }

  useEffect(() => {
    const totalPapers = digests.reduce((sum, d) => sum + (d.papers?.length || 0), 0)
    const today = new Date().toDateString()
    const newToday = digests.filter(d => new Date(d.created_at).toDateString() === today).length
    const sourceSet = new Set()
    digests.forEach(d => d.sources?.forEach(s => sourceSet.add(s)))
    setStats({ totalPapers, newToday, sources: Array.from(sourceSet) })
  }, [digests])

  const handleGenerateDigest = async () => {
    setGenerating(true)
    try {
      const response = await reportsAPI.createReport({ type: activeTab, topic: '' })
      if (response.success) {
        message.success('资讯生成中，请稍候...')
        pollDigestStatus(response.data.id)
      }
    } catch (error) {
      message.error('生成失败')
      setGenerating(false)
    }
  }

  const pollDigestStatus = async (digestId) => {
    const checkStatus = async () => {
      try {
        const response = await reportsAPI.getReport(digestId)
        if (response.success && response.data) {
          const digest = response.data
          if (digest.status === 'ready') {
            setGenerating(false)
            loadDigests()
            message.success('资讯生成完成！')
            return
          } else if (digest.status === 'error') {
            setGenerating(false)
            message.error('资讯生成失败')
            return
          }
        }
      } catch (e) {}
      setTimeout(checkStatus, 3000)
    }
    setTimeout(checkStatus, 2000)
  }

  const handleViewDigest = (digest) => setSelectedDigest(digest)
  const handleDeleteDigest = async (e, digestId) => {
    e.stopPropagation()
    try {
      const response = await reportsAPI.deleteReport(digestId)
      if (response.success) {
        message.success('已删除')
        if (selectedDigest?.id === digestId) setSelectedDigest(null)
        loadDigests()
      }
    } catch (error) {
      message.error('删除失败')
    }
  }
  const handleCopyReport = () => {
    if (!selectedDigest) return
    navigator.clipboard.writeText(selectedDigest.summary || selectedDigest.content || '').then(() => message.success('报告已复制')).catch(() => message.error('复制失败'))
  }
  const handleDownloadReport = () => {
    if (!selectedDigest) return
    const blob = new Blob([selectedDigest.summary || selectedDigest.content || ''], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selectedDigest.title || '学术资讯报告'}.md`
    link.click()
    URL.revokeObjectURL(url)
    message.success('报告已下载')
  }
  const handleAddPaper = (paper) => {
    if (literature.some(l => l.id === paper.paper_id)) { message.info('该文献已在库中'); return }
    addLiterature({ id: paper.paper_id || Date.now(), title: paper.title || '', authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : (paper.authors || ''), year: paper.year || '', journal: paper.venue || paper.journal || '', url: paper.url || '', abstract: paper.abstract || '', source: Array.isArray(paper.sources) ? paper.sources[0] : (paper.sources || ''), citations: paper.citations || 0, status: 'pending' })
    message.success('已添加到文献库')
  }
  const handleRemovePaper = (paperId) => {
    const item = literature.find(l => l.id === paperId)
    if (item) { deleteLiterature(item.id); message.success('已从文献库删除') }
  }
  const getSourceColor = (source) => ({ 'arxiv': 'blue', 'pubmed': 'green', 'semantic_scholar': 'purple', 'openalex': 'orange' }[source] || 'default')
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return `${date.getMonth() + 1}-${date.getDate()}`
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 顶部标题栏 */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <Title level={4} className="!m-0 flex items-center gap-2">
          <FileTextOutlined className="text-blue-500" />
          学术资讯快报
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadDigests} loading={loading} size="small">刷新</Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerateDigest} loading={generating} size="small">
            生成{activeTab === 'daily' ? '今日' : activeTab === 'weekly' ? '本周' : '本月'}资讯
          </Button>
        </Space>
      </div>

      {/* 关键词和数据来源 */}
      <div className="bg-white border-b px-4 py-3">
        <Row gutter={16}>
          <Col span={14}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                <FilterOutlined className="text-white text-lg" />
              </div>
              <div className="flex-1">
                <div className="text-xs text-gray-500 mb-1">监测关键词</div>
                <div className="flex flex-wrap gap-1">
                  {keywords.length > 0 ? keywords.map(k => (
                    <Tag key={k} color="blue" className="cursor-pointer hover:bg-blue-200 transition-colors">
                      {k} ×
                    </Tag>
                  )) : <Text type="secondary">暂无</Text>}
                </div>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0">
                <TagOutlined className="text-white text-lg" />
              </div>
              <div className="flex-1">
                <div className="text-xs text-gray-500 mb-1">数据来源</div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(SOURCE_CONFIG).map(([key, config]) => (
                    <Tag key={key} color={config.color} className="!text-xs">{config.label}</Tag>
                  ))}
                </div>
              </div>
            </div>
          </Col>
          <Col span={4} className="flex items-center justify-center">
            <Button type="primary" icon={<SettingOutlined />} onClick={() => navigate('/settings')} size="middle">
              设置关键词
            </Button>
          </Col>
        </Row>
      </div>

      {/* 统计卡片 */}
      <div className="bg-white border-b px-4 py-3">
        <Row gutter={16}>
          <Col span={6}>
            <div className="flex items-center gap-3 p-2 rounded-lg bg-blue-50 hover:bg-blue-100 transition-colors">
              <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center">
                <FileTextOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="text-xs text-gray-500">论文总数</div>
                <div className="text-xl font-bold text-blue-600">{stats.totalPapers}</div>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div className="flex items-center gap-3 p-2 rounded-lg bg-green-50 hover:bg-green-100 transition-colors">
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center">
                <PlusCircleOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="text-xs text-gray-500">今日新增</div>
                <div className="text-xl font-bold text-green-600">{stats.newToday}</div>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div className="flex items-center gap-3 p-2 rounded-lg bg-orange-50 hover:bg-orange-100 transition-colors">
              <div className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center">
                <CalendarOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="text-xs text-gray-500">当前期数</div>
                <div className="text-xl font-bold text-orange-600">{digests.length}</div>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div className="flex items-center gap-3 p-2 rounded-lg bg-purple-50 hover:bg-purple-100 transition-colors">
              <div className="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center">
                <TagOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="text-xs text-gray-500">数据来源</div>
                <div className="text-xl font-bold text-purple-600">{stats.sources.length} 个</div>
              </div>
            </div>
          </Col>
        </Row>
      </div>

      {/* 资讯类型切换 */}
      <div className="bg-white border-b px-4 py-2">
        <Space>
          <Button type={activeTab === REPORT_TYPES.DAILY ? 'primary' : 'default'} icon={<CalendarOutlined />} onClick={() => setActiveTab(REPORT_TYPES.DAILY)} size="small">每日资讯</Button>
          <Button type={activeTab === REPORT_TYPES.WEEKLY ? 'primary' : 'default'} icon={<CalendarOutlined />} onClick={() => setActiveTab(REPORT_TYPES.WEEKLY)} size="small">每周资讯</Button>
          <Button type={activeTab === REPORT_TYPES.MONTHLY ? 'primary' : 'default'} icon={<CalendarOutlined />} onClick={() => setActiveTab(REPORT_TYPES.MONTHLY)} size="small">每月资讯</Button>
        </Space>
      </div>

      {/* 生成中提示 */}
      {generating && <Alert message="资讯生成中..." description="正在从多个学术数据库搜索最新论文..." type="info" showIcon icon={<LoadingOutlined spin />} />}

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* 左侧资讯列表 */}
        <div className="w-64 bg-white border rounded-lg flex flex-col">
          <div className="px-3 py-2 border-b bg-gray-50">
            <Text strong>📋 资讯列表</Text>
          </div>
          <div className="flex-1 overflow-auto">
            {loading ? <div className="p-4 text-center"><Spin /></div> :
             digests.length === 0 ? <div className="p-4 text-center text-gray-400">暂无资讯</div> :
             <List
               size="small"
               dataSource={digests}
               renderItem={(item, index) => (
                 <List.Item
                   className={`cursor-pointer hover:bg-blue-50 px-3 py-2 ${selectedDigest?.id === item.id ? 'bg-blue-50' : ''}`}
                   onClick={() => handleViewDigest(item)}
                 >
                   <div className="w-full">
                     <div className="flex items-center justify-between">
                       <Text className="text-sm">{formatDate(item.created_at)} {item.title || item.topic || '报告'} {item.status === 'ready' ? '✅' : item.status === 'generating' ? '🔄' : ''}</Text>
                       <Button
                         type="text"
                         size="small"
                         danger
                         icon={<DeleteOutlined />}
                         onClick={(e) => handleDeleteDigest(e, item.id)}
                         className="flex-shrink-0"
                       />
                     </div>
                     <Text type="secondary" className="text-xs">{item.papers?.length || 0}篇</Text>
                   </div>
                 </List.Item>
               )}
             />
            }
          </div>
        </div>

        {/* 右侧报告详情 */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* 上部：每日学术咨询 */}
          <div className="h-[1000px] bg-white border rounded-lg flex flex-col overflow-hidden mb-3">
            <div className="px-4 py-2 border-b bg-gradient-to-r from-blue-50 to-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Text strong className="text-lg">
                  {selectedDigest?.title || '每日学术资讯'}
                </Text>
                {selectedDigest && (
                  <Tag color={selectedDigest.status === 'ready' ? 'green' : 'orange'}>
                    {selectedDigest.status === 'ready' ? '✅ 已完成' : '🔄 生成中'}
                  </Tag>
                )}
              </div>
              <Space>
                <Button icon={<FileTextOutlined />} onClick={handleDownloadReport} disabled={!selectedDigest || selectedDigest.status !== 'ready'}>下载</Button>
                <Button icon={<CopyOutlined />} onClick={handleCopyReport} disabled={!selectedDigest || selectedDigest.status !== 'ready'}>复制</Button>
              </Space>
            </div>

            {!selectedDigest ? (
              <div className="flex-1 flex items-center justify-center text-gray-400">
                <Empty description="请选择左侧资讯查看" />
              </div>
            ) : selectedDigest.status !== 'ready' ? (
              <div className="flex-1 flex items-center justify-center"><Spin tip="生成中..." /></div>
            ) : (
              <MarkdownContent digest={selectedDigest} />
            )}
          </div>

          {/* 下部：今日文献 */}
          <div className="flex-1 bg-white border rounded-lg flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b bg-gradient-to-r from-green-50 to-white">
              <Text strong className="text-base">📚 今日文献</Text>
              <Text type="secondary" className="ml-2 text-xs">{selectedDigest?.papers?.length || 0} 篇</Text>
            </div>
            <div className="flex-1 overflow-auto p-3">
              {selectedDigest?.papers?.length > 0 ? (
                <div className="space-y-2">
                  {selectedDigest.papers.map((paper, idx) => {
                    const inLib = literature.some(l => l.id === paper.paper_id || l.title === paper.title)
                    return (
                      <div key={idx} className="flex items-start gap-2 p-2 rounded hover:bg-gray-50 transition-colors">
                        <Tag color={inLib ? 'green' : 'blue'} className="flex-shrink-0 mt-0.5">
                          {inLib ? '已添加' : '未添加'}
                        </Tag>
                        <div className="flex-1 min-w-0">
                          <Text className="text-sm block truncate">{paper.title}</Text>
                          <Text type="secondary" className="text-xs">
                            {paper.authors?.slice?.(0, 2)?.join?.(', ') || paper.authors || ''} {paper.year ? `(${paper.year})` : ''}
                          </Text>
                        </div>
                        <Button
                          type="link"
                          size="small"
                          className="flex-shrink-0"
                          onClick={() => inLib ? handleRemovePaper(paper.paper_id) : handleAddPaper(paper)}
                        >
                          {inLib ? '移除' : '添加'}
                        </Button>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <Empty description="暂无文献" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReportsPage
