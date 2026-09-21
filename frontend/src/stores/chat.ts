import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatApi } from '@/api/chat'
import type { Message, Conversation } from '@/types/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const streaming = ref(false)
  const tokenCount = ref(0)

  async function loadConversations() {
    conversations.value = await chatApi.getConversations()
  }

  async function loadMessages(convId: string) {
    currentId.value = convId
    const res = await chatApi.getMessages(convId)
    messages.value = res.messages
  }

  async function newConversation() {
    const res = await chatApi.newConversation()
    currentId.value = res.conversation_id
    messages.value = []
    await loadConversations()
  }

  async function deleteConversation(convId: string) {
    await chatApi.deleteConversation(convId)
    if (currentId.value === convId) {
      currentId.value = null
      messages.value = []
    }
    await loadConversations()
  }

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  function updateLastMessage(content: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += content
    }
  }

  return {
    conversations, currentId, messages, streaming, tokenCount,
    loadConversations, loadMessages, newConversation, deleteConversation,
    addMessage, updateLastMessage,
  }
})
