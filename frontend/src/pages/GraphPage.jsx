import { useState, useEffect, useRef, useCallback } from 'react'
import { Network, Search, ZoomIn, ZoomOut, RotateCcw, MessageSquare, Lightbulb } from 'lucide-react'
import useStore from '../stores/useStore'
import { api } from '../api/client'
import styles from './GraphPage.module.css'

const NODE_COLORS = {
  Paper: '#4a9eff',
  Method: '#e8a838',
  Topic: '#3dd68c',
  Finding: '#a78bfa',
  Gap: '#ff6b6b',
  Limitation: '#f59e42',
  Dataset: '#38bdf8',
  InnovationPoint: '#f472b6',
}

export default function GraphPage() {
  const graph = useStore((s) => s.graph)
  const setGraph = useStore((s) => s.setGraph)
  const selectedNodeIds = useStore((s) => s.selectedNodeIds)
  const toggleNodeSelection = useStore((s) => s.toggleNodeSelection)
  const clearNodeSelection = useStore((s) => s.clearNodeSelection)
  const openDrawer = useStore((s) => s.openDrawer)

  const currentProject = useStore((s) => s.currentProject)
  const canvasRef = useRef(null)
  const svgRef = useRef(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [filterType, setFilterType] = useState('all')
  const [zoom, setZoom] = useState(1)
  const [building, setBuilding] = useState(false)

  useEffect(() => {
    if (!currentProject) return
    api.getGraph(currentProject.project_id)
      .then((res) => {
        const data = res.data || res
        if (data.nodes?.length > 0) setGraph(data)
      })
      .catch(() => {})
  }, [currentProject])

  // D3 force simulation
  useEffect(() => {
    if (!svgRef.current || graph.nodes.length === 0) return

    const d3 = require('d3')
    const svg = d3.select(svgRef.current)
    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight

    svg.selectAll('*').remove()

    const g = svg.append('g')

    // Zoom behavior
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
        setZoom(event.transform.k)
      })
    svg.call(zoomBehavior)

    // Filter nodes
    const filteredNodes = filterType === 'all'
      ? graph.nodes
      : graph.nodes.filter((n) => n.type === filterType)

    const filteredNodeIds = new Set(filteredNodes.map((n) => n.id))
    const filteredEdges = graph.edges.filter(
      (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    )

    // Simulation
    const simulation = d3.forceSimulation(filteredNodes)
      .force('link', d3.forceLink(filteredEdges).id((d) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30))

    // Edges
    const link = g.append('g')
      .selectAll('line')
      .data(filteredEdges)
      .join('line')
      .attr('stroke', '#1e2740')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)

    // Nodes
    const node = g.append('g')
      .selectAll('g')
      .data(filteredNodes)
      .join('g')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null; d.fy = null
        })
      )

    // Node circles
    node.append('circle')
      .attr('r', (d) => Math.max(8, Math.min(20, 6 + (d.connections || 1) * 1.2)))
      .attr('fill', (d) => NODE_COLORS[d.type] || '#4a9eff')
      .attr('fill-opacity', 0.85)
      .attr('stroke', (d) => NODE_COLORS[d.type] || '#4a9eff')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.3)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
        toggleNodeSelection(d.id)
      })
      .on('mouseenter', function(event, d) {
        d3.select(this)
          .transition().duration(150)
          .attr('r', Math.max(12, Math.min(26, 8 + (d.connections || 1) * 1.5)))
          .attr('fill-opacity', 1)
          .attr('stroke-opacity', 0.8)
      })
      .on('mouseleave', function(event, d) {
        d3.select(this)
          .transition().duration(150)
          .attr('r', Math.max(8, Math.min(20, 6 + (d.connections || 1) * 1.2)))
          .attr('fill-opacity', 0.85)
          .attr('stroke-opacity', 0.3)
      })

    // Labels
    node.append('text')
      .text((d) => d.label.length > 16 ? d.label.slice(0, 14) + '...' : d.label)
      .attr('dy', (d) => Math.max(8, Math.min(20, 6 + (d.connections || 1) * 1.2)) + 14)
      .attr('text-anchor', 'middle')
      .attr('fill', '#8b8a85')
      .attr('font-size', '10px')
      .attr('font-family', 'var(--font-body)')
      .style('pointer-events', 'none')

    // Type labels (on hover via CSS)
    node.append('title').text((d) => `${d.type}: ${d.label}`)

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)
      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    // Click background to deselect
    svg.on('click', () => {
      setSelectedNode(null)
      clearNodeSelection()
    })

    return () => simulation.stop()
  }, [graph, filterType])

  const handleZoomIn = () => {
    if (svgRef.current) {
      const d3 = require('d3')
      d3.select(svgRef.current).transition().duration(300).call(
        d3.zoom().scaleBy, 1.3
      )
    }
  }

  const handleZoomOut = () => {
    if (svgRef.current) {
      const d3 = require('d3')
      d3.select(svgRef.current).transition().duration(300).call(
        d3.zoom().scaleBy, 0.7
      )
    }
  }

  const handleReset = () => {
    if (svgRef.current) {
      const d3 = require('d3')
      d3.select(svgRef.current).transition().duration(500).call(
        d3.zoom().transform, d3.zoomIdentity
      )
    }
  }

  const nodeTypes = ['all', ...Object.keys(NODE_COLORS)]

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2 className={styles.pageTitle}>知识图谱</h2>
          <span className={styles.count}>{graph.nodes.length} 节点 · {graph.edges.length} 边</span>
        </div>
        <div className={styles.headerActions}>
          <button
            className="btn btn--secondary btn--sm"
            disabled={building || !currentProject}
            onClick={() => {
              if (!currentProject) return
              setBuilding(true)
              api.buildGraph(currentProject.project_id)
                .then(() => api.getGraph(currentProject.project_id))
                .then((res) => { const d = res.data || res; if (d.nodes) setGraph(d) })
                .catch(() => {})
                .finally(() => setBuilding(false))
            }}
          >
            <Network size={14} /> {building ? '构建中...' : '构建图谱'}
          </button>
          {selectedNodeIds.length > 0 && (
            <button className="btn btn--primary btn--sm" onClick={() => window.location.href = '/qa'}>
              <MessageSquare size={14} /> 基于子图QA ({selectedNodeIds.length})
            </button>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <div className={styles.toolbar}>
        <div className={styles.typeFilters}>
          {nodeTypes.map((type) => (
            <button
              key={type}
              className={`${styles.typeBtn} ${filterType === type ? styles.typeActive : ''}`}
              onClick={() => setFilterType(type)}
            >
              {type !== 'all' && (
                <span className={styles.typeDot} style={{ background: NODE_COLORS[type] }} />
              )}
              {type === 'all' ? '全部' : type}
            </button>
          ))}
        </div>

        <div className={styles.zoomControls}>
          <button className={styles.zoomBtn} onClick={handleZoomOut}><ZoomOut size={16} /></button>
          <span className={styles.zoomLevel}>{Math.round(zoom * 100)}%</span>
          <button className={styles.zoomBtn} onClick={handleZoomIn}><ZoomIn size={16} /></button>
          <button className={styles.zoomBtn} onClick={handleReset}><RotateCcw size={16} /></button>
        </div>
      </div>

      {/* Graph Canvas */}
      <div className={styles.canvasContainer} ref={canvasRef}>
        <svg ref={svgRef} className={styles.svg} />

        {/* Node Detail Panel */}
        {selectedNode && (
          <div className={styles.nodePanel}>
            <div className={styles.nodePanelHeader}>
              <span
                className={styles.nodeTypeBadge}
                style={{ background: NODE_COLORS[selectedNode.type], color: '#000' }}
              >
                {selectedNode.type}
              </span>
              <h3 className={styles.nodeTitle}>{selectedNode.label}</h3>
            </div>

            {selectedNode.year && (
              <p className={styles.nodeMeta}>年份: {selectedNode.year}</p>
            )}
            <p className={styles.nodeMeta}>连接数: {selectedNode.connections || 0}</p>

            <div className={styles.nodeActions}>
              <button
                className="btn btn--primary btn--sm"
                onClick={() => toggleNodeSelection(selectedNode.id)}
              >
                {selectedNodeIds.includes(selectedNode.id) ? '移出子图' : '加入子图'}
              </button>
              <button className="btn btn--secondary btn--sm">
                <Lightbulb size={14} /> 基于此QA
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selection Bar */}
      {selectedNodeIds.length > 0 && (
        <div className={styles.selectionBar}>
          <span>选中子图: {selectedNodeIds.length} 个节点</span>
          <button className="btn btn--ghost btn--sm" onClick={clearNodeSelection}>清空</button>
          <button className="btn btn--primary btn--sm" onClick={() => window.location.href = '/qa'}>
            基于子图QA
          </button>
        </div>
      )}
    </div>
  )
}
