import { useParams } from 'react-router-dom'

import { Breadcrumb, PageHeader } from '@/features/shared/PageHeader'
import { EmptyPanel } from '@/features/shared/states'

/** Placeholder until US-021 ships the case review workspace. Honest about what is missing. */
export function OfficerCasePage() {
  const { id = '' } = useParams()
  return (
    <>
      <Breadcrumb items={[{ label: 'Review queue', to: '/officer/queue' }, { label: 'Case' }]} />
      <PageHeader eyebrow="Licensing officer" title="Case review" subtitle={`Application ${id.slice(0, 8)}…`} />
      <EmptyPanel
        title="The case view is not built yet"
        description="The full submission, document checks and review actions arrive with US-021. Nothing on this screen is hidden."
      />
    </>
  )
}
