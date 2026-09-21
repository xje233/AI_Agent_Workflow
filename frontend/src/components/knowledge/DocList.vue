<script setup lang="ts">
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()

const statusMap: Record<string, { label: string; type: string }> = {
  pending: { label: '待索引', type: 'info' },
  indexing: { label: '索引中', type: 'warning' },
  completed: { label: '已索引', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

const fileIcons: Record<string, string> = {
  pdf: 'Document',
  docx: 'Document',
  doc: 'Document',
  txt: 'Tickets',
  md: 'Notebook',
}
</script>

<template>
  <el-table :data="store.documents" style="width: 100%" v-loading="store.uploading">
    <el-table-column label="文件名" min-width="300">
      <template #default="{ row }">
        <div class="file-cell">
          <el-icon :size="20"><component :is="fileIcons[row.file_type] || 'Document'" /></el-icon>
          <span>{{ row.filename }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="类型" width="100">
      <template #default="{ row }">
        <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="120">
      <template #default="{ row }">
        <el-tag :type="statusMap[row.vector_status]?.type || 'info'">
          {{ statusMap[row.vector_status]?.label || row.vector_status }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="上传时间" width="180">
      <template #default="{ row }">
        {{ new Date(row.created_at).toLocaleString('zh-CN') }}
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100">
      <template #default="{ row }">
        <el-button type="danger" link size="small" @click="store.deleteDocument(row.id)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
