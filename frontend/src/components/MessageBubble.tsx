import { RobotOutlined, UserOutlined } from '@ant-design/icons'
import { renderMarkdown } from '@/hooks/useMarkdown'
import type { Message } from '@/types/chat'

export default function MessageBubble({ message, streaming }: { message: Message; streaming: boolean }) {
  const html = renderMarkdown(message.content)
  return <div className={`message-bubble ${message.role}`}><div className="message-avatar">{message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}</div><div className="message-content"><div className="message-role">{message.role === 'user' ? '用户' : 'AI Agent'}</div>{streaming && !message.content ? <div className="thinking-dots"><span /><span /><span /></div> : <div className="markdown-body" dangerouslySetInnerHTML={{ __html: html }} />}{streaming && <span className="typing-cursor">|</span>}</div></div>
}
