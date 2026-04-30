/**
 * Connected Papers风格的知识图谱页面
 *
 * 功能特性：
 * 1. 力导向图谱可视化
 * 2. 节点大小基于引用数/重要性
 * 3. 社区聚类颜色
 * 4. 悬停预览、点击详情
 * 5. 缩放、平移、拖拽
 * 6. 年份范围筛选
 * 7. 搜索功能
 * 8. Prior/Derivative论文分类
 */
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Card, Input, Tag, Button, Space, Typography, Row, Col,
  Slider, Switch, Spin, Tooltip, Select, Badge, Divider,
  List, Avatar, Typography as AntTypography, Empty, message,
  AutoComplete, Tabs, Dropdown, Table, Modal, Form, Upload
} from 'antd'
import {
  SearchOutlined, ZoomInOutlined, ZoomOutOutlined,
  AimOutlined, ReloadOutlined, NodeIndexOutlined,
  FilterOutlined, InfoCircleOutlined, ArrowLeftOutlined,
  ArrowRightOutlined, ExpandOutlined, CompressOutlined,
  ClusterOutlined, GlobalOutlined, ThunderboltOutlined,
  BuildOutlined, StarOutlined, CalendarOutlined, TeamOutlined,
  DownOutlined, DatabaseOutlined,
  FileTextOutlined, CheckCircleOutlined, DeleteOutlined,
  PlusCircleOutlined, UploadOutlined, FilePdfOutlined,
  PlusOutlined, DragOutlined
} from '@ant-design/icons'
import { literatureAPI } from '../services/api'
import { useLiteratureStore } from '../store/literatureStore'
import { useKGStore } from '../store/kgStore'
import { useGraphData } from '../hooks/useGraphData'
import { useGraphInteraction, COMMUNITY_COLORS, TYPE_COLORS, YEAR_COLORS, getYearColor } from '../hooks/useGraphInteraction'

const { Text, Title, Paragraph } = AntTypography
const { Option } = Select
const { TabPane } = Tabs

const KnowledgeGraphPage = () => {
  // 使用自定义 hooks
  const {
    graphLoading,
    graphData,
    communityData,
    loadGraphFromLiterature,
    handleBuildFromLiterature,
    handleBuildGraph,
    handleGraphQuery,
    detectCommunities,
  } = useGraphData()

  const {
    containerRef,
    zoomLevel,
    selectedNode,
    setSelectedNode,
    hoveredNode,
    priorPapers,
    derivativePapers,
    initGraph,
    handleZoom,
    handleFitView,
    calculatePaperConnections,
  } = useGraphInteraction()

  // 视图控制（持久化）
  const {
    viewMode, setViewMode,
    showFilters, setShowFilters,
    sortBy, setSortBy,
    queryText, setQueryText,
    queryResult, setQueryResult,
    showQueryPanel, setShowQueryPanel,
  } = useKGStore()

  // 搜索
  const [searchText, setSearchText] = useState('')

  // GraphRAG问答（不持久化）
  const [queryLoading, setQueryLoading] = useState(false)

  // 使用文献库数据
  const { literature, addLiterature, deleteLiterature, updateLiterature } = useLiteratureStore()

  // 文献库管理状态
  const [literatureSearchText, setLiteratureSearchText] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [form] = Form.useForm()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [showLiteraturePanel, setShowLiteraturePanel] = useState(true)

  // 文献库过滤
  const filteredLiterature = useMemo(() => {
    if (!literatureSearchText.trim()) return literature
    const lower = literatureSearchText.toLowerCase()
    return literature.filter(l =>
      (l.title || '').toLowerCase().includes(lower) ||
      (l.authors || '').toLowerCase().includes(lower) ||
      (l.journal || '').toLowerCase().includes(lower)
    )
  }, [literature, literatureSearchText])

  const literatureColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text) => <Text ellipsis className="text-xs">{text}</Text>
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      width: 120,
      ellipsis: true,
      render: (text) => <Text className="text-xs">{text}</Text>
    },
    {
      title: '年份',
      dataIndex: 'year',
      key: 'year',
      width: 60,
      render: (text) => <Text className="text-xs">{text}</Text>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => {
        const statusMap = {
          cited: { color: 'green', text: '已引用' },
          pending: { color: 'blue', text: '待处理' },
          reading: { color: 'orange', text: '阅读中' },
          completed: { color: 'default', text: '已完成' },
        }
        const cfg = statusMap[status] || statusMap.pending
        return <Tag color={cfg.color} className="text-xs">{cfg.text}</Tag>
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => handleBuildFromLiterature(record.id)}>图谱</Button>
          <Button type="link" size="small" onClick={() => handleCiteLiterature(record.id)}>引用</Button>
          <Button type="link" size="small" danger onClick={() => handleDeleteLiterature(record.id)}>删除</Button>
        </Space>
      )
    }
  ]

  const handleCiteLiterature = (id) => {
    updateLiterature(id, { status: 'cited' })
    message.success('已标记为已引用')
  }

  const handleDeleteLiterature = (id) => {
    deleteLiterature(id)
    message.success('已删除')
  }

  const handleAddLiterature = (values) => {
    const newItem = {
      id: Date.now(),
      title: values.title,
      authors: values.authors,
      year: values.year || '',
      journal: values.journal || '',
      url: '',
      abstract: '',
      status: 'pending',
    }
    addLiterature(newItem)
    setIsAddModalOpen(false)
    form.resetFields()
    message.success('文献已添加')
  }

  const handleUpload = async (file) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await literatureAPI.uploadFile(formData)
      if (result.success) {
        message.success('文件上传成功')
        setIsUploadModalOpen(false)
      }
    } catch (error) {
      message.error('上传失败')
    } finally {
      setUploading(false)
    }
  }

  const beforeUpload = (file) => {
    const isPdf = file.type === 'application/pdf'
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    if (!isPdf && !isDocx) {
      message.error('仅支持 PDF 和 Word 文件')
      return false
    }
    const isLt50M = file.size / 1024 / 1024 < 50
    if (!isLt50M) {
      message.error('文件大小不能超过 50MB')
      return false
    }
    handleUpload(file)
    return false
  }

  const handleSearch = async (query) => {
    const q = query || searchQuery
    if (!q.trim()) return
    setSearchLoading(true)
    try {
      const result = await literatureAPI.search(q, { max_results: 10 })
      if (result.data) {
        const papers = result.data.map(item => ({
          paper_id: item.paper_id || item.id || Date.now().toString(),
          title: item.title || '',
          authors: Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || ''),
          year: item.year || '',
          abstract: item.abstract || '',
          url: item.url || '',
          venue: item.venue || '',
          citations: item.citations || 0,
          sources: item.sources || [],
        }))
        setSearchResults(papers)
      }
    } catch (error) {
      message.error('搜索失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleAddToLibrary = async (record) => {
    if (literature.some(l => l.id === record.paper_id)) {
      message.info('该文献已在库中')
      return
    }
    addLiterature({
      id: record.paper_id || Date.now(),
      title: record.title || '',
      authors: record.authors || '',
      year: record.year || '',
      journal: record.venue || '',
      url: record.url || '',
      abstract: record.abstract || '',
      citations: record.citations || 0,
      status: 'pending',
    })
    message.success('已添加到文献库')
  }

  // 初始化
  useEffect(() => {
    if (literature.length > 0 && graphData.nodes.length === 0) {
      loadGraphFromLiterature()
    }
    return () => {
      // cleanup handled by useGraphInteraction
    }
  }, [])

  // 文献库变化时重新加载
  useEffect(() => {
    if (literature.length > 0 && graphData.nodes.length === 0) {
      loadGraphFromLiterature()
    }
  }, [literature])

  // 图谱数据变化时初始化 G6
  useEffect(() => {
    if (graphData.nodes.length > 0) {
      setTimeout(() => initGraph(graphData, viewMode, graphData), 100)
    }
  }, [graphData])

  // 视图模式变化时更新
  useEffect(() => {
    if (graphData.nodes.length > 0) {
      setTimeout(() => initGraph(graphData, viewMode, graphData), 50)
    }
  }, [viewMode, communityData])

  const onGraphQuery = () => {
    handleGraphQuery(queryText, setQueryResult, setQueryLoading)
  }

  return (
    <div className="h-full flex flex-col bg-gray-100">
      {/* 顶部标题栏 */}
      <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
        <Space size="large">
          <Title level={4} className="m-0 flex items-center gap-2">
            <NodeIndexOutlined className="text-purple-500" />
            知识图谱
            <Badge count={graphData.stats?.totalNodes || 0} showZero color="#722ed1" />
          </Title>
        </Space>
        <Space size="middle">
          {/* 视图切换 */}
          <Select
            value={viewMode}
            onChange={setViewMode}
            style={{ width: 100 }}
            size="small"
          >
            <Option value="community"><ClusterOutlined /> 社区</Option>
            <Option value="type"><InfoCircleOutlined /> 类型</Option>
            <Option value="year"><GlobalOutlined /> 年份</Option>
            <Option value="degree"><ThunderboltOutlined /> 引用</Option>
          </Select>

          {/* 缩放控制 */}
          <Space size={4}>
            <Button icon={<ZoomOutOutlined />} onClick={() => handleZoom(-0.1)} size="small" />
            <Text className="text-xs w-10 text-center">{Math.round(zoomLevel * 100)}%</Text>
            <Button icon={<ZoomInOutlined />} onClick={() => handleZoom(0.1)} size="small" />
            <Button icon={<ExpandOutlined />} onClick={handleFitView} size="small" title="适应视图" />
          </Space>

          <Divider type="vertical" />

          <Button icon={<ReloadOutlined />} onClick={loadGraphFromLiterature} loading={graphLoading} size="small">
            刷新
          </Button>

          <Button
            icon={<SearchOutlined />}
            onClick={() => setShowQueryPanel(!showQueryPanel)}
            type={showQueryPanel ? 'primary' : 'default'}
            size="small"
          >
            GraphRAG
          </Button>
        </Space>
      </div>

      {/* GraphRAG问答面板 */}
      {showQueryPanel && (
        <div className="bg-blue-50 border-b px-4 py-2">
          <Space size="middle">
            <Text strong className="text-sm">GraphRAG问答:</Text>
            <Input
              placeholder="例如: Transformer和BERT有什么关系?"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onPressEnter={onGraphQuery}
              style={{ width: 300 }}
              size="small"
            />
            <Button type="primary" icon={<SearchOutlined />} onClick={onGraphQuery} loading={queryLoading} size="small">
              提问
            </Button>
            {queryResult && (
              <Tag color="green">已回答</Tag>
            )}
          </Space>
        </div>
      )}

      {/* 主内容区 - 三栏布局 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧面板 - Prior/Derivative Papers */}
        <div className="w-64 bg-white border-r flex flex-col">
          <Tabs defaultActiveKey="prior" size="small" className="flex-1">
            <TabPane
              tab={<span className="text-xs"><ArrowLeftOutlined /> Prior</span>}
              key="prior"
            >
              <div className="overflow-y-auto" style={{ height: 'calc(100vh - 280px)' }}>
                {priorPapers.length > 0 ? (
                  <List
                    dataSource={priorPapers}
                    renderItem={(paper) => (
                      <List.Item
                        className="cursor-pointer hover:bg-blue-50 px-3 py-2"
                        onClick={() => { setSelectedNode(paper); calculatePaperConnections(paper.id, graphData); }}
                      >
                        <List.Item.Meta
                          avatar={<Avatar size="small" style={{ backgroundColor: '#1890ff' }}>P</Avatar>}
                          title={<Text ellipsis className="text-xs">{paper.title}</Text>}
                          description={<Text type="secondary" className="text-xs">{paper.year} ★{paper.citations}</Text>}
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <div className="p-4 text-center text-gray-400"><Empty description="暂无" image={Empty.PRESENTED_IMAGE_SIMPLE} /></div>
                )}
              </div>
            </TabPane>
            <TabPane
              tab={<span className="text-xs">Derivative <ArrowRightOutlined /></span>}
              key="derivative"
            >
              <div className="overflow-y-auto" style={{ height: 'calc(100vh - 280px)' }}>
                {derivativePapers.length > 0 ? (
                  <List
                    dataSource={derivativePapers}
                    renderItem={(paper) => (
                      <List.Item
                        className="cursor-pointer hover:bg-green-50 px-3 py-2"
                        onClick={() => { setSelectedNode(paper); calculatePaperConnections(paper.id, graphData); }}
                      >
                        <List.Item.Meta
                          avatar={<Avatar size="small" style={{ backgroundColor: '#52c41a' }}>D</Avatar>}
                          title={<Text ellipsis className="text-xs">{paper.title}</Text>}
                          description={<Text type="secondary" className="text-xs">{paper.year} ★{paper.citations}</Text>}
                        />
                      </List.Item>
                    )}
                  />
                ) : (
                  <div className="p-4 text-center text-gray-400"><Empty description="暂无" image={Empty.PRESENTED_IMAGE_SIMPLE} /></div>
                )}
              </div>
            </TabPane>
          </Tabs>
        </div>

        {/* 中间图谱区域 */}
        <div className="flex-1 relative bg-gray-50" style={{ minHeight: 500 }}>
          {graphLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-white bg-opacity-80">
              <Spin tip="加载图谱..." />
            </div>
          )}

          <div
            ref={containerRef}
            id="knowledge-graph-container"
            className="w-full"
            style={{ background: 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)', height: '100%', minHeight: 580 }}
          />

          {/* 悬停预览 */}
          {hoveredNode && !selectedNode && (
            <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-3 max-w-xs z-10 border">
              <div className="flex items-start gap-2">
                <Tag color={TYPE_COLORS[hoveredNode.type] || 'default'}>
                  {hoveredNode.type}
                </Tag>
                {hoveredNode.year && <Tag>{hoveredNode.year}</Tag>}
              </div>
              <Title level={5} className="mt-2 mb-1">{hoveredNode.title || hoveredNode.label}</Title>
              {hoveredNode.authors && (
                <Text type="secondary" className="text-xs">{Array.isArray(hoveredNode.authors) ? hoveredNode.authors.join(', ') : hoveredNode.authors}</Text>
              )}
              {hoveredNode.citations && (
                <div className="mt-1">
                  <Text className="text-xs">引用数: <Text strong>{hoveredNode.citations.toLocaleString()}</Text></Text>
                </div>
              )}
            </div>
          )}

          {/* 图例 */}
          <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 z-10">
            <Text strong className="text-xs">图例</Text>
            <div className="mt-2 space-y-1">
              {viewMode === 'community' && (
                communityData.communities?.slice(0, 6).map((comm, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length] }}
                    />
                    <Text className="text-xs">社区 {idx + 1} ({comm.size})</Text>
                  </div>
                ))
              )}
              {viewMode === 'type' && (
                <>
                  {Object.entries(TYPE_COLORS).filter(([k]) => k !== 'unknown').map(([type, color]) => (
                    <div key={type} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                      <Text className="text-xs capitalize">{type}</Text>
                    </div>
                  ))}
                </>
              )}
              {viewMode === 'year' && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-3 rounded"
                      style={{
                        background: `linear-gradient(to right, #e6f7ff, #80bbff, #1a80ff, #005acc, #001860)`
                      }}
                    />
                  </div>
                  <div className="flex justify-between w-24">
                    <Text className="text-xs">2015</Text>
                    <Text className="text-xs">2026</Text>
                  </div>
                  <Text type="secondary" className="text-xs">颜色越深=年份越新</Text>
                </div>
              )}
              {viewMode === 'degree' && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#ff4d4f' }} />
                    <Text className="text-xs">高连接度</Text>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#faad14' }} />
                    <Text className="text-xs">中连接度</Text>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#52c41a' }} />
                    <Text className="text-xs">低连接度</Text>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 颜色图例 */}
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-3 z-10">
            <div className="mb-2">
              <Text type="secondary" className="text-xs">节点大小 = 引用数</Text>
            </div>
            <Space direction="vertical" size={4}>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-gradient-to-br from-purple-500 to-purple-700" style={{ width: 16, height: 16 }}></div>
                <Text className="text-xs">高连接度</Text>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gradient-to-br from-blue-400 to-blue-600" style={{ width: 12, height: 12 }}></div>
                <Text className="text-xs">中连接度</Text>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-gradient-to-br from-gray-300 to-gray-500" style={{ width: 8, height: 8 }}></div>
                <Text className="text-xs">低连接度</Text>
              </div>
            </Space>
            {communityData.stats?.total_communities > 0 && (
              <div className="mt-2 pt-2 border-t">
                <Text type="secondary" className="text-xs">社区检测</Text>
                <div className="text-sm font-medium text-green-600">
                  {communityData.stats.total_communities} 个社区
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 右侧面板 - 论文详情 (Connected Papers风格) */}
        <div className="w-80 bg-white border-l overflow-y-auto">
          {selectedNode ? (
            <div className="flex flex-col h-full">
              {/* 论文详情头部 */}
              <div className="p-4 border-b bg-gradient-to-br from-gray-50 to-white">
                <div className="flex items-center gap-2 mb-3">
                  <Avatar
                    size="large"
                    style={{
                      backgroundColor: selectedNode.isTarget ? '#722ed1' : TYPE_COLORS[selectedNode.type] || '#1890ff',
                      border: selectedNode.isTarget ? '3px solid #000' : 'none'
                    }}
                  >
                    {selectedNode.type === 'paper' ? 'P' : selectedNode.type?.[0]?.toUpperCase() || 'N'}
                  </Avatar>
                  <div>
                    {selectedNode.isTarget && (
                      <Tag color="purple" className="mb-1">目标论文</Tag>
                    )}
                    <Tag color={TYPE_COLORS[selectedNode.type] || 'default'}>
                      {selectedNode.type}
                    </Tag>
                  </div>
                </div>

                <Title level={5} className="mt-0 mb-2">{selectedNode.title || selectedNode.label}</Title>

                {selectedNode.authors && (
                  <Paragraph className="text-sm text-gray-600 mb-2 flex items-center gap-1">
                    <TeamOutlined />
                    {typeof selectedNode.authors === 'string' ? selectedNode.authors : (Array.isArray(selectedNode.authors) ? selectedNode.authors.join(', ') : '')}
                  </Paragraph>
                )}

                <div className="flex flex-wrap gap-2 mt-3">
                  {selectedNode.year && (
                    <Tag icon={<CalendarOutlined />} color="blue">
                      {selectedNode.year}
                    </Tag>
                  )}
                  {selectedNode.citations && (
                    <Tag icon={<StarOutlined />} color="gold">
                      ★ {selectedNode.citations.toLocaleString()} citations
                    </Tag>
                  )}
                </div>
              </div>

              {/* 连接关系 */}
              <div className="p-3 border-b">
                <Text strong className="text-sm flex items-center gap-1">
                  <ClusterOutlined /> 连接关系 ({graphData.edges?.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length || 0})
                </Text>
                <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                  {graphData.edges
                    ?.filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                    .map((edge, idx) => {
                      const otherId = edge.source === selectedNode.id ? edge.target : edge.source
                      const otherNode = graphData.nodes.find(n => n.id === otherId)
                      const isSource = edge.source === selectedNode.id
                      return (
                        <div
                          key={idx}
                          className="flex items-center gap-2 text-xs p-2 bg-gray-50 rounded hover:bg-gray-100 cursor-pointer"
                          onClick={() => {
                            if (otherNode) {
                              setSelectedNode(otherNode)
                              calculatePaperConnections(otherNode.id, graphData)
                            }
                          }}
                        >
                          <Tag size="small" color={isSource ? 'blue' : 'green'}>
                            {isSource ? '→' : '←'} {edge.relation}
                          </Tag>
                          <Text ellipsis className="flex-1">{otherNode?.title || otherId}</Text>
                        </div>
                      )
                    })}
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="p-3 mt-auto border-t bg-gray-50">
                <Space direction="vertical" className="w-full">
                  <Button block type="primary" icon={<SearchOutlined />} onClick={() => handleBuildGraph(selectedNode.title)}>
                    以此论文构建图谱
                  </Button>
                </Space>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 p-4">
              <NodeIndexOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <Text type="secondary">点击图谱中的节点</Text>
              <Text type="secondary">查看论文详情</Text>
            </div>
          )}
        </div>
      </div>

      {/* 底部状态栏 */}
      <div className="bg-gray-100 border-t px-4 py-1.5 flex items-center justify-between text-xs text-gray-500">
        <Space size="large">
          <span><DragOutlined /> 拖拽</span>
          <span><SearchOutlined /> 缩放</span>
          <span><ThunderboltOutlined /> 节点=引用数</span>
        </Space>
        <Space>
          {selectedNode && (
            <Text type="secondary">
              当前: <Text strong>{String(selectedNode.title || selectedNode.label).slice(0, 30)}...</Text>
            </Text>
          )}
          <Tag color="blue">{viewMode === 'community' ? '社区' : viewMode === 'type' ? '类型' : viewMode === 'year' ? '年份' : '引用'}</Tag>
        </Space>
      </div>

      {/* 文献库面板 - 底部可折叠 */}
      <div className="bg-white border-t">
        <div
          className="flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50"
          onClick={() => setShowLiteraturePanel(!showLiteraturePanel)}
        >
          <Space>
            <FileTextOutlined />
            <Text strong>文献库</Text>
            <Tag color="green">{filteredLiterature.length}篇</Tag>
            <Button size="small" icon={<UploadOutlined />} onClick={(e) => { e.stopPropagation(); setIsUploadModalOpen(true); }}>上传</Button>
            <Button size="small" icon={<PlusOutlined />} onClick={(e) => { e.stopPropagation(); setIsAddModalOpen(true); }}>添加</Button>
          </Space>
          <Button type="text" size="small" icon={showLiteraturePanel ? <DownOutlined /> : <ArrowLeftOutlined />} />
        </div>

        {showLiteraturePanel && (
          <div className="px-4 pb-3">
            <Input
              placeholder="筛选文献..."
              prefix={<SearchOutlined />}
              value={literatureSearchText}
              onChange={(e) => setLiteratureSearchText(e.target.value)}
              size="small"
              style={{ width: 200, marginBottom: 8 }}
            />
            <Table
              dataSource={filteredLiterature}
              columns={literatureColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 4 }}
              scroll={{ y: 150 }}
            />
          </div>
        )}
      </div>

      {/* 添加文献弹窗 */}
      <Modal
        title="添加文献"
        open={isAddModalOpen}
        onCancel={() => setIsAddModalOpen(false)}
        footer={null}
        width={500}
      >
        <Form form={form} onFinish={handleAddLiterature} layout="vertical">
          <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入论文标题' }]}>
            <Input placeholder="请输入论文标题" />
          </Form.Item>
          <Form.Item label="作者" name="authors" rules={[{ required: true, message: '请输入作者' }]}>
            <Input placeholder="请输入作者，多个作者用逗号分隔" />
          </Form.Item>
          <Space className="w-full" size="large">
            <Form.Item label="年份" name="year" className="flex-1">
              <Input type="number" placeholder="年份" />
            </Form.Item>
            <Form.Item label="期刊" name="journal" className="flex-1">
              <Input placeholder="期刊名称" />
            </Form.Item>
          </Space>
          <Form.Item className="!mb-0">
            <Space className="w-full justify-end">
              <Button onClick={() => setIsAddModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">添加</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 文件上传弹窗 */}
      <Modal
        title="上传文献文件"
        open={isUploadModalOpen}
        onCancel={() => setIsUploadModalOpen(false)}
        footer={null}
        width={500}
      >
        <div className="py-4">
          <div className="text-center">
            {uploading ? (
              <Spin tip="正在上传并提取元数据...">
                <div style={{ minHeight: 200 }} />
              </Spin>
            ) : (
              <>
                <Upload.Dragger
                  accept=".pdf,.doc,.docx"
                  showUploadList={false}
                  beforeUpload={beforeUpload}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <FilePdfOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                  <p className="ant-upload-hint">
                    支持 PDF、Word 文件<br />
                    系统将自动识别文献元数据
                  </p>
                </Upload.Dragger>
              </>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default KnowledgeGraphPage
