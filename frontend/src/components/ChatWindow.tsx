// 聊天窗口：组合消息列表、滚动定位和输入控制。
import { MessageOutlined } from '@ant-design/icons'
import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chat'
import { useSSE } from '@/hooks/useSSE'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'

export default function ChatWindow() {
  const store = useChatStore(); const { sendMessage, stopStreaming } = useSSE(); const container = useRef<HTMLDivElement>(null)
  // 新消息或最后一条内容增长时自动滚动到底部，覆盖流式追加场景。
  useEffect(() => { if (container.current) container.current.scrollTop = container.current.scrollHeight }, [store.messages.length, store.messages[store.messages.length - 1]?.content])
  const send = async (content: string) => { if (!store.currentId) await store.newConversation(); await sendMessage(content) }
  return <main className="chat-window"><div ref={container} className="messages-container">{!store.currentId ? <Welcome title="AI Agent 工作流助手" text="选择一个会话或创建新会话开始对话" size={64} /> : store.messages.length === 0 ? <Welcome text="开始你的第一个问题" size={48} /> : store.messages.map((msg, i) => <MessageBubble key={`${i}-${msg.role}`} message={msg} streaming={store.streaming && i === store.messages.length - 1 && msg.role === 'assistant'} />)}</div><ChatInput disabled={!store.currentId} streaming={store.streaming} onSend={send} onStop={stopStreaming} /></main>
}

function Welcome({ title, text, size }: { title?: string; text: string; size: number }) { return <div className="welcome-message"><MessageOutlined style={{ fontSize: size, color: '#c0c4cc' }} />{title && <h2>{title}</h2>}<p>{text}</p></div> }
