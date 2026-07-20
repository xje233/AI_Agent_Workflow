import { MessageOutlined } from '@ant-design/icons'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useEffect, useLayoutEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chat'
import { useSSE } from '@/hooks/useSSE'
import type { Message } from '@/types/chat'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'

const VIRTUALIZATION_THRESHOLD = 100
const BOTTOM_OFFSET = 80

export default function ChatWindow() {
  const store = useChatStore()
  const { sendMessage, stopStreaming } = useSSE()
  const container = useRef<HTMLDivElement>(null)
  const followOutput = useRef(true)
  const lastMessage = store.messages[store.messages.length - 1]
  const useVirtualList = store.messages.length > VIRTUALIZATION_THRESHOLD

  const updateFollowOutput = () => {
    const element = container.current
    if (!element) return
    followOutput.current = element.scrollHeight - element.scrollTop - element.clientHeight < BOTTOM_OFFSET
  }

  useEffect(() => {
    if (useVirtualList || !followOutput.current || !container.current) return
    window.requestAnimationFrame(() => {
      if (followOutput.current && container.current) container.current.scrollTop = container.current.scrollHeight
    })
  }, [lastMessage?.content, store.messages.length, useVirtualList])

  const send = async (content: string) => {
    if (!store.currentId) await store.newConversation()
    await sendMessage(content)
  }

  return (
    <main className="chat-window">
      <div ref={container} className="messages-container" onScroll={updateFollowOutput}>
        {!store.currentId ? <Welcome title="AI Agent 工作流助手" text="选择一个会话或创建新会话开始对话" size={64} /> : store.messages.length === 0 ? <Welcome text="开始你的第一个问题" size={48} /> : useVirtualList ? <VirtualMessageList messages={store.messages} streaming={store.streaming} container={container} followOutput={followOutput.current} /> : <MessageList messages={store.messages} streaming={store.streaming} />}
      </div>
      <ChatInput disabled={!store.currentId} streaming={store.streaming} onSend={send} onStop={stopStreaming} />
    </main>
  )
}

function MessageList({ messages, streaming }: { messages: Message[]; streaming: boolean }) {
  return <>{messages.map((message, index) => <MessageBubble key={`${index}-${message.role}`} message={message} streaming={streaming && index === messages.length - 1 && message.role === 'assistant'} />)}</>
}

function VirtualMessageList({ messages, streaming, container, followOutput }: { messages: Message[]; streaming: boolean; container: React.RefObject<HTMLDivElement | null>; followOutput: boolean }) {
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => container.current,
    estimateSize: () => 120,
    overscan: 5,
  })
  const lastMessage = messages[messages.length - 1]

  useLayoutEffect(() => {
    if (followOutput && messages.length) virtualizer.scrollToIndex(messages.length - 1, { align: 'end' })
  }, [followOutput, lastMessage?.content, messages.length, virtualizer])

  return (
    <div className="virtual-messages" style={{ height: virtualizer.getTotalSize() }}>
      {virtualizer.getVirtualItems().map((virtualRow) => {
        const message = messages[virtualRow.index]
        return (
          <div ref={virtualizer.measureElement} data-index={virtualRow.index} key={virtualRow.key} className="virtual-message" style={{ transform: `translateY(${virtualRow.start}px)` }}>
            <MessageBubble message={message} streaming={streaming && virtualRow.index === messages.length - 1 && message.role === 'assistant'} />
          </div>
        )
      })}
    </div>
  )
}

function Welcome({ title, text, size }: { title?: string; text: string; size: number }) {
  return <div className="welcome-message"><MessageOutlined style={{ fontSize: size, color: '#c0c4cc' }} />{title && <h2>{title}</h2>}<p>{text}</p></div>
}
