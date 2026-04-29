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
import { knowledgeGraphAPI, literatureAPI } from '../services/api'
import { usePaperStore } from '../store/paperStore'
import * as G6 from '@antv/g6'

const { Text, Title, Paragraph } = AntTypography
const { Option } = Select
const { TabPane } = Tabs
const { Search } = Input

// 社区颜色配置
const COMMUNITY_COLORS = [
  '#1890ff', '#722ed1', '#52c41a', '#fa8c16',
  '#eb2f96', '#13c2c2', '#faad14', '#2f54ed',
  '#a0d911', '#ff6b6b', '#4ecdc4', '#45b7d1'
]

// 节点类型颜色
const TYPE_COLORS = {
  paper: '#1890ff',
  method: '#722ed1',
  dataset: '#52c41a',
  task: '#fa8c16',
  metric: '#eb2f96',
  author: '#13c2c2',
  unknown: '#d9d9d9'
}

// 年份颜色渐变 (浅蓝到深红，越新越深)
const YEAR_COLORS = [
  '#e6f7ff', '#b3d9ff', '#80bbff', '#4d9dff', '#1a80ff',
  '#0070f0', '#005acc', '#0044a8', '#002e84', '#001860'
]

// 根据年份获取颜色 (Connected Papers风格：越新越深)
const getYearColor = (year) => {
  if (!year) return '#e6f7ff'
  const minYear = 2015
  const maxYear = 2026
  const normalized = Math.max(0, Math.min(1, (year - minYear) / (maxYear - minYear)))
  const idx = Math.floor(normalized * (YEAR_COLORS.length - 1))
  return YEAR_COLORS[idx] || '#e6f7ff'
}

const KnowledgeGraphPage = () => {
  // 图谱状态
  const [graphLoading, setGraphLoading] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], stats: {} })
  const [selectedNode, setSelectedNode] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [communityData, setCommunityData] = useState({ communities: [], stats: {} })

  // 视图控制
  const [viewMode, setViewMode] = useState('year') // community, type, degree, year
  const [yearRange, setYearRange] = useState([2000, 2026])
  const [showFilters, setShowFilters] = useState(true)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [fitView, setFitView] = useState(false)
  const [sortBy, setSortBy] = useState('citations') // citations, year, title

  // 搜索
  const [searchText, setSearchText] = useState('')
  const [filteredNodes, setFilteredNodes] = useState([])
  const [paperSearchText, setPaperSearchText] = useState('')

  // GraphRAG问答
  const [queryText, setQueryText] = useState('')
  const [queryResult, setQueryResult] = useState(null)
  const [queryLoading, setQueryLoading] = useState(false)
  const [showQueryPanel, setShowQueryPanel] = useState(false)

  // 引用分类
  const [priorPapers, setPriorPapers] = useState([]) // 当前论文引用的
  const [derivativePapers, setDerivativePapers] = useState([]) // 引用当前论文的

  // 使用文献库数据
  const { literature, addLiterature, deleteLiterature, updateLiterature } = usePaperStore()

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
    return literature.filter(item =>
      item.title?.toLowerCase().includes(lower) ||
      item.authors?.toLowerCase().includes(lower) ||
      item.journal?.toLowerCase().includes(lower)
    )
  }, [literature, literatureSearchText])

  // 文献库列定义
  const literatureColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 250,
      ellipsis: true,
      render: (text) => <Text ellipsis>{text}</Text>,
    },
    { title: '作者', dataIndex: 'authors', key: 'authors', width: 150, ellipsis: true },
    { title: '年份', dataIndex: 'year', key: 'year', width: 70 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => {
        const statusMap = {
          cited: { color: 'green', text: '已引用' },
          pending: { color: 'orange', text: '待引用' },
        }
        const { color, text } = statusMap[status] || { color: 'default', text: status }
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <Space>
          <Tooltip title="添加到知识图谱">
            <Button type="text" size="small" icon={<BuildOutlined />} onClick={() => handleBuildFromLiterature(record.id)} />
          </Tooltip>
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

  // 引用文献
  const handleCiteLiterature = (id) => {
    updateLiterature(id, { status: 'cited' })
    message.success('文献已引用')
  }

  // 在图谱中查看
  const handleViewInGraph = (id) => {
    const paper = literature.find(p => p.id === id)
    if (paper) {
      setSelectedNode({
        id: paper.id,
        title: paper.title,
        year: paper.year,
        citations: paper.citations || paper.citedCount || 0,
        authors: paper.authors || [],
        type: 'paper'
      })
    }
  }

  // 删除文献
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

  // 添加文献
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

  // 上传文件
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
    if (!isPdf && !isDocx) {
      message.error('只支持 PDF、Word 文件！')
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

  // 学术搜索
  const handleSearch = async (query) => {
    const q = query || searchQuery
    if (!q.trim()) {
      message.warning('请输入搜索关键词')
      return
    }
    setSearchLoading(true)
    try {
      const result = await literatureAPI.search(q, { max_results: 10 })
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
        }))
        setSearchResults(papers)
      } else {
        message.warning('未找到相关文献')
        setSearchResults([])
      }
    } catch (e) {
      message.error('搜索失败: ' + (e.message || '网络错误'))
    } finally {
      setSearchLoading(false)
    }
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

  // Refs
  const graphRef = useRef(null)
  const containerRef = useRef(null)
  const hasLoadedFromLiterature = useRef(false)

  // 初始化图谱
  useEffect(() => {
    loadGraphData()
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy()
      }
    }
  }, [])

  // literature变化时重新加载图谱（仅当尚未从文献库加载时）
  useEffect(() => {
    if (literature.length > 0 && graphData.nodes.length === 0 && !hasLoadedFromLiterature.current) {
      hasLoadedFromLiterature.current = true
      loadGraphFromLiterature()
    }
  }, [literature])

  // 重新渲染图谱当视图模式改变时
  useEffect(() => {
    if (graphRef.current && graphData.nodes.length > 0) {
      updateNodeStyles()
    }
  }, [viewMode, communityData])

  // 从文献库加载图谱
  const loadGraphFromLiterature = async () => {
    if (!literature || literature.length === 0) {
      message.info('文献库为空，请先添加文献')
      return
    }

    setGraphLoading(true)
    try {
      // 调用API从文献库构建图谱
      const response = await knowledgeGraphAPI.getLiteratureGraph(literature)
      if (response.success && response.data) {
        setGraphData(response.data)

        // 检测社区
        await detectCommunities()

        // 初始化图谱
        setTimeout(() => initGraph(response.data), 100)
      }
    } catch (e) {
      console.error('Load from literature error:', e)
      // 如果API失败，使用本地数据构建
      const localData = generateFromLiteratureData(literature)
      setGraphData(localData)
      setTimeout(() => initGraph(localData), 100)
    } finally {
      setGraphLoading(false)
    }
  }

  // 从本地文献数据生成本地图谱
  const generateFromLiteratureData = (litData) => {
    const nodes = litData.map((paper, idx) => ({
      id: paper.id || `paper_${idx}`,
      label: (paper.title || 'Untitled').length > 28 ? (paper.title || 'Untitled').substring(0, 28) + '...' : (paper.title || 'Untitled'),
      title: paper.title || 'Untitled',
      year: paper.year || 2020,
      citations: paper.citations || paper.citedCount || 0,
      authors: paper.authors || [],
      type: 'paper',
      nodeInfo: {
        id: paper.id,
        title: paper.title,
        year: paper.year,
        citations: paper.citations || paper.citedCount || 0,
        authors: paper.authors,
        type: 'paper'
      },
      size: Math.max(20, Math.min(50, Math.log((paper.citations || paper.citedCount || 0) + 1) * 4))
    }))

    // 生成边（基于年份相近和共同作者）
    const edges = []
    for (let i = 0; i < litData.length; i++) {
      for (let j = i + 1; j < litData.length; j++) {
        const p1 = litData[i]
        const p2 = litData[j]

        // 处理 authors 可能是字符串或数组的情况
        const authors1 = Array.isArray(p1.authors) ? p1.authors : (typeof p1.authors === 'string' ? p1.authors.split(',').map(a => a.trim()) : [])
        const authors2 = Array.isArray(p2.authors) ? p2.authors : (typeof p2.authors === 'string' ? p2.authors.split(',').map(a => a.trim()) : [])

        // 如果有共同作者或年份相近，创建边
        const hasCommonAuthor = authors1.some(a1 => authors2.some(a2 => a1.toLowerCase() === a2.toLowerCase()))
        const sameYear = p1.year === p2.year
        if (hasCommonAuthor || sameYear) {
          edges.push({
            source: p1.id || `paper_${i}`,
            target: p2.id || `paper_${j}`,
            relation: hasCommonAuthor ? 'co_author' : 'same_year'
          })
        }
      }
    }

    return {
      nodes,
      edges,
      stats: {
        totalNodes: nodes.length,
        totalEdges: edges.length,
        paperCount: nodes.length
      }
    }
  }

  // 加载图谱数据
  const loadGraphData = async () => {
    setGraphLoading(true)
    try {
      // 如果文献库有数据，使用文献库
      if (literature.length > 0 && !hasLoadedFromLiterature.current) {
        hasLoadedFromLiterature.current = true
        await loadGraphFromLiterature()
      }
      // 文献库为空时不加载任何数据，保持空白
    } catch (e) {
      console.error('Load graph error:', e)
      message.error('加载图谱失败')
    } finally {
      setGraphLoading(false)
    }
  }

  // 从文献库下拉菜单构建图谱
  const handleBuildFromLiterature = async (paperId) => {
    const paper = literature.find(p => p.id === paperId)
    if (!paper) return

    setGraphLoading(true)
    try {
      // 先尝试搜索论文获取真实引用数
      let realCitations = paper.citations || paper.citedCount || 0
      try {
        const searchResult = await literatureAPI.search(paper.title, { max_results: 5 })
        if (searchResult.success && searchResult.data) {
          const matchedPaper = searchResult.data.find(p =>
            p.title?.toLowerCase().includes(paper.title?.toLowerCase().substring(0, 30)) ||
            paper.title?.toLowerCase().includes(p.title?.toLowerCase().substring(0, 30))
          )
          if (matchedPaper) {
            realCitations = matchedPaper.citations || realCitations
          }
        }
      } catch (e) {
        console.log('Search for citations failed, using local value')
      }

      // 转换 authors 为数组
      const paperAuthors = Array.isArray(paper.authors)
        ? paper.authors
        : (typeof paper.authors === 'string' ? paper.authors.split(',').map(a => a.trim()) : [])

      // 查找相关的论文（共同作者、年份相近）
      const relatedPapers = literature.filter(p => {
        if (p.id === paperId) return false
        const pAuthors = Array.isArray(p.authors)
          ? p.authors
          : (typeof p.authors === 'string' ? p.authors.split(',').map(a => a.trim()) : [])
        const hasCommonAuthor = paperAuthors.some(a1 => pAuthors.some(a2 => a1.toLowerCase() === a2.toLowerCase()))
        const similarYear = Math.abs((paper.year || 2020) - (p.year || 2020)) <= 2
        return hasCommonAuthor || similarYear
      })

      // 合并目标论文和相关文章
      const paperWithCitations = { ...paper, citations: realCitations }
      const graphPapers = [paperWithCitations, ...relatedPapers]
      const localData = generateFromLiteratureData(graphPapers)

      setSelectedNode({
        id: paper.id,
        title: paper.title,
        year: paper.year,
        citations: paper.citations || paper.citedCount || 0,
        authors: paper.authors || [],
        type: 'paper'
      })

      setGraphData(localData)

      // 尝试社区检测，但不阻塞主流程
      detectCommunities().catch(() => {})

      // 初始化图谱
      setTimeout(() => {
        initGraph(localData)
      }, 100)
    } catch (e) {
      console.error('Build from literature error:', e)
      message.error('构建图谱失败: ' + (e.message || e.name || '未知错误'))
    } finally {
      setGraphLoading(false)
    }
  }

  // 构建图谱 - Connected Papers核心功能
  const handleBuildGraph = async (value) => {
    if (!value?.trim()) {
      message.warning('请输入论文标题或DOI')
      return
    }

    setGraphLoading(true)
    try {
      // 模拟搜索论文（实际应调用文献搜索API）
      message.loading({ content: '搜索论文...', key: 'search' })

      // 模拟找到目标论文
      const targetPaper = {
        id: 'target_paper',
        title: value,
        year: 2020,
        citations: 10000,
        authors: ['Search Author'],
        type: 'paper'
      }

      // 生成以目标论文为核心的图谱
      const mockData = generateTargetedGraphData(targetPaper)
      setGraphData(mockData)
      setSelectedNode(targetPaper)

      // 检测社区并初始化图谱
      await detectCommunities()
      setTimeout(() => initGraph(mockData), 100)
    } catch (e) {
      console.error('Build graph error:', e)
      message.error({ content: '构建图谱失败', key: 'search' })
    } finally {
      setGraphLoading(false)
    }
  }

  // GraphRAG知识问答
  const handleGraphQuery = async () => {
    if (!queryText?.trim()) {
      message.warning('请输入问题')
      return
    }

    if (!graphData.nodes || graphData.nodes.length === 0) {
      message.warning('请先构建图谱')
      return
    }

    setQueryLoading(true)
    try {
      // 调用GraphRAG问答API
      const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
      const response = await fetch('/api/knowledge-graph/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey
        },
        body: JSON.stringify({
          question: queryText,
          papers: literature.length > 0 ? literature : graphData.nodes.map(n => ({
            id: n.id,
            title: n.title || n.label,
            abstract: '',
            authors: n.authors || []
          }))
        })
      })

      const data = await response.json()
      if (data.success) {
        setQueryResult(data.data)
        setShowQueryPanel(true)
        message.success('问答完成')
      } else {
        message.error(data.error || '问答失败')
      }
    } catch (e) {
      console.error('Query error:', e)
      message.error('问答请求失败')
    } finally {
      setQueryLoading(false)
    }
  }

  // 生成以目标论文为核心的图谱数据
  const generateTargetedGraphData = (targetPaper) => {
    // Prior works - 目标论文引用的
    const priorPapers = [
      { id: 'prior_1', title: 'Attention Is All You Need', year: 2017, citations: 50000, authors: ['Vaswani et al.'] },
      { id: 'prior_2', title: 'BERT: Pre-training', year: 2018, citations: 40000, authors: ['Devlin et al.'] },
      { id: 'prior_3', title: 'Neural Machine Translation', year: 2016, citations: 15000, authors: ['Bahdanau et al.'] },
      { id: 'prior_4', title: 'Word2Vec', year: 2013, citations: 30000, authors: ['Mikolov et al.'] },
    ]

    // Derivative works - 引用目标论文的
    const derivativePapers = [
      { id: 'deriv_1', title: 'ChatGPT Analysis', year: 2023, citations: 5000, authors: ['Future Author'] },
      { id: 'deriv_2', title: 'GPT-4 Survey', year: 2024, citations: 3000, authors: ['New Author'] },
      { id: 'deriv_3', title: 'LLM Research', year: 2023, citations: 8000, authors: ['Another Author'] },
    ]

    const allPapers = [targetPaper, ...priorPapers, ...derivativePapers]

    const nodes = allPapers.map((p, idx) => ({
      id: p.id,
      label: p.title.length > 28 ? p.title.substring(0, 28) + '...' : p.title,
      title: p.title,
      year: p.year,
      citations: p.citations,
      authors: p.authors,
      type: 'paper',
      nodeInfo: {
        id: p.id,
        title: p.title,
        year: p.year,
        citations: p.citations,
        authors: p.authors,
        type: 'paper'
      },
      size: p.id === 'target_paper' ? 50 : Math.max(20, Math.min(45, Math.log(p.citations + 1) * 4)),
      isTarget: p.id === 'target_paper'
    }))

    const edges = [
      // 目标论文的边
      { source: 'prior_1', target: 'target_paper', relation: 'cites' },
      { source: 'prior_2', target: 'target_paper', relation: 'cites' },
      { source: 'prior_3', target: 'target_paper', relation: 'cites' },
      { source: 'prior_4', target: 'target_paper', relation: 'cites' },
      { source: 'target_paper', target: 'deriv_1', relation: 'cites' },
      { source: 'target_paper', target: 'deriv_2', relation: 'cites' },
      { source: 'target_paper', target: 'deriv_3', relation: 'cites' },
      // Prior之间的关联
      { source: 'prior_1', target: 'prior_2', relation: 'cites' },
      { source: 'prior_3', target: 'prior_1', relation: 'cites' },
      // Derivative之间的关联
      { source: 'deriv_1', target: 'deriv_2', relation: 'cites' },
      { source: 'deriv_2', target: 'deriv_3', relation: 'cites' },
    ]

    return {
      nodes,
      edges,
      stats: {
        totalNodes: nodes.length,
        totalEdges: edges.length,
        paperCount: allPapers.length,
        targetPaper: targetPaper
      }
    }
  }

  // 生成模拟图谱数据
  const generateMockGraphData = () => {
    const papers = [
      { id: 'paper_1', title: 'Attention Is All You Need', year: 2017, citations: 50000, authors: ['Vaswani et al.'] },
      { id: 'paper_2', title: 'BERT: Pre-training', year: 2018, citations: 40000, authors: ['Devlin et al.'] },
      { id: 'paper_3', title: 'GPT-3', year: 2020, citations: 30000, authors: ['Brown et al.'] },
      { id: 'paper_4', title: 'Deep Learning', year: 2015, citations: 25000, authors: ['LeCun et al.'] },
      { id: 'paper_5', title: 'ResNet', year: 2016, citations: 80000, authors: ['He et al.'] },
      { id: 'paper_6', title: 'Transformer-XL', year: 2019, citations: 8000, authors: ['Dai et al.'] },
      { id: 'paper_7', title: 'XLNet', year: 2019, citations: 12000, authors: ['Yang et al.'] },
      { id: 'paper_8', title: 'RoBERTa', year: 2019, citations: 15000, authors: ['Liu et al.'] },
      { id: 'paper_9', title: 'ALBERT', year: 2019, citations: 10000, authors: ['Lan et al.'] },
      { id: 'paper_10', title: 'T5', year: 2019, citations: 18000, authors: ['Raffel et al.'] },
      { id: 'paper_11', title: 'BART', year: 2019, citations: 9000, authors: ['Lewis et al.'] },
      { id: 'paper_12', title: 'ELECTRA', year: 2020, citations: 5000, authors: ['Clark et al.'] },
    ]

    const methods = [
      { id: 'method_transformer', title: 'Transformer', type: 'method' },
      { id: 'method_attention', title: 'Self-Attention', type: 'method' },
      { id: 'method_bert', title: 'BERT', type: 'method' },
      { id: 'method_gpt', title: 'GPT', type: 'method' },
      { id: 'method_cnn', title: 'CNN', type: 'method' },
      { id: 'method_lstm', title: 'LSTM', type: 'method' },
    ]

    const datasets = [
      { id: 'dataset_glue', title: 'GLUE', type: 'dataset' },
      { id: 'dataset_squad', title: 'SQuAD', type: 'dataset' },
      { id: 'dataset_imagenet', title: 'ImageNet', type: 'dataset' },
    ]

    const nodes = [
      ...papers.map(p => ({
        id: p.id,
        label: p.title.length > 30 ? p.title.substring(0, 30) + '...' : p.title,
        title: p.title,
        year: p.year,
        citations: p.citations,
        authors: p.authors,
        type: 'paper',
        size: Math.max(20, Math.min(60, Math.log(p.citations + 1) * 5))
      })),
      ...methods.map(m => ({
        id: m.id,
        label: m.title,
        title: m.title,
        type: m.type,
        size: 25
      })),
      ...datasets.map(d => ({
        id: d.id,
        label: d.title,
        title: d.title,
        type: d.type,
        size: 22
      }))
    ]

    const edges = [
      // Transformer相关
      { source: 'paper_1', target: 'method_transformer', relation: 'proposes' },
      { source: 'paper_1', target: 'method_attention', relation: 'uses' },
      { source: 'paper_2', target: 'paper_1', relation: 'cites' },
      { source: 'paper_2', target: 'method_bert', relation: 'proposes' },
      { source: 'paper_2', target: 'dataset_glue', relation: 'benchmarks' },
      { source: 'paper_3', target: 'paper_2', relation: 'cites' },
      { source: 'paper_3', target: 'method_gpt', relation: 'proposes' },
      { source: 'paper_6', target: 'paper_1', relation: 'cites' },
      { source: 'paper_6', target: 'method_transformer', relation: 'extends' },
      { source: 'paper_7', target: 'paper_1', relation: 'cites' },
      { source: 'paper_7', target: 'paper_6', relation: 'cites' },
      { source: 'paper_8', target: 'paper_2', relation: 'improves' },
      { source: 'paper_9', target: 'paper_2', relation: 'improves' },
      { source: 'paper_10', target: 'paper_1', relation: 'cites' },
      { source: 'paper_10', target: 'paper_6', relation: 'cites' },
      { source: 'paper_11', target: 'paper_1', relation: 'cites' },
      { source: 'paper_12', target: 'paper_2', relation: 'cites' },
      // CNN/LSTM相关
      { source: 'paper_4', target: 'method_cnn', relation: 'surveys' },
      { source: 'paper_4', target: 'method_lstm', relation: 'surveys' },
      { source: 'paper_5', target: 'method_cnn', relation: 'proposes' },
      { source: 'paper_5', target: 'dataset_imagenet', relation: 'uses' },
      // 跨领域连接
      { source: 'paper_2', target: 'dataset_squad', relation: 'benchmarks' },
    ]

    return {
      nodes,
      edges,
      stats: {
        totalNodes: nodes.length,
        totalEdges: edges.length,
        paperCount: papers.length,
        methodCount: methods.length,
        datasetCount: datasets.length
      }
    }
  }

  // 检测社区
  const detectCommunities = async () => {
    try {
      const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
      const response = await fetch('/api/knowledge-graph/communities?algorithm=leiden', {
        headers: { 'x-api-key': apiKey }
      })
      const data = await response.json()
      if (data.success && data.data) {
        setCommunityData(data.data)
      }
    } catch (e) {
      console.error('Community detection error:', e)
    }
  }

  // 初始化G6图谱
  const initGraph = useCallback((data) => {
    if (!containerRef.current || !data?.nodes?.length) return

    // 清理旧图
    if (graphRef.current) {
      graphRef.current.destroy()
    }

    const container = containerRef.current
    const width = container.offsetWidth || 800
    const height = container.offsetHeight || 600

    // 构建节点到社区的映射
    const nodeToCommunity = {}
    if (communityData.communities) {
      communityData.communities.forEach((comm, idx) => {
        comm.members.forEach(memberId => {
          nodeToCommunity[memberId] = idx
        })
      })
    }

    // 准备G6数据
    const g6Data = {
      nodes: data.nodes.map(n => {
        const communityIdx = nodeToCommunity[n.id]
        const baseColor = TYPE_COLORS[n.type] || TYPE_COLORS.unknown

        let color
        if (viewMode === 'community' && communityIdx !== undefined) {
          color = COMMUNITY_COLORS[communityIdx % COMMUNITY_COLORS.length]
        } else if (viewMode === 'year') {
          // 年份着色：越新的论文颜色越深
          color = getYearColor(n.year)
        } else {
          color = baseColor
        }

        // 目标论文（搜索的论文）用特殊样式 - Connected Papers风格：黑色描边
        const isTarget = n.isTarget || n.id === 'target_paper'
        const targetStyle = isTarget ? {
          fill: color + 'ff',
          stroke: '#000000',
          lineWidth: 4,
          shadowBlur: 16,
          shadowColor: '#00000040'
        } : {
          fill: color + 'cc',
          stroke: color,
          lineWidth: 2,
          shadowBlur: 8,
          shadowColor: color + '40'
        }

        return {
          id: n.id,
          label: n.label,
          size: n.size || 30,
          color: color,
          style: targetStyle,
          nodeInfo: n // 存储完整信息
        }
      }),
      edges: data.edges.map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        label: e.relation || '',
        style: {
          stroke: '#d9d9d9',
          lineWidth: 1,
          opacity: 0.6
        }
      }))
    }

    // 创建图实例
    const graph = new G6.Graph({
      container: container,
      width,
      height,
      data: g6Data,
      node: {
        style: {
          size: 30,
          color: '#1890ff',
          fill: '#1890ff',
          stroke: '#1890ff',
          lineWidth: 2,
        },
        labelText: 'label',
      },
      edge: {
        style: {
          stroke: '#d9d9d9',
          lineWidth: 1,
        },
        labelText: 'relation',
      },
      layout: {
        type: 'force',
        preventOverlap: true,
        nodeSpacing: 30,
        linkDistance: 150,
        nodeStrength: -200,
        edgeStrength: 0.3,
        collideStrength: 0.8,
        alpha: 0.3,
        alphaDecay: 0.02,
        alphaMin: 0.001
      },
      behaviors: [
        'drag-canvas',
        'zoom-canvas',
      ],
      autoFit: true,
    })

    // G6 v5 点击事件
    graph.on('node:click', (evt) => {
      const nodeId = evt.target.id
      if (nodeId && graph.getNodeData) {
        const nodeData = graph.getNodeData(nodeId)
        console.log('nodeData from graph:', nodeData)
        // 使用 nodeInfo 中的完整数据，如果没有则使用 nodeData 本身
        const fullData = nodeData?.nodeInfo || nodeData
        setSelectedNode(fullData)
        if (fullData?.id) calculatePaperConnections(fullData.id)
      }
    })

    graph.on('canvas:click', () => {
      console.log('canvas:click')
      setSelectedNode(null)
      setPriorPapers([])
      setDerivativePapers([])
    })

    // 渲染
    graph.render()
    console.log('Graph rendered')

    graphRef.current = graph
  }, [communityData, viewMode])

  // 计算论文的引用关系
  const calculatePaperConnections = (nodeId) => {
    const prior = []
    const derivative = []

    graphData.edges.forEach(edge => {
      if (edge.source === nodeId) {
        // 当前论文引用的
        const targetNode = graphData.nodes.find(n => n.id === edge.target)
        if (targetNode?.type === 'paper') {
          prior.push({ ...targetNode, relation: edge.relation })
        }
      }
      if (edge.target === nodeId && edge.relation === 'cites') {
        // 引用当前论文的
        const sourceNode = graphData.nodes.find(n => n.id === edge.source)
        if (sourceNode?.type === 'paper') {
          derivative.push({ ...sourceNode, relation: 'cites' })
        }
      }
    })

    setPriorPapers(prior)
    setDerivativePapers(derivative)
  }

  // 更新节点样式 - G6 v5
  const updateNodeStyles = () => {
    if (!graphRef.current || !graphData.nodes.length) return

    const graph = graphRef.current

    // 构建节点ID到社区的映射
    const nodeToCommunity = {}
    if (communityData.communities) {
      communityData.communities.forEach((comm, idx) => {
        comm.members.forEach(memberId => {
          nodeToCommunity[memberId] = idx
        })
      })
    }

    // 创建节点ID到原始数据的映射
    const nodeDataMap = {}
    graphData.nodes.forEach(n => { nodeDataMap[n.id] = n })

    // 更新每个节点的颜色
    graphData.nodes.forEach(node => {
      const originalNode = nodeDataMap[node.id]
      if (!originalNode) return

      const communityIdx = nodeToCommunity[node.id]

      let newColor
      if (viewMode === 'community' && communityIdx !== undefined) {
        newColor = COMMUNITY_COLORS[communityIdx % COMMUNITY_COLORS.length]
      } else if (viewMode === 'year') {
        newColor = getYearColor(originalNode.year)
      } else if (viewMode === 'degree') {
        const degree = graphData.edges.filter(
          e => e.source === node.id || e.target === node.id
        ).length
        newColor = degree > 3 ? '#ff4d4f' : degree > 1 ? '#faad14' : '#52c41a'
      } else {
        newColor = TYPE_COLORS[originalNode.type] || TYPE_COLORS.unknown
      }

      // 直接从graphData获取当前样式
      const currentNodeData = graph.getNodeData(node.id)
      const currentStyle = currentNodeData?.style || {}

      // 更新节点颜色
      graph.updateNodeData(node.id, {
        style: {
          ...currentStyle,
          color: newColor,
          fill: newColor,
          stroke: newColor
        }
      })
    })

    // 重新绘制
    graph.draw()
  }

  // 缩放控制
  const handleZoom = (delta) => {
    if (!graphRef.current) return
    const zoom = graphRef.current.getZoom()
    graphRef.current.zoomTo(zoom + delta, { x: 400, y: 300 })
    setZoomLevel(graphRef.current.getZoom())
  }

  // 适应视图
  const handleFitView = () => {
    if (!graphRef.current) return
    graphRef.current.fitView()
    setZoomLevel(1)
    setFitView(!fitView)
  }

  // 筛选节点
  const filterNodes = (searchTerm) => {
    setSearchText(searchTerm)
    if (!searchTerm.trim()) {
      setFilteredNodes([])
      return
    }

    const filtered = graphData.nodes.filter(n =>
      n.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.label?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    setFilteredNodes(filtered)

    // 高亮匹配的节点
    if (graphRef.current && filtered.length > 0) {
      const graph = graphRef.current
      graph.getNodes().forEach(node => {
        const model = node.getModel()
        const isMatch = filtered.some(f => f.id === model.id)
        if (isMatch) {
          graph.setItemState(node, 'active', true)
        } else {
          graph.setItemState(node, 'active', false)
        }
      })
    }
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
              onPressEnter={handleGraphQuery}
              style={{ width: 300 }}
              size="small"
            />
            <Button type="primary" icon={<SearchOutlined />} onClick={handleGraphQuery} loading={queryLoading} size="small">
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
                        onClick={() => { setSelectedNode(paper); calculatePaperConnections(paper.id); }}
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
                        onClick={() => { setSelectedNode(paper); calculatePaperConnections(paper.id); }}
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
                              calculatePaperConnections(otherNode.id)
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
