import { RobotOutlined } from '@ant-design/icons'
import { Menu } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'

export default function NavBar() {
  const navigate = useNavigate(); const location = useLocation()
  return <div className="nav-bar"><div className="nav-brand"><RobotOutlined /> <span>AI Agent 工作流平台</span></div><Menu mode="horizontal" selectedKeys={[location.pathname]} onClick={({ key }) => navigate(key)} items={[{ key: '/', label: 'AI 对话' }, { key: '/workflow', label: '工作流' }, { key: '/knowledge', label: '知识库' }]} overflowedIndicator={null} /></div>
}
