import type { LearningResponse } from './api'
export type ResearchTool = 'comparison' | 'report' | 'graph'
export interface EvidenceRef { source_marker: string; quote: string }
export interface GroundedStatement { text: string; evidence: EvidenceRef[] }
export interface SourceCoverage { filename: string; document_id: string; document_version: string; total_chunks: number; examined_chunk_ids: string[]; coverage: 'complete' | 'selected_excerpt' }
export interface ResearchResult extends LearningResponse {
  schema_version: 1; goal: string; sources: SourceCoverage[]; limits: string[]
  source_notes: { filename: string; status: 'evidence' | 'not_found'; detail: string }[]
}
export interface SourceCriterion { filename: string; criterion_id: string; status: 'supported' | 'not_found'; statement: GroundedStatement | null; limitation: string }
export interface ComparisonResponse extends ResearchResult {
  kind: 'comparison'
  criteria: { id: string; label: string; sources: SourceCriterion[] }[]
  findings: { criterion_id: string; kind: 'agreement' | 'direct_conflict' | 'different_conditions' | 'different_wording' | 'difference'; statement: GroundedStatement }[]
  conclusion: GroundedStatement[]
}
export type ReportMode = 'study_guide' | 'explanation' | 'synthesis'
export interface ReportResponse extends ResearchResult {
  kind: 'report'; mode: ReportMode; title: string
  sections: { title: string; statements: GroundedStatement[] }[]
  conclusion: GroundedStatement[]
}
export interface TaskProgress { stage: string; completed_steps?: number; total_steps?: number; source_count?: number; chunk_count?: number; planned_calls?: number; calls?: number }
export const findingLabels = { agreement: 'Thống nhất', direct_conflict: 'Mâu thuẫn trực tiếp', different_conditions: 'Khác điều kiện / phạm vi', different_wording: 'Khác cách diễn đạt', difference: 'Khác biệt' }

export type Relation = 'is_a' | 'part_of' | 'requires' | 'causes' | 'contrasts_with' | 'related_to' | 'example_of' | 'equivalent_to' | 'optimizes' | 'measures' | 'predicts' | 'uses'
export const relationLabels: Record<Relation, string> = { is_a: 'là một dạng', part_of: 'là thành phần của', requires: 'cần', causes: 'dẫn đến', contrasts_with: 'tương phản với', related_to: 'liên quan đến', example_of: 'là ví dụ của', equivalent_to: 'tương đương với', optimizes: 'tối ưu', measures: 'đo lường', predicts: 'dự đoán', uses: 'sử dụng' }
export interface GraphNode { id: string; label: string; meaning_key: string; aliases: string[]; definition: GroundedStatement }
export interface GraphEdge { id: string; source: string; target: string; relation: Relation; statement: GroundedStatement }
export interface GraphResponse extends ResearchResult { kind: 'graph'; nodes: GraphNode[]; edges: GraphEdge[]; discarded_relations: number; merge_policy: 'same_meaning_and_documented_name' }
