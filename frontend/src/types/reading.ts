import type { SelectedPassage } from './api'

export interface ReadingDocument {
  document_id: string
  filename: string
  document_version: string
  page_count: number
}
export interface ReadingChatInput {
  notebookId: string
  document_id: string
  scope: 'document' | 'notebook'
  selection?: SelectedPassage | null
}
export interface PdfTarget { page: number; token: number; text?: string | null }
