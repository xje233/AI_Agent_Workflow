<script setup lang="ts">
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

function selectConversation(id: string) {
  store.loadMessages(id)
}
</script>

<template>
  <div class="history-sidebar">
    <div class="sidebar-header">
      <h3>历史会话</h3>
      <el-button type="primary" size="small" @click="store.newConversation()">
        <el-icon><Plus /></el-icon>
        新会话
      </el-button>
    </div>

    <div class="conversation-list">
      <div
        v-for="conv in store.conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === store.currentId }"
        @click="selectConversation(conv.id)"
      >
        <el-icon><ChatLineSquare /></el-icon>
        <span class="conv-title">{{ conv.title }}</span>
        <el-button
          type="danger"
          link
          size="small"
          class="delete-btn"
          @click.stop="store.deleteConversation(conv.id)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>

      <div v-if="store.conversations.length === 0" class="empty-hint">
        暂无会话，点击上方按钮创建
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
}
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.conversation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.conversation-item:hover {
  background: #f5f7fa;
}
.conversation-item.active {
  background: #ecf5ff;
  color: #409eff;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}
.conversation-item:hover .delete-btn {
  opacity: 1;
}
.empty-hint {
  text-align: center;
  padding: 40px 16px;
  color: #c0c4cc;
  font-size: 14px;
}
</style>
