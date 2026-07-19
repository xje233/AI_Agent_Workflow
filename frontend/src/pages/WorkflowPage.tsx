import NavBar from '@/components/NavBar'
import WorkflowPanel from '@/components/WorkflowPanel'

export default function WorkflowPage() { return <div className="page-container"><NavBar /><div className="content-body"><div className="content-header"><h2>LangGraph 工作流</h2><p>多步骤任务编排：分析 → 检索 → 执行 → 审查</p></div><WorkflowPanel /></div></div> }
