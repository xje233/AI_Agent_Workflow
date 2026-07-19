import { ArrowRightOutlined, CheckCircleOutlined, LoadingOutlined, SearchOutlined, SettingOutlined, SyncOutlined } from '@ant-design/icons'
import { Tag } from 'antd'
import type { NodeState } from '@/types/workflow'

const labels = { analyze: '分析意图', research: '检索信息', execute: '生成方案', review: '质量审查' }
const icons = { analyze: <SearchOutlined />, research: <SyncOutlined />, execute: <SettingOutlined />, review: <CheckCircleOutlined /> }
const statusText = { pending: '等待', running: '执行中', completed: '完成', error: '失败' }
const colors = { pending: '#c0c4cc', running: '#409eff', completed: '#67c23a', error: '#f56c6c' }

export default function NodeStatusCard({ node, isLast }: { node: NodeState; isLast: boolean }) {
  return <div className="node-chain-wrapper"><div className={`node-card ${node.status}`}><div className="node-icon" style={{ background: colors[node.status] }}>{icons[node.name]}</div><div className="node-info"><div className="node-name">{labels[node.name]}</div><Tag color={node.status === 'pending' ? 'default' : node.status === 'running' ? 'blue' : node.status === 'completed' ? 'success' : 'error'}>{statusText[node.status]}</Tag></div>{node.status === 'running' && <LoadingOutlined className="node-spinner" spin />}</div>{!isLast && <div className="node-arrow" style={{ color: colors[node.status] }}><ArrowRightOutlined /></div>}</div>
}
