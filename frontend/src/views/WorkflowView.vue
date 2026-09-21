<script setup lang="ts">
import NavBar from '@/components/common/NavBar.vue'
import WorkflowPanel from '@/components/workflow/WorkflowPanel.vue'
</script>

<template>
  <div class="workflow-container">
    <NavBar />
    <div class="workflow-body">
      <div class="workflow-header">
        <h2>LangGraph 工作流</h2>
        <p>多步骤任务编排：分析 → 检索 → 执行 → 审查</p>
      </div>
      <WorkflowPanel />
    </div>
  </div>
</template>

<style scoped>
.workflow-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.workflow-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #f5f7fa;
}
.workflow-header {
  margin-bottom: 24px;
}
.workflow-header h2 {
  margin: 0 0 8px;
}
.workflow-header p {
  color: #909399;
  margin: 0;
}
</style>
