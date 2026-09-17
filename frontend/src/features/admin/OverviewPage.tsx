import { EmptyPanel } from '@/features/shared/states'
import { PageHeader } from '@/features/shared/PageHeader'

export function AdminOverviewPage() {
  return (
    <>
      <PageHeader title="Operations overview" />
      <EmptyPanel title="Nothing to show yet" description="Platform metrics arrive with US-070." />
    </>
  )
}
