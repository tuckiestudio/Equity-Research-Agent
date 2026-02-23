import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import AppShell from '@/components/layout/AppShell'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Dashboard from '@/pages/Dashboard'
import StockDetail from '@/pages/StockDetail'
import Settings from '@/pages/Settings'
import Portfolio from '@/pages/Portfolio'
import Search from '@/pages/Search'
import Market from '@/pages/Market'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/search" element={<Search />} />
            <Route path="/market" element={<Market />} />
            <Route path="/stock/:ticker" element={<StockDetail />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>
      </Routes>
    </Router>
  )
}

export default App
