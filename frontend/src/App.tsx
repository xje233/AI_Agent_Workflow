import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

const HomePage = lazy(() => import('./pages/HomePage'))
const KnowledgePage = lazy(() => import('./pages/KnowledgePage'))
const WorkflowPage = lazy(() => import('./pages/WorkflowPage'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="route-loading">加载中...</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/workflow" element={<WorkflowPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
