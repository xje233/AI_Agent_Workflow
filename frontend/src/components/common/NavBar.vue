<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const navItems = [
  { path: '/', label: 'AI 对话' },
  { path: '/workflow', label: '工作流' },
  { path: '/knowledge', label: '知识库' },
]
</script>

<template>
  <el-menu
    :default-active="route.path"
    mode="horizontal"
    :ellipsis="false"
    @select="(key: string) => router.push(key)"
  >
    <div class="nav-brand">
      <el-icon :size="24"><Cpu /></el-icon>
      <span>AI Agent 工作流平台</span>
    </div>
    <div class="flex-grow" />
    <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
      {{ item.label }}
    </el-menu-item>
  </el-menu>
</template>

<style scoped>
.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}
.flex-grow {
  flex: 1;
}
</style>
