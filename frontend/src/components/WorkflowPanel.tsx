import { CloseOutlined, VideoCameraAddOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Input, Tag } from 'antd'
import { useState } from 'react'
import { useWorkflowStore } from '@/stores/workflow'
import { useWorkflowSSE } from '@/hooks/useWorkflowSSE'
import NodeStatusCard from './NodeStatusCard'

export default function WorkflowPanel() {
  const store = useWorkflowStore(); const { startWorkflow, stopWorkflow } = useWorkflowSSE(); const [question, setQuestion] = useState(''); const running = store.status === 'running'
  const start = async () => { const value = question.trim(); if (value) await startWorkflow(value) }
  return <div className="workflow-panel"><Card title="输入任务描述"><Input.TextArea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => { if (e.ctrlKey && e.key === 'Enter') start() }} rows={3} maxLength={2000} showCount disabled={running} placeholder="描述你的复杂任务，例如：分析数据库性能瓶颈并给出优化方案" /><div className="input-actions">{!running ? <Button type="primary" icon={<VideoCameraAddOutlined />} disabled={!question.trim()} onClick={start}>启动工作流</Button> : <Button danger icon={<CloseOutlined />} onClick={stopWorkflow}>停止</Button>}<span className="hint">Ctrl+Enter 快速启动</span></div></Card>{store.status !== 'idle' && <Card title={<div className="nodes-header"><span>执行进度</span><Tag color={store.status === 'completed' ? 'success' : store.status === 'error' ? 'error' : 'processing'}>{store.status === 'running' ? '运行中' : store.status === 'completed' ? '已完成' : '出错'}</Tag></div>}><div className="nodes-chain">{store.nodes.map((node, index) => <NodeStatusCard key={node.name} node={node} isLast={index === store.nodes.length - 1} />)}</div></Card>}{store.streamContent && <Card title="实时输出"><div className="stream-output markdown-body">{store.streamContent}</div></Card>}{store.finalAnswer && <Card title="最终结果"><div className="final-answer markdown-body">{store.finalAnswer}</div>{store.reviewNote && store.reviewNote !== 'PASS' && <Alert type="warning" showIcon message={store.reviewNote} />}</Card>}{store.errorMessage && <Alert type="error" showIcon message={store.errorMessage} />}</div>
}
