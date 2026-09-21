import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const SSE_TIMEOUT_MS = 120_000   // 2分钟超时
const MAX_RETRIES = 1             // 最多重试1次

export function useSSE() {
  const store = useChatStore()
  const abortController = ref<AbortController | null>(null)
  const lastQuestion = ref('')

  function _errorLabel(status: number): string {
    if (status === 500) return '服务器内部错误'
    if (status === 502 || status === 503) return '服务暂时不可用'
    if (status === 504) return '请求超时，请稍后重试'
    if (status === 429) return '请求过于频繁，请稍后重试'
    return `请求失败 (${status})`
  }

  async function sendMessage(content: string) {
    lastQuestion.value = content
    store.addMessage({ role: 'user', content })
    store.addMessage({ role: 'assistant', content: '' })
    store.streaming = true

    let retries = 0
    let success = false

    while (retries <= MAX_RETRIES && !success) {
      abortController.value = new AbortController()
      const timer = setTimeout(() => abortController.value?.abort(), SSE_TIMEOUT_MS)

      try {
        const response = await fetch('/api/chat/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conversation_id: store.currentId, message: content }),
          signal: abortController.value.signal,
        })

        clearTimeout(timer)

        if (!response.ok) {
          if (response.status >= 500 && retries < MAX_RETRIES) {
            retries++
            continue  // 服务端错误重试
          }
          throw new Error(_errorLabel(response.status))
        }

        const convId = response.headers.get('X-Conversation-Id')
        if (convId) store.currentId = convId

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''  // 缓冲区，处理跨 chunk 的 SSE 数据分割

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''  // 保留未完成的行

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const data = JSON.parse(line.slice(6))
              if (data.done) {
                store.streaming = false
              } else {
                store.updateLastMessage(data.content)
              }
            } catch {
              // skip malformed JSON（跨 chunk 截断等情况）
            }
          }
        }

        store.streaming = false
        success = true
        await store.loadConversations()
      } catch (e: any) {
        clearTimeout(timer)
        if (e.name === 'AbortError') {
          store.streaming = false
          store.updateLastMessage('\n\n> ⏱ 请求已取消或超时')
          break
        }
        if (retries >= MAX_RETRIES) {
          store.streaming = false
          const msg = typeof e.message === 'string' && e.message ? e.message : '网络连接失败'
          store.updateLastMessage(`\n\n> ❌ ${msg}，请稍后重试`)
        }
      }
    }
  }

  function stopStreaming() {
    abortController.value?.abort()
    store.streaming = false
  }

  function retry() {
    if (lastQuestion.value) {
      sendMessage(lastQuestion.value)
    }
  }

  return { sendMessage, stopStreaming, retry }
}
