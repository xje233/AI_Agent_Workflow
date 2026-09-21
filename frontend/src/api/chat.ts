import request from './request'
import type { Conversation, Message } from '@/types/chat'

export const chatApi = {
  getConversations(): Promise<Conversation[]> {
    return request.get('/conversations') as any
  },

  getMessages(conversationId: string): Promise<{ messages: Message[] }> {
    return request.get(`/conversations/${conversationId}/messages`) as any
  },

  deleteConversation(conversationId: string): Promise<any> {
    return request.delete(`/conversations/${conversationId}`)
  },

  newConversation(): Promise<{ conversation_id: string }> {
    return request.post('/chat/new')
  },
}
