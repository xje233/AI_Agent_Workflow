import { useEffect } from 'react'
import NavBar from '@/components/NavBar'
import FileUploader from '@/components/FileUploader'
import DocList from '@/components/DocList'
import { useKnowledgeStore } from '@/stores/knowledge'

export default function KnowledgePage() { const load = useKnowledgeStore((state) => state.loadDocuments); useEffect(() => { void load() }, [load]); return <div className="page-container"><NavBar /><div className="content-body"><div className="content-header"><h2>知识库管理</h2><p>上传文档构建企业知识库，支持 PDF、Word、Markdown、TXT 格式</p><FileUploader /></div><DocList /></div></div> }
