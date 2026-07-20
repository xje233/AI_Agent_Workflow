// 文件上传组件：限制允许类型，并触发知识库索引流程。
import { InboxOutlined } from '@ant-design/icons'
import { message, Upload } from 'antd'
import { useKnowledgeStore } from '@/stores/knowledge'

export default function FileUploader() {
  const store = useKnowledgeStore()
  return <Upload.Dragger accept=".pdf,.docx,.txt,.md" showUploadList={false} disabled={store.uploading} beforeUpload={async (file) => { try { await store.uploadDocument(file); message.success('文档上传并索引成功') } catch { /* interceptor handles the error */ } return false }}><p className="ant-upload-drag-icon"><InboxOutlined /></p><p>拖拽文件到此处或 <em>点击上传</em></p><p className="hint">支持 PDF、Word、Markdown、TXT</p></Upload.Dragger>
}
