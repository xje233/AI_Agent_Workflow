import { create } from 'zustand'
import { chatApi } from '@/api/chat'
import type { Conversation, Message } from '@/types/chat'

interface ChatState {
  conversations: Conversation[]
  currentId: string | null
  messages: Message[]
  streaming: boolean
  tokenCount: number
  loadConversations: () => Promise<void>
  loadMessages: (id: string) => Promise<void>
  newConversation: () => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  addMessage: (message: Message) => void
  updateLastMessage: (content: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [], currentId: null, messages: [], streaming: false, tokenCount: 0,
  loadConversations: async () => set({ conversations: await chatApi.getConversations() }),
  loadMessages: async (id) => {
    const result = await chatApi.getMessages(id)
    set({ currentId: id, messages: result.messages })
  },
  newConversation: async () => {
    const result = await chatApi.newConversation()
    set({ currentId: result.conversation_id, messages: [] })
    await get().loadConversations()
  },
  deleteConversation: async (id) => {
    await chatApi.deleteConversation(id)
    set((state) => ({ currentId: state.currentId === id ? null : state.currentId, messages: state.currentId === id ? [] : state.messages }))
    await get().loadConversations()
  },
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (content) => set((state) => {
    const messages = [...state.messages]
    const last = messages[messages.length - 1]
    if (last?.role === 'assistant') messages[messages.length - 1] = { ...last, content: last.content + content }
    return { messages }
  }),
}))
