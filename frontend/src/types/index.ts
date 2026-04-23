// ─── Domain types ────────────────────────────────────────────────────────────

export type ResearchStatus =
  | 'idle'
  | 'planning'
  | 'searching'
  | 'reading'
  | 'analysing'
  | 'writing'
  | 'reviewing'
  | 'done'
  | 'error'

export interface Paper {
  id: string
  title: string
  authors: string[]
  year: number
  abstract: string
  url?: string
  pdf_url?: string
  source: 'arxiv' | 'semantic_scholar' | 'local'
  relevance_score?: number
  citations?: number
  themes?: string[]
  key_contributions?: string[]
  methods?: string[]
}

export interface AgentEvent {
  type:
    | 'status'
    | 'paper_found'
    | 'paper_read'
    | 'analysis_update'
    | 'writing_update'
    | 'error'
    | 'done'
  agent: string
  message: string
  data?: unknown
  timestamp: string
}

export interface ResearchTask {
  task_id: string
  query: string
  status: ResearchStatus
  created_at: string
  papers: Paper[]
  report?: string
  error?: string
}

export interface Theme {
  id: string
  label: string
  paper_ids: string[]
  summary: string
}

export interface KnowledgeNode {
  id: string
  label: string
  type: 'concept' | 'method' | 'dataset' | 'paper'
  weight: number
}

export interface KnowledgeEdge {
  source: string
  target: string
  relation: string
  weight: number
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}

export interface Report {
  id: string
  task_id: string
  query: string
  content: string
  created_at: string
  paper_count: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: Paper[]
}
