export interface KnowledgeDocument {
  id: string
  filename: string
  file_type: string
  vector_status: 'pending' | 'indexing' | 'completed' | 'failed'
  created_at: string
}
