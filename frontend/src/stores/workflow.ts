import { create } from 'zustand'
import type { NodeName, NodeState } from '@/types/workflow'

interface WorkflowLog { node: NodeName; status: string; summary: string }
interface WorkflowState {
  nodes: NodeState[]
  status: 'idle' | 'running' | 'completed' | 'error'
  logs: WorkflowLog[]
  finalAnswer: string
  reviewNote: string
  streamContent: string
  errorMessage: string
  reset: () => void
  updateNode: (name: NodeName, status: string, summary?: string) => void
  addLog: (log: WorkflowLog) => void
}

const initialNodes = (): NodeState[] => ['analyze', 'research', 'execute', 'review'].map((name) => ({ name: name as NodeName, status: 'pending', summary: '' }))

export const useWorkflowStore = create<WorkflowState>((set) => ({
  nodes: initialNodes(), status: 'idle', logs: [], finalAnswer: '', reviewNote: '', streamContent: '', errorMessage: '',
  reset: () => set({ nodes: initialNodes(), status: 'idle', logs: [], finalAnswer: '', reviewNote: '', streamContent: '', errorMessage: '' }),
  updateNode: (name, status, summary) => set((state) => ({ nodes: state.nodes.map((node) => node.name === name ? { ...node, status: status as NodeState['status'], summary: summary || node.summary, timestamp: new Date().toISOString() } : node) })),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
}))
