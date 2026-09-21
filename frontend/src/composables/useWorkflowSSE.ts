import { ref } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import type { WorkflowEvent } from '@/types/workflow'
import { ElMessage } from 'element-plus'

export function useWorkflowSSE() {
  const store = useWorkflowStore()
  const abortController = ref<AbortController | null>(null)

  async function startWorkflow(question: string) {
    store.reset()
    store.status = 'running'

    abortController.value = new AbortController()

    try {
      const response = await fetch('/api/workflow/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: abortController.value.signal,
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || '工作流启动失败')
      }

      const reader = response.body!.getReader()
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
          try {
            const event: WorkflowEvent = JSON.parse(line.slice(6))
            handleEvent(event)
          } catch {
            // skip malformed JSON
          }
        }
      }

      if (store.status === 'running') {
        store.status = 'completed'
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        store.status = 'error'
        store.errorMessage = e.message || '工作流执行失败'
        ElMessage.error(store.errorMessage)
      }
    }
  }

  function handleEvent(event: WorkflowEvent) {
    switch (event.type) {
      case 'node_start':
        if (event.node) {
          store.updateNode(event.node, 'running')
          store.addLog({ node: event.node, status: 'running', summary: '' })
        }
        break

      case 'node_complete':
        if (event.node) {
          store.updateNode(event.node, 'completed', event.summary)
          store.addLog({
            node: event.node,
            status: 'completed',
            summary: event.summary || '',
          })
        }
        break

      case 'stream_start':
        store.streamContent = ''
        break

      case 'stream_token':
        if (event.content) {
          store.streamContent += event.content
        }
        break

      case 'done':
        store.finalAnswer = event.final_answer || ''
        store.reviewNote = event.review_note || ''
        store.status = 'completed'
        break

      case 'error':
        store.status = 'error'
        store.errorMessage = event.message || '未知错误'
        ElMessage.error(store.errorMessage)
        break
    }
  }

  function stopWorkflow() {
    abortController.value?.abort()
    store.status = 'idle'
  }

  return { startWorkflow, stopWorkflow }
}
