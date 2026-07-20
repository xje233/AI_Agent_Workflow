// 历史会话侧栏：创建、切换和删除聊天会话。
import { DeleteOutlined, MessageOutlined, PlusOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import { useChatStore } from '@/stores/chat'

export default function HistorySidebar() {
  const store = useChatStore()
  return <aside className="history-sidebar"><div className="sidebar-header"><h3>历史会话</h3><Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => store.newConversation()}>新会话</Button></div><div className="conversation-list">{store.conversations.map((conversation) => <div key={conversation.id} className={`conversation-item ${conversation.id === store.currentId ? 'active' : ''}`} onClick={() => store.loadMessages(conversation.id)}><MessageOutlined /><span className="conv-title">{conversation.title}</span><Button type="text" danger size="small" className="delete-btn" icon={<DeleteOutlined />} onClick={(e) => { e.stopPropagation(); store.deleteConversation(conversation.id) }} /></div>)}{store.conversations.length === 0 && <div className="empty-hint">暂无会话，点击上方按钮创建</div>}</div></aside>
}
