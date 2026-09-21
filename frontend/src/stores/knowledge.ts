import { defineStore } from 'pinia'
import { ref } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import type { KnowledgeDocument } from '@/types/knowledge'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref<KnowledgeDocument[]>([])
  const uploading = ref(false)

  async function loadDocuments() {
    documents.value = await knowledgeApi.getDocuments()
  }

  async function uploadDocument(file: File) {
    uploading.value = true
    try {
      await knowledgeApi.upload(file)
      await loadDocuments()
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(docId: string) {
    await knowledgeApi.deleteDocument(docId)
    await loadDocuments()
  }

  return { documents, uploading, loadDocuments, uploadDocument, deleteDocument }
})
