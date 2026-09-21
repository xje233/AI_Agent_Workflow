<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '@/composables/useMarkdown'
import type { Message } from '@/types/chat'

const props = defineProps<{
  message: Message
  streaming: boolean
}>()

const { render } = useMarkdown()

const htmlContent = computed(() => render(props.message.content))
</script>

<template>
  <div class="message-bubble" :class="message.role">
    <div class="message-avatar">
      <el-icon v-if="message.role === 'user'" :size="24"><UserFilled /></el-icon>
      <el-icon v-else :size="24"><Cpu /></el-icon>
    </div>
    <div class="message-content">
      <div class="message-role">{{ message.role === 'user' ? '你' : 'AI Agent' }}</div>
      <div v-if="streaming && !message.content" class="thinking-dots">
        <span></span><span></span><span></span>
      </div>
      <div v-else class="markdown-body" v-html="htmlContent" />
      <span v-if="streaming" class="typing-cursor">|</span>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 85%;
}
.message-bubble.user {
  margin-left: auto;
  flex-direction: row-reverse;
}
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409eff;
  color: white;
  flex-shrink: 0;
}
.message-bubble.user .message-avatar {
  background: #67c23a;
}
.message-role {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.message-bubble.user .message-content {
  background: #409eff;
  color: white;
}
.typing-cursor {
  animation: blink 1s infinite;
  font-weight: bold;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.thinking-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
  animation: bounce 1.4s infinite ease-in-out;
}
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
