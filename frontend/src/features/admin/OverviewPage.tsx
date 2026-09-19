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
        description="The administration screens (US-070 to US-073) are deferred beyond this release. Nothing is required from you."
      />
    </>
  )
}
