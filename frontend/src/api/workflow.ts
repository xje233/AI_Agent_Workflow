// 工作流 API：启动后端任务并返回原始流式 Response 供 SSE Hook 消费。
import request from './request'

export const workflowApi = {
  async startWorkflow(data: { question: string; conversation_id?: string }): Promise<Response> {
    // 流式响应不能由 Axios 自动解包，直接交给 Fetch 和读取器处理。
    return fetch('/api/workflow/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },

  getStatus(threadId: string): Promise<any> {
    return request.get(`/workflow/status/${threadId}`) as any
  },
}
