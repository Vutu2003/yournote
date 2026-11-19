export interface HealthResponse {
  status: 'ok'
}

export interface Locator { kind: 'page' | 'paragraph'; page?: number | null; anchor?: string | null; paragraph?: number | null; heading?: string[] }
export interface DocumentInfo {
  schema_version?: number
  kind?: 'pdf' | 'docx' | 'markdown' | 'text'
  original_filename?: string | null
  document_version?: string | null
  anchor_count?: number
  warnings?: string[]
  filename: string
  document_id: string
  pages: number[]
  page_count: number
  chunk_count: number
}
export interface DocumentsResponse { documents: DocumentInfo[] }
export interface UploadResponse { filename: string; chunks_indexed: number; document_id?: string; document_version?: string; original_filename?: string; deduplicated?: boolean; warnings?: string[] }
export interface Citation {
  schema_version?: number
  document_id?: string | null
  document_version?: string | null
  locator?: Locator | null
  source_index: number
  source_marker: string
  filename: string
  page: number | null
  source_text?: string | null
  section?: string | null
  chunk_id?: string | null
}
export interface SourceSelection { filenames: string[]; pages?: number[]; document_versions?: Record<string, string> }
export interface ChatRequest extends SourceSelection { question: string; k?: number }
export interface SelectedPassage {
  document_id: string
  filename: string
  document_version: string
  page: number
  text: string
}
export interface ChatContext {
  mode: 'reading'
  scope: 'document' | 'notebook'
  filenames: string[]
  selection: SelectedPassage | null
}
export type ReasoningEffort = 'none' | 'minimal' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'
export interface ModelChoice { provider: 'gemini' | 'chatgpt'; model: string; connection_id: string | null; reasoning_effort?: ReasoningEffort | null }
export interface GenerationMetadata {
  reasoning_effort?: ReasoningEffort | null
  provider: 'gemini' | 'chatgpt'; requested_model: string; model: string | null; actual_models: string[]
  created_at: string; status: 'completed'; request_id: string; notebook_id: string
  source_versions?: Record<string, string>
  source_filenames: string[]; pages: number[]; calls: number; duration_seconds: number
  usage: { input_tokens: number | null; output_tokens: number | null; total_tokens: number | null } | null
}
export interface RetrievalTrace { method: string; query_sha256: string; chunk_ids: string[]; context_count: number; duration_ms: number; history_turns: number }
export interface ChatResponse { retrieval_trace?: RetrievalTrace | null; question: string; answer: string; citations: Citation[]; context?: ChatContext | null; generation?: GenerationMetadata | null }
export interface SummaryRequest extends SourceSelection { topic?: string | null; k?: number | null }
export interface LearningResponse {
  generation?: GenerationMetadata | null
  scope: 'query' | 'document' | 'filter' | 'corpus'
  target?: string | null
  citations: Citation[]
}
export interface SummaryResponse extends LearningResponse { summary: string; key_points: string[] }
export interface MindMapNode {
  label: string
  description: string
  source_markers: string[]
  children: MindMapNode[]
}
export interface MindMapResponse extends LearningResponse { root: MindMapNode }
export interface QuizItem {
  question: string
  options: [string, string, string, string]
  correct_index: number
  explanation: string
  source_markers: string[]
  difficulty?: string | null
  topic?: string | null
}
export interface QuizRequest extends SummaryRequest { count?: number }
export interface QuizResponse extends LearningResponse { items: QuizItem[] }
export interface Flashcard {
  front: string
  back: string
  hint?: string | null
  topic?: string | null
  source_markers: string[]
}
export interface FlashcardsRequest extends SummaryRequest { count?: number }
export interface FlashcardsResponse extends LearningResponse { cards: Flashcard[] }
export interface ValidationIssue { loc: (string | number)[]; msg: string; type: string }
export interface APIErrorResponse { detail: string | ValidationIssue[] }
export interface ExportResults {
  chat: ChatResponse
  summary: SummaryResponse
  quiz: QuizResponse
  flashcards: FlashcardsResponse
  mindmap: MindMapResponse
  comparison: import('./research').ComparisonResponse
  report: import('./research').ReportResponse
  graph: import('./research').GraphResponse
}
export type ExportFeature = keyof ExportResults
export type LegacyGenerationTool = 'summary' | 'quiz' | 'flashcards' | 'mindmap'
export type GenerationTool = Exclude<ExportFeature, 'chat'>
export type StudioTool = GenerationTool | 'notes'
