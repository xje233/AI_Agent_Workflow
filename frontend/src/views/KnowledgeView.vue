<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from '@/components/common/NavBar.vue'
import FileUploader from '@/components/knowledge/FileUploader.vue'
import DocList from '@/components/knowledge/DocList.vue'
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()

onMounted(() => {
  store.loadDocuments()
})
</script>

<template>
  <div class="knowledge-container">
    <NavBar />
    <div class="knowledge-body">
      <div class="knowledge-header">
        <h2>知识库管理</h2>
        <p>上传文档构建企业知识库，支持 PDF、Word、Markdown、TXT 格式</p>
        <FileUploader />
      </div>
      <DocList />
    </div>
  </div>
</template>

<style scoped>
.knowledge-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.knowledge-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #f5f7fa;
}
.knowledge-header {
  margin-bottom: 24px;
}
.knowledge-header h2 {
  margin: 0 0 8px;
}
.knowledge-header p {
  color: #909399;
  margin: 0 0 16px;
}
</style>
