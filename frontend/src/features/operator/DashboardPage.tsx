import { useAuth } from '@/features/auth/AuthContext'
import { EmptyPanel } from '@/features/shared/states'
import { PageHeader } from '@/features/shared/PageHeader'

export function OperatorDashboardPage() {
  const { user } = useAuth()
  const first = user?.full_name.split(' ').slice(-2).join(' ') ?? ''
  return (
    <>
      <PageHeader title={`Good day, ${first}`} subtitle="Here is what needs your attention today." />
      <EmptyPanel title="No applications yet" description="Creating an application arrives with the next story (US-010)." />
    </>
  )
}
