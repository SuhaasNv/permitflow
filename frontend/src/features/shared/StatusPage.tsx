import { useQuery } from '@tanstack/react-query'

import { getHealth } from '@/api/health'

/** Temporary landing for the skeleton: shows API health. Replaced by the real screens from US-001. */
export function StatusPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })
  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <h1 className="text-[26px] font-semibold leading-8 tracking-tight">PermitFlow</h1>
      <p className="mt-1 text-text-2">Application skeleton. Screens arrive with the next stories.</p>
      <dl className="mt-6 grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 rounded-lg border border-line bg-surface p-5 text-sm">
        <dt className="text-text-3">API</dt>
        <dd data-testid="api-status" className="font-medium">
          {health.isPending ? 'Checking…' : health.isError ? 'Unreachable' : health.data.status}
        </dd>
        <dt className="text-text-3">Database</dt>
        <dd className="font-medium">{health.data?.database ?? '–'}</dd>
      </dl>
    </div>
  )
}
