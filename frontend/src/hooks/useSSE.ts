import { useRef } from 'react'
import { useChatStore } from '@/stores/chat'

const TIMEOUT = 120000
const MAX_RETRIES = 1

export function useSSE() {
  const abortRef = useRef<AbortController | null>(null)
  const lastQuestion = useRef('')
  const store = useChatStore()

  async function sendMessage(content: string) {
    lastQuestion.current = content
    store.addMessage({ role: 'user', content })
    store.addMessage({ role: 'assistant', content: '' })
    useChatStore.setState({ streaming: true })
    let retries = 0
    while (retries <= MAX_RETRIES) {
      abortRef.current = new AbortController()
      const timer = window.setTimeout(() => abortRef.current?.abort(), TIMEOUT)
      try {
        const response = await fetch('/api/chat/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ conversation_id: useChatStore.getState().currentId, message: content }), signal: abortRef.current.signal })
        window.clearTimeout(timer)
        if (!response.ok) {
          if (response.status >= 500 && retries < MAX_RETRIES) { retries++; continue }
          throw new Error(`请求失败 (${response.status})`)
        }
        const conversationId = response.headers.get('X-Conversation-Id')
        if (conversationId) useChatStore.setState({ currentId: conversationId })
        const reader = response.body?.getReader()
        if (!reader) throw new Error('响应流不可用')
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try { const data = JSON.parse(line.slice(6)); if (!data.done) useChatStore.getState().updateLastMessage(data.content || '') } catch { /* ignore malformed chunks */ }
          }
        }
        useChatStore.setState({ streaming: false })
        await useChatStore.getState().loadConversations()
        return
      } catch (error) {
        window.clearTimeout(timer)
        if (error instanceof DOMException && error.name === 'AbortError') { useChatStore.setState({ streaming: false }); useChatStore.getState().updateLastMessage('\n\n> 请求已取消或超时'); return }
        if (retries >= MAX_RETRIES) { useChatStore.setState({ streaming: false }); useChatStore.getState().updateLastMessage(`\n\n> ${error instanceof Error ? error.message : '网络连接失败'}，请稍后重试`); return }
      }
    }
  }

  return { sendMessage, stopStreaming: () => { abortRef.current?.abort(); useChatStore.setState({ streaming: false }) }, retry: () => lastQuestion.current && sendMessage(lastQuestion.current) }
}
