import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { NodeState, NodeName } from '@/types/workflow'

interface WorkflowLog {
  node: NodeName
  status: string
  summary: string
}

export const useWorkflowStore = defineStore('workflow', () => {
  const nodes = ref<NodeState[]>([
    { name: 'analyze', status: 'pending', summary: '' },
    { name: 'research', status: 'pending', summary: '' },
    { name: 'execute', status: 'pending', summary: '' },
    { name: 'review', status: 'pending', summary: '' },
  ])

  const status = ref<'idle' | 'running' | 'completed' | 'error'>('idle')
  const logs = ref<WorkflowLog[]>([])
  const finalAnswer = ref('')
  const reviewNote = ref('')
  const streamContent = ref('')
  const errorMessage = ref('')

  function reset() {
    nodes.value.forEach((n) => {
      n.status = 'pending'
      n.summary = ''
    })
    status.value = 'idle'
    logs.value = []
    finalAnswer.value = ''
    reviewNote.value = ''
    streamContent.value = ''
    errorMessage.value = ''
  }

  function updateNode(nodeName: NodeName, nodeStatus: string, summary?: string) {
    const node = nodes.value.find((n) => n.name === nodeName)
    if (node) {
      node.status = nodeStatus as any
      if (summary) node.summary = summary
      node.timestamp = new Date().toISOString()
    }
  }

  function addLog(log: WorkflowLog) {
    logs.value.push(log)
  }

  return {
    nodes, status, logs, finalAnswer, reviewNote, streamContent, errorMessage,
    reset, updateNode, addLog,
  }
})
