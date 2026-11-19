import type { SelectedPassage, Locator } from './api'

export interface ReadingDocument {
  kind?: 'pdf' | 'docx' | 'markdown' | 'text'
  original_filename?: string | null
  historical?: boolean
  document_id: string
  filename: string
  document_version: string
  page_count: number
}
export interface ReadingChatInput {
  document_version?: string | null
  notebookId: string
  document_id: string
  scope: 'document' | 'notebook'
  selection?: SelectedPassage | null
}
export interface PdfTarget { page: number; token: number; text?: string | null; anchor?: string | null; version?: string | null }
export interface TextDocument extends ReadingDocument { blocks: { text: string; locator: Locator }[] }
export interface CitationResolution { document: ReadingDocument; locator: Locator }
