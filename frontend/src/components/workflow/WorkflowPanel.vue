<script setup lang="ts">
import { ref } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { useWorkflowSSE } from '@/composables/useWorkflowSSE'
import NodeStatusCard from './NodeStatusCard.vue'

const store = useWorkflowStore()
const { startWorkflow, stopWorkflow } = useWorkflowSSE()

const question = ref('')
const running = ref(false)

async function handleStart() {
  const q = question.value.trim()
  if (!q) return
  running.value = true
  await startWorkflow(q)
  running.value = false
}

function handleStop() {
  stopWorkflow()
  running.value = false
}
</script>

<template>
  <div class="workflow-panel">
    <!-- 输入区 -->
    <el-card class="input-card">
      <template #header>
        <span>输入任务描述</span>
      </template>
      <el-input
        v-model="question"
        type="textarea"
        :rows="3"
        maxlength="2000"
        show-word-limit
        placeholder="描述你的复杂任务，例如：分析数据库性能瓶颈并给出优化方案"
        :disabled="running"
        @keydown.enter.ctrl="handleStart"
      />
      <div class="input-actions">
        <el-button
          v-if="!running"
          type="primary"
          :disabled="!question.trim()"
          @click="handleStart"
        >
          <el-icon><VideoPlay /></el-icon>
          启动工作流
        </el-button>
        <el-button v-else type="danger" @click="handleStop">
          <el-icon><Close /></el-icon>
          停止
        </el-button>
        <span class="hint">Ctrl+Enter 快速启动</span>
      </div>
    </el-card>

    <!-- 节点状态 -->
    <el-card class="nodes-card" v-if="store.status !== 'idle'">
      <template #header>
        <div class="nodes-header">
          <span>执行进度</span>
          <el-tag
            :type="
              store.status === 'completed' ? 'success'
              : store.status === 'error' ? 'danger'
              : 'warning'
            "
          >
            {{
              store.status === 'running' ? '运行中'
              : store.status === 'completed' ? '已完成'
              : '出错'
            }}
          </el-tag>
        </div>
      </template>
      <div class="nodes-chain">
        <NodeStatusCard
          v-for="(node, index) in store.nodes"
          :key="node.name"
          :node="node"
          :is-last="index === store.nodes.length - 1"
        />
      </div>
    </el-card>

    <!-- 实时输出 -->
    <el-card class="output-card" v-if="store.streamContent">
      <template #header>
        <span>实时输出</span>
      </template>
      <div class="stream-output markdown-body" v-text="store.streamContent" />
    </el-card>

    <!-- 最终结果 -->
    <el-card class="result-card" v-if="store.finalAnswer">
      <template #header>
        <span>最终结果</span>
      </template>
      <div class="final-answer markdown-body" v-text="store.finalAnswer" />

      <el-alert
        v-if="store.reviewNote && store.reviewNote !== 'PASS'"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #title>{{ store.reviewNote }}</template>
      </el-alert>
    </el-card>
  </div>
</template>

<style scoped>
.workflow-panel {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.input-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.input-actions .hint {
  color: #c0c4cc;
  font-size: 12px;
}
.nodes-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.nodes-chain {
  display: flex;
  align-items: center;
  gap: 0;
  overflow-x: auto;
  padding: 8px 0;
}
</style>
