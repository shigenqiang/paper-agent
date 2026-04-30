/**
 * 知识图谱可视化组件
 * 负责G6图谱的初始化、渲染和交互
 */
import React, { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import * as G6 from '@antv/g6'

// 社区颜色配置
const COMMUNITY_COLORS = [
  '#1890ff', '#722ed1', '#52c41a', '#fa8c16',
  '#eb2f96', '#13c2c2', '#faad14', '#2f54ed',
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

// 年份颜色渐变
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

const GraphVisualization = forwardRef(({
  graphData,
  viewMode,
  communityData,
  onNodeClick,
  onNodeHover,
  zoomLevel,
}, ref) => {
  const containerRef = useRef(null)
  const graphRef = useRef(null)

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    getGraph: () => graphRef.current,
    destroy: () => {
      if (graphRef.current) {
        graphRef.current.destroy()
        graphRef.current = null
      }
    }
  }))

  // 根据视图模式更新节点样式
  const updateNodeStyles = () => {
    if (!graphRef.current || !graphData?.nodes?.length) return

    const graph = graphRef.current
    const nodes = graph.getNodes()

    nodes.forEach(node => {
      const model = node.getModel()
      let color = TYPE_COLORS[model.type] || TYPE_COLORS.unknown

      if (viewMode === 'year' && model.year) {
        color = getYearColor(model.year)
      } else if (viewMode === 'community' && communityData?.communities) {
        const community = communityData.communities.find(c => c.nodes?.includes(model.id))
        if (community) {
          color = COMMUNITY_COLORS[communityData.communities.indexOf(community) % COMMUNITY_COLORS.length]
        }
      } else if (viewMode === 'degree') {
        const degree = graphData.edges?.filter(
          e => e.source === model.id || e.target === model.id
        ).length || 0
        const intensity = Math.min(degree / 10, 1)
        color = `hsl(210, 80%, ${20 + intensity * 40}%)`
      }

      graph.updateItem(node, {
        style: { fill: color, stroke: color }
      })
    })
  }

  // 初始化图谱
  useEffect(() => {
    if (!containerRef.current || graphData?.nodes?.length === 0) return

    // 销毁旧图谱
    if (graphRef.current) {
      graphRef.current.destroy()
    }

    const container = containerRef.current
    const width = container.offsetWidth
    const height = container.offsetHeight || 600

    // 创建图谱实例
    const graph = new G6.Graph({
      container: container,
      width,
      height,
      fitView: true,
      fitViewPadding: 50,
      animate: true,
      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node']
      },
      defaultNode: {
        size: 30,
        style: {
          fill: '#1890ff',
          stroke: '#1890ff',
          lineWidth: 2,
          cursor: 'pointer'
        },
        labelCfg: {
          position: 'bottom',
          offset: 5,
          style: {
            fontSize: 10,
            fill: '#333'
          }
        }
      },
      defaultEdge: {
        style: {
          stroke: '#e0e0e0',
          lineWidth: 1,
          endArrow: false
        }
      },
      layout: {
        type: 'force-directed',
        preventOverlap: true,
        nodeSpacing: 20,
        linkDistance: 150,
        nodeStrength: -800,
        edgeStrength: 0.3
      }
    })

    // 绑定事件
    graph.on('node:mouseenter', (evt) => {
      const { item } = evt
      const model = item.getModel()
      if (onNodeHover) onNodeHover(model)
    })

    graph.on('node:mouseleave', () => {
      if (onNodeHover) onNodeHover(null)
    })

    graph.on('node:click', (evt) => {
      const { item } = evt
      const model = item.getModel()
      if (onNodeClick) onNodeClick(model)
    })

    graph.on('wheel', (evt) => {
      evt.preventDefault()
    })

    // 渲染数据
    graph.data(graphData)
    graph.render()

    // 保存引用
    graphRef.current = graph

    // 更新样式
    setTimeout(updateNodeStyles, 500)

    // 窗口调整
    const handleResize = () => {
      if (graph && container) {
        graph.changeSize(container.offsetWidth, container.offsetHeight || 600)
        graph.fitView()
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (graphRef.current) {
        graphRef.current.destroy()
        graphRef.current = null
      }
    }
  }, [graphData])

  // 更新视图模式
  useEffect(() => {
    updateNodeStyles()
  }, [viewMode, communityData])

  // 应用缩放
  useEffect(() => {
    if (graphRef.current && zoomLevel) {
      graphRef.current.zoomTo(zoomLevel)
    }
  }, [zoomLevel])

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '500px',
        background: '#fafafa'
      }}
    />
  )
})

GraphVisualization.displayName = 'GraphVisualization'

export default GraphVisualization
