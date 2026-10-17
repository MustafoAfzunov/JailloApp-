import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { Loading } from './components/ui.jsx'
import { useAuth } from './lib/auth.jsx'
import Home from './pages/Home.jsx'
import SafetyMap from './pages/SafetyMap.jsx'
import Market from './pages/Market.jsx'
import Sell from './pages/Sell.jsx'
import Login from './pages/Login.jsx'
import AlertPage from './pages/AlertPage.jsx'
import Help from './pages/Help.jsx'
import Orders from './pages/Orders.jsx'
import Chats from './pages/Chats.jsx'
import Profile from './pages/Profile.jsx'

function RequireAuth({ children }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return <Loading />
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="map" element={<SafetyMap />} />
        <Route path="market" element={<Market />} />
        <Route path="sell" element={<RequireAuth><Sell /></RequireAuth>} />
        <Route path="alert" element={<AlertPage />} />
        <Route path="help" element={<Help />} />
        <Route path="login" element={<Login />} />
        <Route path="orders" element={<RequireAuth><Orders /></RequireAuth>} />
        <Route path="chats" element={<RequireAuth><Chats /></RequireAuth>} />
        <Route path="chats/:id" element={<RequireAuth><Chats /></RequireAuth>} />
        <Route path="me" element={<RequireAuth><Profile /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
