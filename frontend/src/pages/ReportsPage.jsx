import React, { useState, useEffect } from 'react'
import { Card, Tabs, Button, Space, Typography, List, Tag, Empty, Spin, message, Divider, Statistic, Row, Col, Alert, Badge } from 'antd'
import {
  ReloadOutlined,
  FileTextOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  FilterOutlined,
  SettingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { reportsAPI, settingsAPI } from '../services/api'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography
const { TabPane } = Tabs

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

const ReportsPage = () => {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(REPORT_TYPES.DAILY)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [selectedDigest, setSelectedDigest] = useState(null)
  const [digests, setDigests] = useState([])
  const [lastUpdate, setLastUpdate] = useState(null)
  const [keywords, setKeywords] = useState([])
  const [stats, setStats] = useState({
    totalPapers: 0,
    newToday: 0,
    sources: []
  })

  const loadDigests = async () => {
    setLoading(true)
    try {
      let response
      if (activeTab === REPORT_TYPES.DAILY) {
        response = await reportsAPI.getDailyReports()
      } else if (activeTab === REPORT_TYPES.WEEKLY) {
        response = await reportsAPI.getWeeklyReports()
      } else {
        response = await reportsAPI.getMonthlyReports()
      }

      if (response.success) {
        setDigests(response.data || [])
        setLastUpdate(new Date())
      } else {
        setDigests([])
      }
    } catch (error) {
      console.error('加载资讯失败:', error)
      setDigests([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setSelectedDigest(null)
    loadDigests()
  }, [activeTab])

  useEffect(() => {
    loadKeywords()
  }, [])

  const loadKeywords = async () => {
    try {
      const response = await settingsAPI.getSettings()
      if (response.success && response.data) {
        setKeywords(response.data.keywords || [])
      }
    } catch (e) {
      console.error('加载关键词失败', e)
    }
  }

  useEffect(() => {
    const totalPapers = digests.reduce((sum, d) => sum + (d.papers?.length || 0), 0)
    const today = new Date().toDateString()
    const newToday = digests.filter(d => new Date(d.created_at).toDateString() === today).length

    const sourceSet = new Set()
    digests.forEach(d => {
      d.sources?.forEach(s => sourceSet.add(s))
    })

    setStats({
      totalPapers,
      newToday,
      sources: Array.from(sourceSet)
    })
  }, [digests])

  const handleGenerateDigest = async () => {
    setGenerating(true)
    try {
      const response = await reportsAPI.createReport({
        type: activeTab,
        topic: ''
      })

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
      } catch (e) {
        console.error('检查状态失败', e)
      }

      if (generating) {
        setTimeout(checkStatus, 3000)
      }
    }

    setTimeout(checkStatus, 2000)
  }

  const handleViewDigest = (digest) => {
    setSelectedDigest(digest)
  }

  const getSourceColor = (source) => {
    const colors = {
      'arxiv': 'blue',
      'pubmed': 'green',
      'semantic_scholar': 'purple',
      'openalex': 'orange'
    }
    return colors[source] || 'default'
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Title level={3} className="!mb-0">
          <Space>
            <FileTextOutlined />
            <span>学术资讯快报</span>
          </Space>
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadDigests} loading={loading}>
            刷新
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerateDigest} loading={generating}>
            生成{activeTab === 'daily' ? '今日' : activeTab === 'weekly' ? '本周' : '本月'}资讯
          </Button>
        </Space>
      </div>

      <Card size="small">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <Text type="secondary" className="mr-2">监测关键词:</Text>
            {keywords.length > 0 ? (
              keywords.map(keyword => (
                <Tag key={keyword} color="blue">{keyword}</Tag>
              ))
            ) : (
              <Text type="secondary">暂无设置</Text>
            )}
          </div>
          <Button
            type="link"
            size="small"
            icon={<SettingOutlined />}
            onClick={() => navigate('/settings')}
          >
            设置关键词
          </Button>
        </div>
      </Card>

      {generating && (
        <Alert
          message="资讯生成中..."
          description="系统正在从多个学术数据库搜索最新论文并生成摘要，请稍候..."
          type="info"
          showIcon
          icon={<LoadingOutlined spin />}
        />
      )}

      <Row gutter={16}>
        <Col span={6}>
          <Card size="small" className="!border-l-4 !border-l-blue-500">
            <Statistic
              title={<Text type="secondary" className="text-xs">论文总数</Text>}
              value={stats.totalPapers}
              prefix={<FileTextOutlined className="text-blue-500" />}
              valueStyle={{ fontSize: '24px', color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="!border-l-4 !border-l-green-500">
            <Statistic
              title={<Text type="secondary" className="text-xs">今日新增</Text>}
              value={stats.newToday}
              valueStyle={{ fontSize: '24px', color: '#52c41a' }}
              prefix={<CheckCircleOutlined className="text-green-500" />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="!border-l-4 !border-l-orange-500">
            <Statistic
              title={<Text type="secondary" className="text-xs">当前期数</Text>}
              value={digests.length}
              prefix={<CalendarOutlined className="text-orange-500" />}
              valueStyle={{ fontSize: '24px', color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="!border-l-4 !border-l-purple-500">
            <Statistic
              title={<Text type="secondary" className="text-xs">数据来源</Text>}
              value={stats.sources.length}
              suffix="个"
              valueStyle={{ fontSize: '24px', color: '#722ed1' }}
              prefix={<FilterOutlined className="text-purple-500" />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={(key) => { setActiveTab(key); setSelectedDigest(null); }}>
          <TabPane tab={<span><CalendarOutlined />每日资讯</span>} key={REPORT_TYPES.DAILY}>
            <ContentPanel
              digests={digests}
              selectedDigest={selectedDigest}
              loading={loading}
              onViewDigest={handleViewDigest}
              onGenerate={handleGenerateDigest}
              getSourceColor={getSourceColor}
              formatDate={formatDate}
              generating={generating}
            />
          </TabPane>

          <TabPane tab={<span><CalendarOutlined />每周资讯</span>} key={REPORT_TYPES.WEEKLY}>
            <ContentPanel
              digests={digests}
              selectedDigest={selectedDigest}
              loading={loading}
              onViewDigest={handleViewDigest}
              onGenerate={handleGenerateDigest}
              getSourceColor={getSourceColor}
              formatDate={formatDate}
              generating={generating}
            />
          </TabPane>

          <TabPane tab={<span><CalendarOutlined />每月资讯</span>} key={REPORT_TYPES.MONTHLY}>
            <ContentPanel
              digests={digests}
              selectedDigest={selectedDigest}
              loading={loading}
              onViewDigest={handleViewDigest}
              onGenerate={handleGenerateDigest}
              getSourceColor={getSourceColor}
              formatDate={formatDate}
              generating={generating}
            />
          </TabPane>
        </Tabs>
      </Card>

      {lastUpdate && (
        <div className="text-xs text-gray-400 text-center">
          最后更新: {formatDate(lastUpdate)}
        </div>
      )}
    </div>
  )
}

const ContentPanel = ({
  digests,
  selectedDigest,
  loading,
  onViewDigest,
  onGenerate,
  getSourceColor,
  formatDate,
  generating
}) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin tip="加载中..." size="large" />
      </div>
    )
  }

  if (digests.length === 0) {
    return (
      <Card className="text-center py-12 !rounded-lg">
        <div className="mb-4">
          <FileTextOutlined className="text-5xl text-gray-300" />
        </div>
        <Text type="secondary" className="text-base block mb-4">暂无资讯，点击下方按钮生成</Text>
        <Button type="primary" size="large" onClick={onGenerate} loading={generating} icon={<ThunderboltOutlined />}>
          生成资讯
        </Button>
      </Card>
    )
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-340px)] min-h-[400px]">
      {/* 左侧资讯列表 - 时间线样式 */}
      <Card className="w-80 flex-shrink-0 flex flex-col !rounded-lg" title={<Space><FileTextOutlined /><span>资讯列表</span></Space>} bodyStyle={{ padding: 0, flex: 1, overflow: 'auto' }}>
        <List
          size="small"
          dataSource={digests}
          renderItem={(item, index) => (
            <List.Item
              className={`cursor-pointer hover:bg-blue-50 px-4 py-3 transition-all ${selectedDigest?.id === item.id ? 'bg-blue-50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'}`}
              onClick={() => onViewDigest(item)}
            >
              <div className="w-full">
                <div className="flex items-center justify-between mb-1">
                  <Text strong className="text-sm">{item.title || `第${index + 1}期`}</Text>
                  {item.status === 'ready' ? (
                    <CheckCircleOutlined className="text-green-500" />
                  ) : item.status === 'generating' ? (
                    <LoadingOutlined className="text-orange-500" />
                  ) : null}
                </div>
                <div className="text-xs text-gray-400">{formatDate(item.created_at)}</div>
                <div className="flex items-center gap-2 mt-2">
                  <Tag className="!text-xs" size="small" color="blue">{item.papers?.length || 0} 篇</Tag>
                  {item.sources?.slice(0, 2).map(source => (
                    <Tag className="!text-xs" size="small" color={getSourceColor(source)} key={source}>
                      {SOURCE_CONFIG[source]?.label || source}
                    </Tag>
                  ))}
                </div>
              </div>
            </List.Item>
          )}
        />
      </Card>

      {/* 右侧资讯详情 */}
      <Card className="flex-1 flex flex-col !rounded-lg" title={
        <Space>
          {selectedDigest ? <FileTextOutlined /> : <ClockCircleOutlined />}
          <span>{selectedDigest ? selectedDigest.title : '请选择资讯'}</span>
        </Space>
      }>
        {!selectedDigest ? (
          <div className="flex-1 flex items-center justify-center">
            <Empty description="请从左侧选择一期资讯查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        ) : (
          <div className="flex flex-col h-full">
            {/* 详情头部 */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <Space split={<Divider type="vertical" />}>
                <Text type="secondary"><FileTextOutlined /> {selectedDigest.papers?.length || 0} 篇</Text>
                <Text type="secondary"><CalendarOutlined /> {formatDate(selectedDigest.created_at)}</Text>
              </Space>
              <Space>
                {selectedDigest.sources?.map(source => (
                  <Tag color={getSourceColor(source)} key={source}>{SOURCE_CONFIG[source]?.label || source}</Tag>
                ))}
              </Space>
            </div>

            {/* 论文列表 */}
            <div className="flex-1 overflow-auto py-2">
              <List
                size="small"
                dataSource={selectedDigest.papers || []}
                renderItem={(paper, idx) => (
                  <List.Item className={`!py-3 ${idx !== 0 ? '!border-t !border-gray-100' : ''}`}>
                    <div className="w-full">
                      <div className="flex items-start gap-3">
                        <Badge count={idx + 1} style={{ backgroundColor: '#1890ff' }} />
                        <div className="flex-1">
                          <Text strong className="text-sm block">{paper.title}</Text>
                          <Text type="secondary" className="text-xs block mt-1">
                            {paper.authors?.slice(0, 3).join(', ')}{paper.authors?.length > 3 && ' 等'} · {paper.year}
                          </Text>
                          {paper.abstract && (
                            <Text type="secondary" className="text-xs block mt-1 line-clamp-2">
                              {paper.abstract}
                            </Text>
                          )}
                        </div>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default ReportsPage
