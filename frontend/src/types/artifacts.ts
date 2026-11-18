import type { FlashcardsResponse, QuizResponse, SourceSelection, SummaryResponse, MindMapResponse } from './api'

export interface StudioArtifact<T> {
  id: string
  title: string
  createdAt: number
  sourceFilenames: string[]
  pages: number[]
  topic: string | null
  result: T
}

export type SummaryArtifact = StudioArtifact<SummaryResponse>
export type QuizArtifact = StudioArtifact<QuizResponse>
export type FlashcardArtifact = StudioArtifact<FlashcardsResponse>
export type MindMapArtifact = StudioArtifact<MindMapResponse>

export function createArtifact<T>(result: T, context: SourceSelection & { topic: string | null }): StudioArtifact<T> {
  const firstTitle = context.filenames[0].replace(/\.pdf$/i, '')
  return {
    id: crypto.randomUUID(),
    title: context.filenames.length === 1 ? firstTitle : `${firstTitle} +${context.filenames.length - 1}`,
    createdAt: Date.now(),
    sourceFilenames: [...context.filenames],
    pages: [...(context.pages || [])],
    topic: context.topic,
    result,
  }
}
