<script setup lang="ts">
import { nextTick, watch, ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSSE } from '@/composables/useSSE'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'

const store = useChatStore()
const { sendMessage, stopStreaming } = useSSE()
const messagesContainer = ref<HTMLElement>()

watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

async function handleSend(content: string) {
  if (!store.currentId) {
    await store.newConversation()
  }
  await sendMessage(content)
}
</script>

<template>
  <div class="chat-window">
    <div ref="messagesContainer" class="messages-container">
      <div v-if="!store.currentId" class="welcome-message">
        <el-icon :size="64" color="#c0c4cc"><ChatDotRound /></el-icon>
        <h2>AI Agent 工作流助手</h2>
        <p>选择一个会话或创建新会话开始对话</p>
      </div>

      <div v-else-if="store.messages.length === 0" class="welcome-message">
        <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>开始你的第一个问题</p>
      </div>

      <MessageBubble
        v-for="(msg, i) in store.messages"
        :key="i"
        :message="msg"
        :streaming="store.streaming && i === store.messages.length - 1 && msg.role === 'assistant'"
      />
    </div>

    <ChatInput
      :disabled="!store.currentId"
      :streaming="store.streaming"
      @send="handleSend"
      @stop="stopStreaming"
    />
  </div>
</template>

<style scoped>
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 12px;
}
.welcome-message h2 {
  margin: 0;
  color: #303133;
}
</style>
