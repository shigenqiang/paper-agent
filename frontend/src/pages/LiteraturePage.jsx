import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Input, Table, Tag, Button, Space, Typography, Modal, Form, Select, message, Tooltip, Row, Col, Empty, Upload, Spin, Tabs, Switch, Alert, Drawer, Popover, Badge, Divider } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, CheckCircleOutlined, FileTextOutlined, UploadOutlined, FilePdfOutlined, PlusCircleOutlined, DatabaseOutlined } from '@ant-design/icons'
import { useLiteratureStore } from '../store/literatureStore'
import { literatureAPI, settingsAPI, knowledgeGraphAPI } from '../services/api'
import { useLocation } from 'react-router-dom'
import { SOURCE_CONFIG_LIST, SOURCE_CONFIG } from '../constants/source'
import * as G6 from '@antv/g6'

const { Title, Text } = Typography

const LiteraturePage = () => {
  const location = useLocation()
  const {
    literature, addLiterature, deleteLiterature, updateLiterature,
    // 搜索状态（持久化）
    searchResults, searchQuery, searchLoading, hasMore, currentPage, activeTab, graphVisible,
    setSearchResults, setSearchQuery, setSearchLoading, setHasMore, setCurrentPage, setActiveTab, setGraphVisible,
  } = useLiteratureStore()
  const [searchText, setSearchText] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [form] = Form.useForm()

  // 多源搜索状态（不持久化的状态）
  const [searchLoadingMore, setSearchLoadingMore] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [isSourceSettingsOpen, setIsSourceSettingsOpen] = useState(false)
  const [sources, setSources] = useState(['arxiv', 'pubmed', 'semantic_scholar', 'openalex'])
  const [expandedAuthors, setExpandedAuthors] = useState([])

  // 知识图谱状态
  const [graphLoading, setGraphLoading] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [selectedNode, setSelectedNode] = useState(null)
  const [communityMode, setCommunityMode] = useState(false)
  const [communityData, setCommunityData] = useState({ communities: [], stats: {} })
  const [communityLoading, setCommunityLoading] = useState(false)
  const [centralityData, setCentralityData] = useState({ top_hub_nodes: [], centrality: [] })
  const [pathData, setPathData] = useState({ paths: [], path_count: 0 })
  const [neighborData, setNeighborData] = useState({ neighbors: [], total_neighbors: 0 })
  const [analysisMode, setAnalysisMode] = useState('none') // none, centrality, paths, neighbors
  const graphRef = useRef(null)
  const graphContainerRef = useRef(null)

  const PAGE_SIZE = 10

  // 加载数据源设置
  useEffect(() => {
    loadSourceSettings()
  }, [])

  const loadSourceSettings = async () => {
    try {
      const response = await settingsAPI.getSettings()
      if (response.success && response.data?.sources) {
        setSources(response.data.sources)
      }
    } catch (e) {
      console.error('加载数据源设置失败:', e)
    }
  }

  const toggleSource = (sourceKey) => {
    if (sources.includes(sourceKey)) {
      if (sources.length > 1) {
        setSources(sources.filter(s => s !== sourceKey))
      }
    } else {
      setSources([...sources, sourceKey])
    }
  }

  const saveSourceSettings = async () => {
    try {
      await settingsAPI.updateSettings({ sources })
      message.success('数据来源设置已保存')
      setIsSourceSettingsOpen(false)
    } catch (e) {
      message.error('保存失败')
    }
  }

  // 从 header 搜索跳转过来时自动触发搜索
  useEffect(() => {
    if (location.state?.searchQuery) {
      setSearchQuery(location.state.searchQuery)
      handleSearch(location.state.searchQuery)
      setActiveTab('search')
    }
  }, [location.state])

  // 多源学术搜索
  const handleSearch = async (query) => {
    const q = query || searchQuery
    if (!q.trim()) {
      message.warning('请输入搜索关键词')
      return
    }
    setSearchLoading(true)
    setSearchResults([])
    setSelectedRowKeys([])
    setCurrentPage(1)
    setHasMore(true)
    try {
      const result = await literatureAPI.search(q, { max_results: PAGE_SIZE })
      if (result.success && result.data) {
        const papers = result.data.map(item => ({
          id: item.paper_id || item.id || Date.now() + Math.random(),
          title: item.title || '',
          authors: Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || ''),
          year: item.year || '',
          journal: item.venue || item.journal || '',
          abstract: item.abstract || '',
          url: item.url || '',
          source: item.source || 'unknown',
          citations: item.citations || 0,
          doi: item.doi || '',
        }))
        setSearchResults(papers)
        setHasMore(result.data.length >= PAGE_SIZE)
        setActiveTab('search')
      } else {
        message.warning('未找到相关文献')
        setSearchResults([])
        setHasMore(false)
      }
    } catch (e) {
      message.error('搜索失败: ' + (e.message || '网络错误'))
      setSearchResults([])
      setHasMore(false)
    } finally {
      setSearchLoading(false)
    }
  }

  // 加载更多搜索结果
  const handleLoadMore = async () => {
    if (searchLoadingMore || !hasMore) return
    setSearchLoadingMore(true)
    try {
      const nextPage = currentPage + 1
      const result = await literatureAPI.search(searchQuery, {
        max_results: PAGE_SIZE,
        page: nextPage,
      })
      if (result.success && result.data) {
        const papers = result.data.map(item => ({
          id: item.paper_id || item.id || Date.now() + Math.random(),
          title: item.title || '',
          authors: Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || ''),
          year: item.year || '',
          journal: item.venue || item.journal || '',
          abstract: item.abstract || '',
          url: item.url || '',
          source: item.source || 'unknown',
          citations: item.citations || 0,
          doi: item.doi || '',
        }))
        setSearchResults(prev => [...prev, ...papers])
        setCurrentPage(nextPage)
        setHasMore(result.data.length >= PAGE_SIZE)
      } else {
        setHasMore(false)
      }
    } catch (e) {
      message.error('加载更多失败')
    } finally {
      setSearchLoadingMore(false)
    }
  }

  // 批量添加选中结果到文献库
  const handleBatchAddSelected = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要添加的文献')
      return
    }
    const selected = searchResults.filter(r => selectedRowKeys.includes(r.id))
    selected.forEach(item => {
      addLiterature({ ...item, status: 'pending' })
    })
    message.success(`已添加 ${selected.length} 篇文献到文献库`)
    setSelectedRowKeys([])
  }

  // 添加搜索结果到文献库
  const handleAddToLibrary = async (record) => {
    try {
      addLiterature({
        ...record,
        status: 'pending',
      })
      message.success('已添加到文献库')
    } catch (e) {
      message.error('添加失败')
    }
  }

  // 修复引用按钮
  const handleCiteLiterature = (id) => {
    updateLiterature(id, { status: 'cited' })
    message.success('文献已引用')
  }

  const handleDeleteLiterature = (id) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条文献吗？',
      okText: '删除',
      okType: 'danger',
      onOk() {
        deleteLiterature(id)
        message.success('文献已删除')
      }
    })
  }

  const handleAddLiterature = (values) => {
    const newItem = {
      ...values,
      id: Date.now(),
      citations: 0,
      status: 'pending',
    }
    addLiterature(newItem)
    message.success('文献添加成功')
    setIsAddModalOpen(false)
    form.resetFields()
  }

  // 上传文件处理
  const handleUpload = async (file) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await literatureAPI.uploadFile(formData)
      if (result.success && result.data) {
        addLiterature({
          ...result.data,
          id: result.data.id || Date.now(),
          status: 'pending',
        })
        message.success('文献上传成功！已自动提取元数据')
        setIsUploadModalOpen(false)
      } else {
        throw new Error(result.error || '上传失败')
      }
    } catch (error) {
      message.error('上传失败：' + (error.message || '未知错误'))
    } finally {
      setUploading(false)
    }
    return false
  }

  const beforeUpload = (file) => {
    const isPdf = file.type === 'application/pdf'
    const isDocx = file.name.endsWith('.docx') || file.name.endsWith('.doc')
    const isText = file.type.startsWith('text/')
    if (!isPdf && !isDocx && !isText) {
      message.error('只支持 PDF、Word 或文本文件！')
      return false
    }
    const isLt50M = file.size / 1024 / 1024 < 50
    if (!isLt50M) {
      message.error('文件大小不能超过 50MB！')
      return false
    }
    handleUpload(file)
    return false
  }

  const filteredLiterature = useMemo(() => {
    if (!searchText.trim()) return literature
    const lower = searchText.toLowerCase()
    return literature.filter(item =>
      item.title?.toLowerCase().includes(lower) ||
      item.authors?.toLowerCase().includes(lower) ||
      item.journal?.toLowerCase().includes(lower)
    )
  }, [literature, searchText])

  const totalCount = filteredLiterature.length
  const citedCount = filteredLiterature.filter(l => l.status === 'cited').length
  const pendingCount = filteredLiterature.filter(l => l.status === 'pending').length

  // 加载知识图谱
  const loadKnowledgeGraph = async () => {
    setGraphLoading(true)
    try {
      // 将文献数据传递给后端以构建图谱
      const response = await knowledgeGraphAPI.getLiteratureGraph(literature)
      if (response.success && response.data) {
        setGraphData(response.data)
        // 初始化图谱
        setTimeout(() => initGraph(response.data), 100)
      }
    } catch (e) {
      message.error('加载知识图谱失败')
    } finally {
      setGraphLoading(false)
    }
  }

  // 社区检测
  const detectCommunities = async (algorithm = 'leiden') => {
    setCommunityLoading(true)
    try {
      const response = await fetch(`/api/knowledge-graph/communities?algorithm=${algorithm}`)
      const data = await response.json()
      if (data.success && data.data) {
        setCommunityData(data.data)
        message.success(`检测到 ${data.data.stats.total_communities} 个社区`)
      }
    } catch (e) {
      console.error('Community detection error:', e)
      message.error('社区检测失败')
    } finally {
      setCommunityLoading(false)
    }
  }

  // 节点中心性分析
  const analyzeCentrality = async (algorithm = 'degree') => {
    setCommunityLoading(true)
    setAnalysisMode('centrality')
    try {
      const response = await fetch(`/api/knowledge-graph/centrality?algorithm=${algorithm}`)
      const data = await response.json()
      if (data.success && data.data) {
        setCentralityData(data.data)
        message.success(`分析完成，中心性节点: ${data.data.top_hub_nodes?.join(', ')}`)
      }
    } catch (e) {
      console.error('Centrality analysis error:', e)
      message.error('中心性分析失败')
    } finally {
      setCommunityLoading(false)
    }
  }

  // 路径查找
  const findPaths = async (source, target) => {
    if (!source || !target) {
      message.warning('请选择起止节点')
      return
    }
    setCommunityLoading(true)
    setAnalysisMode('paths')
    try {
      const response = await fetch(`/api/knowledge-graph/paths?source=${source}&target=${target}&max_depth=4`)
      const data = await response.json()
      if (data.success && data.data) {
        setPathData(data.data)
        message.success(`找到 ${data.data.path_count} 条路径`)
      }
    } catch (e) {
      console.error('Path finding error:', e)
      message.error('路径查找失败')
    } finally {
      setCommunityLoading(false)
    }
  }

  // 邻居分析
  const analyzeNeighbors = async (nodeId, depth = 1) => {
    if (!nodeId) {
      message.warning('请先选择节点')
      return
    }
    setCommunityLoading(true)
    setAnalysisMode('neighbors')
    try {
      const response = await fetch(`/api/knowledge-graph/entity/${nodeId}/neighbors?depth=${depth}`)
      const data = await response.json()
      if (data.success && data.data) {
        setNeighborData(data.data)
        message.success(`找到 ${data.data.total_neighbors} 个邻居节点`)
      }
    } catch (e) {
      console.error('Neighbor analysis error:', e)
      message.error('邻居分析失败')
    } finally {
      setCommunityLoading(false)
    }
  }

  // 初始化G6图谱
  const initGraph = (data) => {
    if (!graphContainerRef.current || !data?.nodes?.length) return

    // 清理旧图
    if (graphRef.current) {
      graphRef.current.destroy()
    }

    const container = graphContainerRef.current
    const width = container.offsetWidth || 650
    const height = container.offsetHeight || 380

    // 构建节点到社区的映射
    const nodeToCommunity = {}
    if (communityMode && communityData.communities) {
      communityData.communities.forEach((comm, idx) => {
        comm.members.forEach(memberId => {
          nodeToCommunity[memberId] = idx
        })
      })
    }

    // 社区颜色
    const communityColors = [
      '#1890ff', '#722ed1', '#52c41a', '#fa8c16',
      '#eb2f96', '#13c2c2', '#faad14', '#2f54ed',
      '#a0d911', '#ff6b6b', '#4ecdc4', '#45b7d1'
    ]

    // 转换数据为G6格式
    const g6Data = {
      nodes: data.nodes.map(n => {
        // 根据模式选择颜色
        const isCommunityMode = communityMode && communityData.communities?.length > 0
        const communityIdx = nodeToCommunity[n.id]
        const baseType = n.type

        let color, fill, stroke
        if (isCommunityMode && communityIdx !== undefined) {
          color = communityColors[communityIdx % communityColors.length]
          fill = color + '20'
          stroke = color
        } else {
          color = baseType === 'paper' ? '#1890ff' :
                  baseType === 'method' ? '#722ed1' :
                  baseType === 'dataset' ? '#52c41a' :
                  baseType === 'task' ? '#fa8c16' :
                  baseType === 'metric' ? '#eb2f96' :
                  baseType === 'author' ? '#13c2c2' : '#d9d9d9'
          fill = color + '33'
          stroke = color
        }

        return {
          id: n.id,
          label: n.label,
          type: baseType,
          community: communityIdx,
          size: baseType === 'paper' ? 40 : baseType === 'method' ? 30 : 25,
          color,
          style: { fill, stroke }
        }
      }),
      edges: data.edges?.map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        label: e.relation || 'related',
        style: { stroke: '#d9d9d9', lineWidth: 1 }
      })) || []
    }

    try {
      // 使用力导向布局
      const graph = new G6.Graph({
        container: container.id || 'graph-container',
        width,
        height,
        fitView: true,
        layout: {
          type: 'force',
          preventOverlap: true,
          nodeSize: 40,
          nodeSpacing: 20,
          linkDistance: 100,
          nodeStrength: -80,
          edgeStrength: 0.3,
          collideStrength: 0.8,
          alpha: 0.3,
          alphaDecay: 0.02,
        },
        defaultNode: {
          labelCfg: {
            style: {
              fill: '#333',
              fontSize: 11,
              background: {
                fill: '#fff',
                padding: [4, 6, 4, 6],
                radius: 4,
              }
            }
          },
        },
        defaultEdge: {
          labelCfg: {
            autoRotate: true,
            style: { fill: '#999', fontSize: 10 }
          }
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node']
        },
        nodeStateStyles: {
          hover: { shadowBlur: 10, shadowColor: '#666' },
          selected: { stroke: '#000', lineWidth: 2 }
        }
      })

      graph.data(g6Data)
      graph.render()

      // 节点点击事件
      graph.on('node:click', (evt) => {
        const { item } = evt
        const model = item.getModel()
        const nodeData = data.nodes.find(n => n.id === model.id)
        setSelectedNode(nodeData || model)
      })

      graphRef.current = graph
    } catch (e) {
      console.error('G6 init error:', e)
    }
  }

  // 打开图谱时加载数据
  useEffect(() => {
    if (graphVisible && literature.length > 0 && graphData.nodes?.length === 0) {
      loadKnowledgeGraph()
    }
  }, [graphVisible, literature])

  // 组件卸载时销毁图
  useEffect(() => {
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy()
      }
    }
  }, [])

  const libraryColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text) => <Text strong>{text}</Text>,
    },
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 180, ellipsis: true },
    { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
    { title: '期刊', dataIndex: 'journal', key: 'journal', width: 150, ellipsis: true },
    { title: '引用', dataIndex: 'citations', key: 'citations', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          cited: { color: 'green', text: '已引用' },
          pending: { color: 'orange', text: '待引用' },
          not_cited: { color: 'default', text: '未引用' },
        }
        const { color, text } = statusMap[status] || { color: 'default', text: status }
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="引用">
            <Button type="text" size="small" icon={<CheckCircleOutlined />} onClick={() => handleCiteLiterature(record.id)} />
          </Tooltip>
          <Tooltip title="删除">
            <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteLiterature(record.id)} />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const searchResultColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 300,
      ellipsis: true,
      render: (text, record) => (
        <div>
          <Text strong>{text}</Text>
          {record.url && (
            <div><a href={record.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500">{record.url.substring(0, 60)}...</a></div>
          )}
        </div>
      ),
    },
    {
      title: '作者',
      dataIndex: 'authors',
      key: 'authors',
      width: 220,
      ellipsis: true,
      render: (authors, record) => {
        const authorList = authors ? authors.split(',').map(a => a.trim()) : []
        const isLong = authorList.length > 3
        const displayAuthors = expandedAuthors.includes(record.id)
          ? authorList
          : authorList.slice(0, 3)
        return (
          <div>
            <span>{displayAuthors.join(', ')}{isLong && !expandedAuthors.includes(record.id) ? '...' : ''}</span>
            {isLong && (
              <a
                className="ml-1 text-blue-500"
                onClick={(e) => {
                  e.stopPropagation()
                  setExpandedAuthors(prev =>
                    prev.includes(record.id)
                      ? prev.filter(id => id !== record.id)
                      : [...prev, record.id]
                  )
                }}
              >
                {expandedAuthors.includes(record.id) ? '收起' : '展开'}
              </a>
            )}
          </div>
        )
      }
    },
    { title: '年份', dataIndex: 'year', key: 'year', width: 80 },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source) => {
        const config = SOURCE_CONFIG[source] || { label: source, color: '#999' }
        return <Tag color={config.color}>{config.label}</Tag>
      },
    },
    { title: '引用数', dataIndex: 'citations', key: 'citations', width: 80 },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: literature.some(l => l.id === record.id),
    }),
  }

  return (
    <div className="space-y-4">
      {/* 搜索区域 */}
      <Card className="!rounded-lg">
        <div className="text-center py-8">
          <Title level={2} className="!mb-6">学术文献搜索</Title>
          <div className="max-w-2xl mx-auto">
            <Space direction="vertical" size="middle" className="w-full">
              <Input.Search
                placeholder="输入关键词搜索学术文献，如: machine learning, deep learning..."
                prefix={<SearchOutlined />}
                size="large"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onSearch={(value) => handleSearch(value)}
                enterButton={
                  <Button type="primary" size="large" loading={searchLoading}>
                    搜索
                  </Button>
                }
                loading={searchLoading}
                className="!text-lg"
              />
              <div className="flex justify-center gap-2 flex-wrap">
                {SOURCE_CONFIG_LIST.map(source => (
                  <Tag
                    key={source.key}
                    color={sources.includes(source.key) ? source.color : 'default'}
                    className="!px-3 !py-1 !text-sm cursor-pointer"
                    onClick={() => toggleSource(source.key)}
                  >
                    {source.label}
                  </Tag>
                ))}
              </div>
            </Space>
          </div>
        </div>
      </Card>

      {/* 搜索结果区域 */}
      {searchLoading ? (
        <Card className="!rounded-lg">
          <div className="text-center py-16">
            <Spin size="large" tip="正在搜索 arXiv, PubMed, Semantic Scholar, OpenAlex..." />
          </div>
        </Card>
      ) : searchResults.length === 0 ? (
        <Card className="!rounded-lg">
          <Empty
            description={
              <Space direction="vertical">
                <Text>请输入关键词进行学术搜索</Text>
                <Text type="secondary" className="text-sm">支持搜索 arXiv、PubMed、Semantic Scholar、OpenAlex 等多个学术数据库</Text>
              </Space>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      ) : (
        <Card className="!rounded-lg">
          {/* 结果统计 */}
          <div className="flex justify-between items-center mb-4">
            <Text type="secondary">
              找到 <Text strong>{searchResults.length}</Text> 篇相关文献
              {hasMore && `+更多`}
            </Text>
            {selectedRowKeys.length > 0 && (
              <Button type="primary" icon={<PlusCircleOutlined />} onClick={handleBatchAddSelected}>
                添加到文献库 ({selectedRowKeys.length})
              </Button>
            )}
          </div>

          {/* 搜索结果表格 */}
          <Table
            dataSource={searchResults}
            columns={searchResultColumns}
            rowKey="id"
            rowSelection={rowSelection}
            pagination={{ pageSize: 10 }}
            size="middle"
            expandable={{
              rowExpandable: (record) => !!record.abstract,
              expandedRowRender: (record) => (
                <div className="py-2">
                  <Text type="secondary" className="text-sm">{record.abstract}</Text>
                </div>
              ),
            }}
          />
        </Card>
      )}

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
          <Form.Item label="DOI" name="doi">
            <Input placeholder="论文DOI (可选)" />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Select mode="tags" placeholder="添加标签" />
          </Form.Item>
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
                  accept=".pdf,.doc,.docx,.txt"
                  showUploadList={false}
                  beforeUpload={beforeUpload}
                  disabled={uploading}
                >
                  <p className="ant-upload-drag-icon">
                    <FilePdfOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
                  <p className="ant-upload-hint">
                    支持 PDF、Word (.doc/.docx) 或文本文件<br />
                    系统将自动识别文献元数据（标题、作者、年份等）
                  </p>
                </Upload.Dragger>
                <div className="mt-4 text-xs text-gray-400">
                  <Text type="secondary">上传后AI将自动提取文件中的元数据信息</Text>
                </div>
              </>
            )}
          </div>
        </div>
      </Modal>

      {/* 数据来源设置Modal */}
      <Modal
        title={
          <Space>
            <DatabaseOutlined className="text-blue-500" />
            <span>学术数据来源设置</span>
          </Space>
        }
        open={isSourceSettingsOpen}
        onOk={saveSourceSettings}
        onCancel={() => setIsSourceSettingsOpen(false)}
        okText="保存设置"
        cancelText="取消"
        width={500}
      >
        <Alert
          message="数据来源设置"
          description="选择系统从哪些学术数据库搜索论文。不同来源涵盖不同领域，建议全部启用。"
          type="info"
          showIcon
          icon={<DatabaseOutlined />}
          className="!mb-4"
        />

        <Text type="secondary" className="block mb-3">
          当前启用的数据来源（共 {sources.length} 个）:
        </Text>

        <div className="grid grid-cols-2 gap-3 mb-4">
          {SOURCE_CONFIG_LIST.map(source => {
            const isEnabled = sources.includes(source.key)
            return (
              <div
                key={source.key}
                onClick={() => toggleSource(source.key)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  isEnabled
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-gray-50 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: source.color }}
                    ></div>
                    <Text strong className={isEnabled ? 'text-blue-700' : 'text-gray-600'}>
                      {source.label}
                    </Text>
                  </div>
                  <Switch size="small" checked={isEnabled} onChange={() => toggleSource(source.key)} />
                </div>
                <Text type="secondary" className="text-xs">{source.desc}</Text>
              </div>
            )
          })}
        </div>
      </Modal>

    </div>
  )
}

export default LiteraturePage
