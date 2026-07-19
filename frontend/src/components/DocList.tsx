import { DeleteOutlined, FileTextOutlined, FileWordOutlined, FileMarkdownOutlined, FileUnknownOutlined } from '@ant-design/icons'
import { Button, Space, Table, Tag } from 'antd'
import { useKnowledgeStore } from '@/stores/knowledge'
import type { KnowledgeDocument } from '@/types/knowledge'

const statuses: Record<string, { label: string; color: string }> = { pending: { label: '待索引', color: 'default' }, indexing: { label: '索引中', color: 'processing' }, completed: { label: '已索引', color: 'success' }, failed: { label: '失败', color: 'error' } }
function icon(type: string) { return type === 'docx' || type === 'doc' ? <FileWordOutlined /> : type === 'md' ? <FileMarkdownOutlined /> : type === 'txt' ? <FileTextOutlined /> : <FileUnknownOutlined /> }

export default function DocList() {
  const store = useKnowledgeStore()
  const columns = [{ title: '文件名', dataIndex: 'filename', key: 'filename', render: (name: string, row: KnowledgeDocument) => <Space>{icon(row.file_type)}{name}</Space> }, { title: '类型', dataIndex: 'file_type', width: 100, render: (type: string) => <Tag>{type.toUpperCase()}</Tag> }, { title: '状态', dataIndex: 'vector_status', width: 120, render: (status: string) => <Tag color={statuses[status]?.color}>{statuses[status]?.label || status}</Tag> }, { title: '上传时间', dataIndex: 'created_at', width: 180, render: (date: string) => new Date(date).toLocaleString('zh-CN') }, { title: '操作', width: 100, render: (_: unknown, row: KnowledgeDocument) => <Button type="link" danger icon={<DeleteOutlined />} onClick={() => store.deleteDocument(row.id)}>删除</Button> }]
  return <Table rowKey="id" loading={store.uploading} dataSource={store.documents} columns={columns} />
}
