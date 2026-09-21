import request from './request'

export const workflowApi = {
  async startWorkflow(data: { question: string; conversation_id?: string }): Promise<Response> {
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
