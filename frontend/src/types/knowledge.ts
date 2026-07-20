// 知识库领域类型：描述文件元数据和后端返回的索引状态。
export interface KnowledgeDocument {
  id: string
  filename: string
  file_type: string
  vector_status: 'pending' | 'indexing' | 'completed' | 'failed'
  created_at: string
}
