<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '@/components/common/NavBar.vue'
import HistorySidebar from '@/components/chat/HistorySidebar.vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()

onMounted(() => {
  store.loadConversations()
})
</script>

<template>
  <div class="home-container">
    <NavBar />
    <div class="home-body">
      <HistorySidebar />
      <ChatWindow />
    </div>
  </div>
</template>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.home-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
