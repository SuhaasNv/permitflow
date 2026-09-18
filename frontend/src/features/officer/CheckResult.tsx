import type { OfficerVerification } from '@/api/officer'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'

type Kind = OfficerVerification['status']

const TITLE: Record<Kind, string> = {
  pending: 'Queued for checking',
  running: 'Checking',
  verified: 'Verified',
  issues_found: 'Issues found',
  needs_review: 'Needs your review',
  unreadable: 'Could not be read',
  failed: 'Check did not complete',
  unavailable: 'Check unavailable',
}

const TINT: Record<Kind, string> = {
  pending: 'bg-surface-3 text-text-2',
  running: 'bg-info-soft text-info',
  verified: 'bg-success-soft text-success',
  issues_found: 'bg-warning-soft text-warning',
  needs_review: 'bg-warning-soft text-warning',
  unreadable: 'bg-surface-3 text-text-2',
  failed: 'bg-error-soft text-error',
  unavailable: 'bg-surface-3 text-text-2',
}

const REASON: Record<string, string> = {
  provider_not_configured: 'No AI provider is configured; the mock or a live key is needed.',
  provider_unavailable: 'The AI service did not respond in time.',
  provider_error: 'The AI service returned an invalid result.',
  storage_error: 'The stored file could not be read.',
  internal_error: 'An internal error stopped the check.',
  interrupted: 'The check was interrupted by a restart.',
}

function Icon({ kind }: { kind: Kind }) {
  if (kind === 'running' || kind === 'pending')
    return <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-info-line border-t-info" aria-hidden="true" />
  const d =
    kind === 'verified'
      ? 'M20 6 9 17l-5-5'
      : kind === 'failed'
        ? 'M18 6 6 18M6 6l12 12'
        : kind === 'issues_found' || kind === 'needs_review'
          ? 'm10.3 3.9-8.5 14.6A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01'
          : 'M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z'
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  )
}

/** Officer-facing check result: outcome, confidence, model, every issue with its evidence. Advisory by design. */
export function CheckResult({ verification }: { verification: OfficerVerification }) {
  const v = verification
  const live = v.status === 'pending' || v.status === 'running'
  return (
    <div className="flex gap-3" data-verification={v.status}>
      <span className={cn('mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full', TINT[v.status])}>
        <Icon kind={v.status} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-sm font-semibold">{TITLE[v.status]}</span>
          {v.confidence !== null && !live ? (
            <span className="font-mono text-xs text-text-3">confidence {Math.round(v.confidence * 100)}%</span>
          ) : null}
          {v.model ? <span className="text-xs text-text-3">· {v.model}</span> : null}
          {v.finished_at ? <span className="text-xs text-text-3">· {formatDateTime(v.finished_at)}</span> : null}
        </div>
        {v.summary && !live ? <p className="mt-0.5 text-[13px] leading-[19px] text-text-2">{v.summary}</p> : null}
        {v.error_reason && (v.status === 'failed' || v.status === 'unavailable' || v.status === 'unreadable') ? (
          <p className="mt-0.5 text-[13px] leading-[19px] text-text-2">{REASON[v.error_reason] ?? v.error_reason}</p>
        ) : null}
        {v.issues.length > 0 ? (
          <ul className="mt-2.5 divide-y divide-line rounded-md border border-line bg-surface-2">
            {v.issues.map((issue, i) => (
              <li key={i} className="px-3 py-2.5 text-[13px] leading-[19px]">
                <div className="flex gap-3">
                  <span
                    className={cn(
                      'mt-[6px] h-[7px] w-[7px] shrink-0 rounded-full',
                      issue.severity === 'high' && 'bg-error',
                      issue.severity === 'medium' && 'bg-warning',
                      issue.severity === 'low' && 'bg-line-strong',
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2">
                      <span className="font-medium text-text">{issue.message}</span>
                      <span className="font-mono text-[11px] text-text-3">{issue.code}</span>
                      {issue.field ? <span className="font-mono text-[11px] text-text-3">{issue.field}</span> : null}
                    </div>
                    {issue.evidence ? (
                      <blockquote className="mt-1.5 border-l-2 border-line-strong pl-2.5 font-mono text-[12px] leading-[18px] text-text-2">
                        {issue.evidence}
                      </blockquote>
                    ) : null}
                  </div>
                  <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">{issue.severity}</span>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        {v.missing_information.length > 0 ? (
          <div className="mt-2 text-[13px] leading-[19px] text-text-2">
            <span className="font-semibold">Could not find:</span> {v.missing_information.join('; ')}
          </div>
        ) : null}
      </div>
    </div>
  )
}
