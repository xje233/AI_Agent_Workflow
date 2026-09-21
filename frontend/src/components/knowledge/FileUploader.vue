<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useKnowledgeStore } from '@/stores/knowledge'

const store = useKnowledgeStore()
const uploadRef = ref<any>()

const allowedTypes = ['.pdf', '.docx', '.txt', '.md']

async function handleUpload(options: any) {
  try {
    await store.uploadDocument(options.file)
    ElMessage.success('文档上传并索引成功')
  } catch {
    // error handled by axios interceptor
  }
}
</script>

<template>
  <el-upload
    ref="uploadRef"
    drag
    :auto-upload="true"
    :accept="allowedTypes.join(',')"
    :http-request="handleUpload"
    :show-file-list="false"
    :disabled="store.uploading"
  >
    <el-icon :size="48" color="#c0c4cc"><UploadFilled /></el-icon>
    <div class="upload-text">
      <p>拖拽文件到此处或 <em>点击上传</em></p>
      <p class="hint">支持 PDF、Word、Markdown、TXT</p>
    </div>
  </el-upload>
</template>

<style scoped>
.upload-text p {
  margin: 4px 0;
  color: #606266;
}
.upload-text .hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
