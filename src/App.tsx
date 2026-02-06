import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LoadingFallback from './components/ui/LoadingFallback'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Chat = lazy(() => import('./pages/Chat'))
const Orders = lazy(() => import('./pages/Orders'))
const Screener = lazy(() => import('./pages/Screener'))

export default function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/screener" element={<Screener />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

