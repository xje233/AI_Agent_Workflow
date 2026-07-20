// 工作流领域类型：约束节点名称、节点进度及流式事件结构。
export type NodeName = 'analyze' | 'research' | 'execute' | 'review'
export type NodeStatus = 'pending' | 'running' | 'completed' | 'error'

export interface NodeState {
  name: NodeName
  status: NodeStatus
  summary: string
  timestamp?: string
}

export interface WorkflowEvent {
  type: 'node_start' | 'node_complete' | 'stream_start' | 'stream_token' | 'done' | 'error'
  node?: NodeName
  status?: NodeStatus
  summary?: string
  content?: string
  final_answer?: string
  review_note?: string
  message?: string
}
