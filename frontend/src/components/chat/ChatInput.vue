<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled: boolean
  streaming: boolean
}>()
const emit = defineEmits<{ send: [content: string]; stop: [] }>()

const input = ref('')
const textarea = ref<any>()

function handleSend() {
  const content = input.value.trim()
  if (!content || props.streaming) return
  emit('send', content)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input-bar">
    <div class="input-wrapper">
      <el-input
        ref="textarea"
        v-model="input"
        type="textarea"
        :rows="2"
        maxlength="4000"
        show-word-limit
        placeholder="输入消息，Enter 发送，Shift+Enter 换行"
        :disabled="disabled"
        @keydown="handleKeydown"
      />
      <el-button
        v-if="!streaming"
        type="primary"
        :disabled="!input.trim() || disabled"
        @click="handleSend"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="emit('stop')">
        <el-icon class="is-loading"><Loading /></el-icon>
        停止生成
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-input-bar {
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e4e7ed;
}
.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
