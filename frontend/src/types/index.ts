export interface Source {
  title: string
  url: string
  snippet: string
  score?: number
  source_score?: number
  quality_score?: number
  quality_label?: 'high' | 'medium' | 'low'
  source_type?: string
  source_type_label?: string
  citation_index?: number
}

export interface CitationAudit {
  has_citations: boolean
  invalid_citations: number[]
  valid: boolean
  source_count: number
}

export type PipelineStage = 'search' | 'process' | 'rag' | 'answer' | 'audit'
export type PipelineStatus = 'pending' | 'running' | 'done'

export interface PipelineStep {
  stage: PipelineStage
  label: string
  status: PipelineStatus
  duration_ms?: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  followUps?: string[]
}

export interface Conversation {
  id: string
  share_id: string
  title: string
  created_at: string
  is_favorite: boolean
  messages?: Message[]
}

export interface SearchRequest {
  query: string
  conversation_id?: string
}
