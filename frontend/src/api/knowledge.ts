import request from './request'
import type { KnowledgeDocument } from '@/types/knowledge'

export const knowledgeApi = {
  upload(file: File): Promise<KnowledgeDocument> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }) as any
  },

  getDocuments(): Promise<KnowledgeDocument[]> {
    return request.get('/knowledge/documents') as any
  },

  deleteDocument(docId: string): Promise<any> {
    return request.delete(`/knowledge/documents/${docId}`)
  },
}
