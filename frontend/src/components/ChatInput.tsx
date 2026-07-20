// 聊天输入框：管理本地草稿，并在发送或停止间切换操作。
import { LoadingOutlined } from '@ant-design/icons'
import { Button, Input } from 'antd'
import { useState } from 'react'

export default function ChatInput({ disabled, streaming, onSend, onStop }: { disabled: boolean; streaming: boolean; onSend: (content: string) => void; onStop: () => void }) {
  const [input, setInput] = useState('')
  const send = () => { const content = input.trim(); if (!content || streaming || disabled) return; onSend(content); setInput('') }
  return <div className="chat-input-bar"><div className="input-wrapper"><Input.TextArea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} autoSize={{ minRows: 2, maxRows: 5 }} maxLength={4000} showCount disabled={disabled} placeholder="输入消息，Enter 发送，Shift+Enter 换行" /><Button type={streaming ? 'default' : 'primary'} danger={streaming} disabled={!streaming && (!input.trim() || disabled)} onClick={streaming ? onStop : send}>{streaming && <LoadingOutlined spin />}{streaming ? '停止生成' : '发送'}</Button></div></div>
}
