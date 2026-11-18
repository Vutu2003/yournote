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
