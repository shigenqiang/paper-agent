/**
 * 自定义 hook：知识图谱 G6 交互管理
 *
 * 负责图谱的初始化、缩放、筛选等交互逻辑。
 */
import { useState, useCallback, useRef } from 'react'
import * as G6 from '@antv/g6'

const COMMUNITY_COLORS = [
  '#1890ff', '#722ed1', '#52c41a', '#fa8c16',
  '#eb2f96', '#13c2c2', '#faad14', '#2f54ed',
  '#a0d911', '#ff6b6b', '#4ecdc4', '#45b7d1'
]

const TYPE_COLORS = {
  paper: '#1890ff',
  method: '#722ed1',
  dataset: '#52c41a',
  task: '#fa8c16',
  metric: '#eb2f96',
  author: '#13c2c2',
  unknown: '#d9d9d9'
}

const YEAR_COLORS = [
  '#e6f7ff', '#b3d9ff', '#80bbff', '#4d9dff', '#1a80ff',
  '#0070f0', '#005acc', '#0044a8', '#002e84', '#001860'
]

const getYearColor = (year) => {
  if (!year) return '#e6f7ff'
  const minYear = 2015
  const maxYear = 2026
  const normalized = Math.max(0, Math.min(1, (year - minYear) / (maxYear - minYear)))
  const idx = Math.floor(normalized * (YEAR_COLORS.length - 1))
  return YEAR_COLORS[idx] || '#e6f7ff'
}

export const useGraphInteraction = () => {
  const graphRef = useRef(null)
  const containerRef = useRef(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [selectedNode, setSelectedNode] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [priorPapers, setPriorPapers] = useState([])
  const [derivativePapers, setDerivativePapers] = useState([])

  const calculatePaperConnections = useCallback((nodeId, graphData) => {
    const prior = []
    const derivative = []
    for (const edge of graphData.edges || []) {
      if (edge.source === nodeId) {
        const targetNode = graphData.nodes.find(n => n.id === edge.target)
        if (targetNode) derivative.push(targetNode)
      }
      if (edge.target === nodeId) {
        const sourceNode = graphData.nodes.find(n => n.id === edge.source)
        if (sourceNode) prior.push(sourceNode)
      }
    }
    setPriorPapers(prior)
    setDerivativePapers(derivative)
  }, [])

  const initGraph = useCallback((data, viewMode, graphData) => {
    const container = containerRef.current
    if (!container) return

    const width = container.offsetWidth || 800
    const height = container.offsetHeight || 600

    const nodeToCommunity = {}
    if (viewMode === 'community') {
      data.nodes.forEach((node, idx) => {
        nodeToCommunity[node.id] = idx % COMMUNITY_COLORS.length
      })
    }

    const g6Data = {
      nodes: data.nodes.map(n => ({
        ...n,
        nodeInfo: n,
        size: Math.max(20, Math.min(60, (n.citations || 0) / 5 + 20)),
        style: {
          fill: viewMode === 'community'
            ? COMMUNITY_COLORS[nodeToCommunity[n.id] || 0]
            : viewMode === 'type'
            ? TYPE_COLORS[n.type] || TYPE_COLORS.unknown
            : viewMode === 'year'
            ? getYearColor(n.year)
            : TYPE_COLORS[n.type] || TYPE_COLORS.unknown,
          stroke: n.isTarget ? '#000' : '#fff',
          lineWidth: n.isTarget ? 3 : 1,
        },
        label: n.title?.length > 15 ? n.title.slice(0, 15) + '...' : (n.label || n.title || ''),
        labelCfg: { style: { fontSize: 8, fill: '#333' } },
      })),
      edges: data.edges.map(e => ({
        ...e,
        style: { stroke: '#ccc', lineWidth: (e.weight || 0.5) * 2 },
      })),
    }

    if (graphRef.current) {
      graphRef.current.destroy()
    }

    const graph = new G6.Graph({
      container: 'knowledge-graph-container',
      width,
      height,
      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
      },
      layout: {
        type: 'force',
        preventOverlap: true,
        nodeSize: 40,
        linkDistance: 150,
        nodeStrength: -50,
      },
      defaultNode: {
        type: 'circle',
        size: 30,
        style: { fill: '#1890ff', stroke: '#fff', lineWidth: 1 },
        labelCfg: { style: { fontSize: 8 } },
      },
      defaultEdge: {
        type: 'line',
        style: { stroke: '#ccc', lineWidth: 1 },
      },
    })

    graph.data(g6Data)
    graph.render()

    graph.on('node:mouseenter', (evt) => {
      const nodeId = evt.target.id
      const nodeData = graph.getNodeData(nodeId)
      const fullData = nodeData?.nodeInfo || nodeData
      setHoveredNode(fullData)
    })

    graph.on('node:mouseleave', () => {
      setHoveredNode(null)
    })

    graph.on('node:click', (evt) => {
      const nodeId = evt.target.id
      const nodeData = graph.getNodeData(nodeId)
      const fullData = nodeData?.nodeInfo || nodeData
      setSelectedNode(fullData)
      calculatePaperConnections(nodeId, graphData)
    })

    graphRef.current = graph
  }, [calculatePaperConnections])

  const handleZoom = useCallback((delta) => {
    if (!graphRef.current) return
    const zoom = graphRef.current.getZoom()
    const newZoom = Math.max(0.1, Math.min(2, zoom + delta))
    graphRef.current.zoomTo(newZoom)
    setZoomLevel(newZoom)
  }, [])

  const handleFitView = useCallback(() => {
    if (!graphRef.current) return
    graphRef.current.fitView(20)
    setZoomLevel(graphRef.current.getZoom())
  }, [])

  const filterNodes = useCallback((searchTerm, graphData) => {
    if (!graphRef.current || !searchTerm) return
    const filtered = graphData.nodes.filter(n =>
      n.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.label?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    const graph = graphRef.current
    graphData.nodes.forEach(node => {
      const model = node // graph nodes are direct data
      const isMatch = filtered.some(f => f.id === model.id)
      graph.updateItem(model.id, {
        style: { opacity: isMatch ? 1 : 0.2 },
      })
    })
  }, [])

  return {
    graphRef,
    containerRef,
    zoomLevel,
    selectedNode,
    setSelectedNode,
    hoveredNode,
    setHoveredNode,
    priorPapers,
    derivativePapers,
    initGraph,
    handleZoom,
    handleFitView,
    filterNodes,
    calculatePaperConnections,
  }
}

export { COMMUNITY_COLORS, TYPE_COLORS, YEAR_COLORS, getYearColor }
