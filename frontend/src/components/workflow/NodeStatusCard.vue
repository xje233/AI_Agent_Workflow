<script setup lang="ts">
import type { NodeState } from '@/types/workflow'
import { computed } from 'vue'

const props = defineProps<{
  node: NodeState
  isLast: boolean
}>()

const labelMap: Record<string, string> = {
  analyze: '分析意图',
  research: '检索信息',
  execute: '生成方案',
  review: '质量审查',
}

const iconMap: Record<string, string> = {
  analyze: 'Search',
  research: 'Collection',
  execute: 'SetUp',
  review: 'Finished',
}

const statusColor = computed(() => {
  if (props.node.status === 'completed') return '#67c23a'
  if (props.node.status === 'running') return '#409eff'
  if (props.node.status === 'error') return '#f56c6c'
  return '#c0c4cc'
})
</script>

<template>
  <div class="node-chain-wrapper">
    <div class="node-card" :class="node.status">
      <div class="node-icon" :style="{ background: statusColor }">
        <el-icon :size="20"><component :is="iconMap[node.name]" /></el-icon>
      </div>
      <div class="node-info">
        <div class="node-name">{{ labelMap[node.name] }}</div>
        <div class="node-status">
          <el-tag
            size="small"
            :type="
              node.status === 'completed' ? 'success'
              : node.status === 'running' ? ''
              : node.status === 'error' ? 'danger'
              : 'info'
            "
            :effect="node.status === 'running' ? 'dark' : 'plain'"
          >
            {{
              node.status === 'completed' ? '完成'
              : node.status === 'running' ? '执行中'
              : node.status === 'error' ? '失败'
              : '等待'
            }}
          </el-tag>
        </div>
      </div>
      <div v-if="node.status === 'running'" class="node-spinner">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
    </div>
    <div v-if="!isLast" class="node-arrow" :style="{ color: statusColor }">
      <el-icon><ArrowRight /></el-icon>
    </div>
  </div>
</template>

<style scoped>
.node-chain-wrapper {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.node-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 10px;
  background: white;
  border: 2px solid #e4e7ed;
  min-width: 160px;
  transition: all 0.3s;
}
.node-card.completed {
  border-color: #67c23a;
}
.node-card.running {
  border-color: #409eff;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}
.node-card.error {
  border-color: #f56c6c;
}
.node-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: background 0.3s;
}
.node-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.node-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.node-status {
  font-size: 12px;
}
.node-spinner {
  color: #409eff;
}
.node-arrow {
  font-size: 20px;
  margin: 0 4px;
  display: flex;
  align-items: center;
  transition: color 0.3s;
}
</style>
