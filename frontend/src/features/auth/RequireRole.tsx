import { Navigate, Outlet, useLocation } from 'react-router-dom'

import type { Role } from '@/api/auth'
import { useAuth } from './AuthContext'
import { NotAvailableForRole, Skeleton } from '@/features/shared/states'

/** Route guard. The server re-checks the role on every request (SEC-001); this only shapes navigation. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user, ready } = useAuth()
  const location = useLocation()
  if (!ready) {
    return (
      <div className="mx-auto max-w-[1360px] px-4 py-8 sm:px-8" aria-busy="true" aria-label="Restoring your session">
        <Skeleton className="mb-3 h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />
  if (!roles.includes(user.role)) return <NotAvailableForRole />
  return <Outlet />
}
