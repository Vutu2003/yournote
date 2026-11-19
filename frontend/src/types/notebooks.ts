import type { ComparisonResponse, ReportResponse, GraphResponse } from './research'
import type { StudioArtifact } from './artifacts'
import type { ChatResponse, StudioTool } from './api'
import type { FlashcardArtifact, QuizArtifact, SummaryArtifact, MindMapArtifact } from './artifacts'

export interface UserNote {
  id: string
  title: string
  content: string
  createdAt: number
  updatedAt: number
}

export interface WorkspaceSnapshot {
  schema_version?: 1 | 2 | 3
  document_filenames: string[]
  source_names: Record<string, string>
  selected: string[]
  read_documents: string[]
  notes: UserNote[]
  page: string
  active_tool: StudioTool
  chat: ChatResponse[]
  summary_artifacts: SummaryArtifact[]
  quiz_artifacts: QuizArtifact[]
  flashcard_artifacts: FlashcardArtifact[]
  mindmap_artifacts: MindMapArtifact[]
  comparison_artifacts?: StudioArtifact<ComparisonResponse>[]
  report_artifacts?: StudioArtifact<ReportResponse>[]
  graph_artifacts?: StudioArtifact<GraphResponse>[]
}

export interface NotebookInfo {
  id: string
  title: string
  icon: string
  created_at: string
  updated_at: string
  source_count: number
  chat_count: number
}

export interface Notebook extends NotebookInfo { state: WorkspaceSnapshot }
export interface NotebookUpdate { title: string; icon: string; state: WorkspaceSnapshot }
