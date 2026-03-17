import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/use-auth'

export function AdminGuard() {
  const { isAdmin } = useAuth()

  if (!isAdmin) {
    return <Navigate replace to="/projects" />
  }

  return <Outlet />
}
