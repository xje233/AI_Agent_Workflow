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
  conversation_id?: string
  message: string
}
