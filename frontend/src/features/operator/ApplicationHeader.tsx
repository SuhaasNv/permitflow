import type { ReactNode } from 'react'

import type { ApplicationView } from '@/api/applications'
import { Breadcrumb } from '@/features/shared/Breadcrumb'
import type { Crumb } from '@/features/shared/Breadcrumb'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { formatDate } from '@/lib/format'

export interface ApplicationHeaderProps {
  view: ApplicationView
  /** Trailing breadcrumb after the reference (for example "Documents"). */
  crumb?: string
  actions?: ReactNode
  /** Extra line under the status (for example "Step 2 of 6"). */
  aside?: ReactNode
}

function businessName(view: ApplicationView): string | null {
  const raw = view.sections[0]?.data.business_name
  return typeof raw === 'string' && raw.trim() ? raw : null
}

/** Consistent application header: reference eyebrow, business name as title, licence, status with explanation, meta line. */
export function ApplicationHeader({ view, crumb, actions, aside }: ApplicationHeaderProps) {
  const name = businessName(view)
  const crumbs: Crumb[] = [{ label: 'My applications', to: '/app/dashboard' }]
  if (crumb) {
    crumbs.push({ label: view.reference_no, to: `/app/applications/${view.id}` }, { label: crumb })
  } else {
    crumbs.push({ label: view.reference_no })
  }
  return (
    <div className="mb-6">
      <Breadcrumb items={crumbs} />
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between lg:gap-8">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <span className="font-mono text-[13px] font-medium tracking-[0.02em] text-text-2">{view.reference_no}</span>
            <span className="text-line-strong" aria-hidden="true">
              ·
            </span>
            <span className="text-[13px] text-text-2">{view.licence_title}</span>
          </div>
          <h1 className="mt-1.5 text-[28px] font-semibold leading-9 tracking-[-0.015em]">
            {name ?? <span className="text-text-2">New application</span>}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
            <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
            <span className="text-sm text-text-2">{view.status_explanation}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-text-3">
            <span>Created {formatDate(view.created_at)}</span>
            {view.revision_count > 0 ? <span>· Revision {view.revision_count}</span> : null}
            {aside}
          </div>
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  )
}
