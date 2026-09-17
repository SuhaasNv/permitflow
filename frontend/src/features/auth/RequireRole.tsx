import { Navigate, Outlet, useLocation } from 'react-router-dom'

import type { Role } from '@/api/auth'
import { useAuth } from './AuthContext'
import { NotAvailableForRole } from '@/features/shared/states'

/** Route guard. The server re-checks the role on every request (SEC-001); this only shapes navigation. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(user.role)) return <NotAvailableForRole />
  return <Outlet />
}
