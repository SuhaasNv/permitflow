import { PageHeader } from '@/features/shared/PageHeader'
import { EmptyPanel } from '@/features/shared/states'

export function AdminOverviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Operations overview"
        subtitle="Read-only oversight of applications, verification runs and users."
      />
      <EmptyPanel
        title="Nothing to show yet"
        description="Platform metrics and user management arrive in Sprint 3. Nothing is required from you right now."
      />
    </>
  )
}
