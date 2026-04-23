import { useEffect, useRef, useState } from 'react'
import { GitBranch } from 'lucide-react'
import cytoscape from 'cytoscape'
import { api } from '@/services/api'
import type { KnowledgeGraph as KG } from '@/types'

export default function GraphPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<{ id: string; label: string; type: string } | null>(null)

  useEffect(() => {
    api.getKnowledgeGraph().then((data: KG) => {
      if (!containerRef.current) return

      const elements = [
        ...data.nodes.map((n) => ({
          data: { id: n.id, label: n.label, type: n.type, weight: n.weight },
        })),
        ...data.edges.map((e) => ({
          data: { source: e.source, target: e.target, relation: e.relation, weight: e.weight },
        })),
      ]

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              'font-size': 11,
              'text-wrap': 'wrap',
              'text-max-width': 80,
              'background-color': (ele) => {
                const t = ele.data('type')
                return t === 'concept' ? '#3b82f6' : t === 'method' ? '#8b5cf6' : t === 'dataset' ? '#10b981' : '#f59e0b'
              },
              width: (ele) => 20 + (ele.data('weight') ?? 1) * 8,
              height: (ele) => 20 + (ele.data('weight') ?? 1) * 8,
              'text-valign': 'bottom',
              'text-margin-y': 4,
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1,
              'line-color': '#94a3b8',
              'curve-style': 'bezier',
              label: 'data(relation)',
              'font-size': 8,
              'text-rotation': 'autorotate',
              'text-opacity': 0.6,
            },
          },
        ],
        layout: { name: 'cose', animate: true, padding: 40 } as any,
      })

      cy.on('tap', 'node', (e) => {
        const node = e.target
        setSelected({ id: node.id(), label: node.data('label'), type: node.data('type') })
      })

      cyRef.current = cy
      setLoading(false)
    })
    return () => cyRef.current?.destroy()
  }, [])

  return (
    <div className="flex h-full">
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-900/60 z-10 text-gray-400">
            加载知识图谱…
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* detail panel */}
      {selected && (
        <aside className="w-64 border-l border-gray-200 dark:border-gray-700 p-4 text-sm space-y-3">
          <h3 className="font-semibold flex items-center gap-2"><GitBranch size={16} /> 节点详情</h3>
          <div><span className="text-gray-400">名称：</span>{selected.label}</div>
          <div><span className="text-gray-400">类型：</span>{selected.type}</div>
          <button onClick={() => setSelected(null)} className="text-xs text-brand-600 hover:underline">关闭</button>
        </aside>
      )}
    </div>
  )
}
