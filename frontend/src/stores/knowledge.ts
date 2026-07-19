import { create } from 'zustand'
import { knowledgeApi } from '@/api/knowledge'
import type { KnowledgeDocument } from '@/types/knowledge'

interface KnowledgeState {
  documents: KnowledgeDocument[]
  uploading: boolean
  loadDocuments: () => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  deleteDocument: (id: string) => Promise<void>
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  documents: [], uploading: false,
  loadDocuments: async () => set({ documents: await knowledgeApi.getDocuments() }),
  uploadDocument: async (file) => {
    set({ uploading: true })
    try { await knowledgeApi.upload(file); await get().loadDocuments() } finally { set({ uploading: false }) }
  },
  deleteDocument: async (id) => { await knowledgeApi.deleteDocument(id); await get().loadDocuments() },
}))
