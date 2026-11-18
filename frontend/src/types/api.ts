export interface HealthResponse {
  status: 'ok'
}

export interface DocumentInfo {
  filename: string
  document_id: string
  pages: number[]
  page_count: number
  chunk_count: number
}
export interface DocumentsResponse { documents: DocumentInfo[] }
export interface UploadResponse { filename: string; chunks_indexed: number }
export interface Citation {
  source_index: number
  source_marker: string
  filename: string
  page: number
  source_text?: string | null
  section?: string | null
  chunk_id?: string | null
}
export interface SourceSelection { filenames: string[]; pages?: number[] }
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
export interface ChatResponse { question: string; answer: string; citations: Citation[]; context?: ChatContext | null }
export interface SummaryRequest extends SourceSelection { topic?: string | null; k?: number | null }
export interface LearningResponse {
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
}
export type ExportFeature = keyof ExportResults
export type GenerationTool = Exclude<ExportFeature, 'chat'>
export type StudioTool = GenerationTool | 'notes'
