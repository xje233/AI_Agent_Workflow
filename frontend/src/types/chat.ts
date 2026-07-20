// 聊天领域类型：描述消息和会话在接口、状态与组件间的共享结构。
export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface Conversation {
  id: string
  title: string
  created_at: string
}

export interface ChatRequest {
  conversation_id?: string | null
  message: string
}
