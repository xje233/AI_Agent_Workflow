import request from './request'
import type { KnowledgeDocument } from '@/types/knowledge'

export const knowledgeApi = {
  upload(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<KnowledgeDocument>('/knowledge/upload', formData) as unknown as Promise<KnowledgeDocument>
  },
  getDocuments: () => request.get<KnowledgeDocument[]>('/knowledge/documents') as unknown as Promise<KnowledgeDocument[]>,
  deleteDocument: (id: string) => request.delete(`/knowledge/documents/${id}`),
}
