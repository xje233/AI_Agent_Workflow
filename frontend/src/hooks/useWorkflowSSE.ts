// 工作流流 Hook：将节点和文本事件映射到工作流状态。
import { useRef } from 'react'
import { message } from 'antd'
import { useWorkflowStore } from '@/stores/workflow'
import type { WorkflowEvent } from '@/types/workflow'

export function useWorkflowSSE() {
  const abortRef = useRef<AbortController | null>(null)

  async function startWorkflow(question: string) {
    const set = useWorkflowStore.setState
    const get = useWorkflowStore.getState
    // 每次启动先清除上一轮结果，再建立本轮请求的取消控制器。
    get().reset(); set({ status: 'running' }); abortRef.current = new AbortController()
    try {
      const response = await fetch('/api/workflow/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }), signal: abortRef.current.signal })
      if (!response.ok) { const error = await response.json(); throw new Error(error.detail || '工作流启动失败') }
      const reader = response.body?.getReader()
      if (!reader) throw new Error('响应流不可用')
      const decoder = new TextDecoder(); let buffer = ''
      while (true) {
        const { done, value } = await reader.read(); if (done) break
        // 与聊天流一致：保留跨网络分块的不完整尾行。
        buffer += decoder.decode(value, { stream: true }); const lines = buffer.split('\n'); buffer = lines.pop() || ''
        for (const line of lines) if (line.startsWith('data: ')) { try { handleEvent(JSON.parse(line.slice(6))) } catch { /* ignore malformed chunks */ } }
      }
      if (useWorkflowStore.getState().status === 'running') set({ status: 'completed' })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      const text = error instanceof Error ? error.message : '工作流执行失败'
      set({ status: 'error', errorMessage: text }); message.error(text)
    }
  }

  function handleEvent(event: WorkflowEvent) {
    // 后端事件类型与 Store 动作一一对应，组件只消费最终状态。
    const store = useWorkflowStore.getState()
    if (event.type === 'node_start' && event.node) { store.updateNode(event.node, 'running'); store.addLog({ node: event.node, status: 'running', summary: '' }) }
    if (event.type === 'node_complete' && event.node) { store.updateNode(event.node, 'completed', event.summary); store.addLog({ node: event.node, status: 'completed', summary: event.summary || '' }) }
    if (event.type === 'stream_start') useWorkflowStore.setState({ streamContent: '' })
    if (event.type === 'stream_token' && event.content) useWorkflowStore.setState((state) => ({ streamContent: state.streamContent + event.content }))
    if (event.type === 'done') useWorkflowStore.setState({ finalAnswer: event.final_answer || '', reviewNote: event.review_note || '', status: 'completed' })
    if (event.type === 'error') { const text = event.message || '未知错误'; useWorkflowStore.setState({ status: 'error', errorMessage: text }); message.error(text) }
  }

  return { startWorkflow, stopWorkflow: () => { abortRef.current?.abort(); useWorkflowStore.setState({ status: 'idle' }) } }
}
