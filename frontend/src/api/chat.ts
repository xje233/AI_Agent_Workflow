// 聊天 API：封装会话管理和历史消息读取请求。
import request from './request'
import type { Conversation, Message } from '@/types/chat'

export const chatApi = {
  getConversations: () => request.get<Conversation[]>('/conversations') as unknown as Promise<Conversation[]>,
  getMessages: (id: string) => request.get<{ messages: Message[] }>(`/conversations/${id}/messages`) as unknown as Promise<{ messages: Message[] }>,
  deleteConversation: (id: string) => request.delete(`/conversations/${id}`),
  newConversation: () => request.post<{ conversation_id: string }>('/chat/new') as unknown as Promise<{ conversation_id: string }>,
}
