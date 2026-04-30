/**
 * 自定义 hook：知识图谱数据管理
 *
 * 负责图谱数据的加载、生成、社区检测等逻辑。
 */
import { useState, useCallback, useRef } from 'react'
import { knowledgeGraphAPI, literatureAPI } from '../services/api'
import { useLiteratureStore } from '../store/literatureStore'

export const useGraphData = () => {
  const [graphLoading, setGraphLoading] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], stats: {} })
  const [communityData, setCommunityData] = useState({ communities: [], stats: {} })
  const { literature, addLiterature } = useLiteratureStore()
  const hasLoadedFromLiterature = useRef(false)

  const generateFromLiteratureData = (litData) => {
    const nodes = litData.map((paper, idx) => ({
      id: paper.id || `paper_${idx}`,
      label: paper.title || `Paper ${idx + 1}`,
      title: paper.title || '',
      type: 'paper',
      year: paper.year || 0,
      citations: paper.citations || 0,
      authors: paper.authors || '',
      abstract: paper.abstract || '',
      venue: paper.journal || '',
      url: paper.url || '',
      isTarget: idx === 0,
    }))

    const edges = []
    for (let i = 0; i < litData.length; i++) {
      for (let j = i + 1; j < litData.length; j++) {
        const p1 = litData[i]
        const p2 = litData[j]
        const authors1 = Array.isArray(p1.authors) ? p1.authors : (typeof p1.authors === 'string' ? p1.authors.split(',').map(a => a.trim()) : [])
        const authors2 = Array.isArray(p2.authors) ? p2.authors : (typeof p2.authors === 'string' ? p2.authors.split(',').map(a => a.trim()) : [])
        const hasCommonAuthor = authors1.some(a1 => authors2.some(a2 => a1.toLowerCase() === a2.toLowerCase()))
        const sameYear = p1.year === p2.year

        if (hasCommonAuthor || sameYear) {
          edges.push({
            source: nodes[i].id,
            target: nodes[j].id,
            relation: hasCommonAuthor ? '共同作者' : '同年发表',
            weight: hasCommonAuthor ? 0.8 : 0.3,
          })
        }
      }
    }

    return { nodes, edges, stats: { totalNodes: nodes.length, totalEdges: edges.length } }
  }

  const loadGraphFromLiterature = useCallback(async () => {
    if (literature.length === 0) return
    setGraphLoading(true)
    try {
      try {
        const response = await knowledgeGraphAPI.getLiteratureGraph(literature)
        if (response.success && response.data?.nodes?.length > 0) {
          setGraphData(response.data)
          return
        }
      } catch (e) {
        // API 不可用时使用本地数据
      }
      const localData = generateFromLiteratureData(literature)
      setGraphData(localData)
    } finally {
      setGraphLoading(false)
    }
  }, [literature])

  const loadGraphData = useCallback(async () => {
    setGraphLoading(true)
    try {
      if (literature.length > 0) {
        await loadGraphFromLiterature()
      }
    } finally {
      setGraphLoading(false)
    }
  }, [loadGraphFromLiterature, literature])

  const handleBuildFromLiterature = useCallback(async (paperId) => {
    const paper = literature.find(p => p.id === paperId)
    if (!paper) return

    setGraphLoading(true)
    try {
      let realCitations = paper.citations || 0
      try {
        const searchResult = await literatureAPI.search(paper.title, { max_results: 5 })
        if (searchResult.data) {
          const matchedPaper = searchResult.data.find(p =>
            p.title?.toLowerCase() === paper.title?.toLowerCase()
          )
          if (matchedPaper?.citations) {
            realCitations = matchedPaper.citations
          }
        }
      } catch (e) { /* ignore */ }

      const paperAuthors = Array.isArray(paper.authors)
        ? paper.authors
        : (typeof paper.authors === 'string' ? paper.authors.split(',').map(a => a.trim()) : [])

      const relatedPapers = literature.filter(p => {
        if (p.id === paper.id) return false
        const pAuthors = Array.isArray(p.authors)
          ? p.authors
          : (typeof p.authors === 'string' ? p.authors.split(',').map(a => a.trim()) : [])
        const hasCommonAuthor = paperAuthors.some(a1 => pAuthors.some(a2 => a1.toLowerCase() === a2.toLowerCase()))
        const similarYear = Math.abs((paper.year || 2020) - (p.year || 2020)) <= 2
        return hasCommonAuthor || similarYear
      })

      const paperWithCitations = { ...paper, citations: realCitations }
      const graphPapers = [paperWithCitations, ...relatedPapers]
      const localData = generateFromLiteratureData(graphPapers)
      setGraphData(localData)
    } finally {
      setGraphLoading(false)
    }
  }, [literature])

  const handleBuildGraph = useCallback(async (value) => {
    setGraphLoading(true)
    try {
      const targetPaper = {
        id: 'target_paper',
        title: value,
        type: 'paper',
        year: new Date().getFullYear(),
        citations: 100,
        isTarget: true,
      }
      // 生成基于目标论文的图谱数据
      const papers = [targetPaper]
      const nodes = papers.map((p, idx) => ({
        id: p.id || `paper_${idx}`,
        label: p.title,
        ...p,
      }))
      const edges = []
      setGraphData({ nodes, edges, stats: { totalNodes: nodes.length, totalEdges: edges.length } })
    } finally {
      setGraphLoading(false)
    }
  }, [])

  const handleGraphQuery = useCallback(async (queryText, setQueryResult, setQueryLoading) => {
    if (!queryText.trim()) return
    setQueryLoading(true)
    try {
      const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
      const response = await fetch('/api/knowledge-graph/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
        body: JSON.stringify({ query: queryText }),
      })
      const data = await response.json()
      if (data.success) {
        setQueryResult(data.data?.answer || data.data || '无结果')
      } else {
        setQueryResult('查询失败: ' + (data.error || '未知错误'))
      }
    } catch (error) {
      setQueryResult('查询失败: ' + error.message)
    } finally {
      setQueryLoading(false)
    }
  }, [])

  const detectCommunities = useCallback(async () => {
    try {
      const apiKey = localStorage.getItem('api_key') || 'dev-api-key'
      const response = await fetch('/api/knowledge-graph/communities?algorithm=leiden', {
        headers: { 'x-api-key': apiKey },
      })
      const data = await response.json()
      if (data.success) {
        setCommunityData(data.data || data)
      }
    } catch (error) {
      /* ignore */
    }
  }, [])

  return {
    graphLoading,
    graphData,
    setGraphData,
    communityData,
    loadGraphFromLiterature,
    loadGraphData,
    handleBuildFromLiterature,
    handleBuildGraph,
    handleGraphQuery,
    detectCommunities,
    hasLoadedFromLiterature,
  }
}
