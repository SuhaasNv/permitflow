import type { VerificationView } from '@/api/documents'
import { cn } from '@/lib/cn'

type Kind = 'pending' | 'running' | 'verified' | 'issues' | 'review' | 'unreadable' | 'failed' | 'unavailable'

const COPY: Record<VerificationView['status'], { kind: Kind; title: string; text: string }> = {
  pending: {
    kind: 'pending',
    title: 'Queued for checking',
    text: 'The automatic check will start shortly.',
  },
  running: {
    kind: 'running',
    title: 'Checking document…',
    text: 'Reading the file and comparing it with your form. Usually takes under a minute.',
  },
  verified: {
    kind: 'verified',
    title: 'Verified',
    text: 'The details in this document match your form.',
  },
  issues_found: {
    kind: 'issues',
    title: 'Issues found',
    text: 'Some details do not match your form. Check them before you submit.',
  },
  needs_review: {
    kind: 'review',
    title: 'Needs officer review',
    text: 'The check could not confirm this document. A licensing officer will review it.',
  },
  unreadable: {
    kind: 'unreadable',
    title: 'Could not read this document',
    text: 'Images cannot be read by the checker. The file is attached and will be reviewed by an officer as normal.',
  },
  failed: {
    kind: 'failed',
    title: 'Check failed',
    text: 'The checker returned an invalid result. You can re-run the check.',
  },
  unavailable: {
    kind: 'unavailable',
    title: 'Check unavailable',
    text: 'The checking service is not available right now. You can still submit; an officer will review the document.',
  },
}

const TINT: Record<Kind, string> = {
  pending: 'bg-neutral-soft text-text-2',
  running: 'bg-info-soft text-info',
  verified: 'bg-success-soft text-success',
  issues: 'bg-error-soft text-error',
  review: 'bg-warning-soft text-warning',
  unreadable: 'bg-neutral-soft text-text-2',
  failed: 'bg-error-soft text-error',
  unavailable: 'bg-neutral-soft text-text-2',
}

const PATHS: Record<Exclude<Kind, 'running'>, string> = {
  pending: 'M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  verified: 'M20 6 9 17l-5-5',
  issues: 'm10.3 3.9-8.5 14.6A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01',
  review: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  unreadable:
    'M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM10 8.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zm11 6.5-5-5L5 21',
  failed: 'M18 6 6 18M6 6l12 12',
  unavailable: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zm-17.1-7.1 14.2 14.2',
}

function Icon({ kind }: { kind: Kind }) {
  if (kind === 'running')
    return <span className="h-4 w-4 animate-spin rounded-full border-2 border-info-line border-t-info" aria-hidden="true" />
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={PATHS[kind]} />
    </svg>
  )
}

/** Operator-facing verification result: state, plain explanation, issues, what to do. No confidence numbers. */
export function VerificationBlock({ verification }: { verification: VerificationView }) {
  const copy = COPY[verification.status]
  const showSummary = Boolean(verification.summary) && verification.status !== 'running' && verification.status !== 'pending'
  const title =
    verification.status === 'issues_found'
      ? `${verification.issues.length} ${verification.issues.length === 1 ? 'issue' : 'issues'} found`
      : copy.title
  return (
    <div className="flex gap-3 border-t border-line px-4 py-3" aria-live="polite" data-verification={verification.status}>
      <span className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full', TINT[copy.kind])}>
        <Icon kind={copy.kind} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold">{title}</div>
        <div className="mt-0.5 text-[13px] text-text-2">{showSummary ? verification.summary : copy.text}</div>
        {verification.status === 'running' ? (
          <div className="mt-2 h-1 overflow-hidden rounded-sm bg-info-soft">
            <div className="h-full w-2/5 animate-[slide_1.6s_ease-in-out_infinite] rounded-sm bg-info" />
          </div>
        ) : null}
        {verification.issues.length > 0 ? (
          <ul className="mt-2.5 flex flex-col gap-2">
            {verification.issues.map((issue, i) => (
              <li key={i} className="flex gap-2.5 rounded-md border border-line bg-surface-2 px-3 py-2.5 text-[13px] leading-[19px]">
                <span
                  className={cn(
                    'mt-0.5 h-[18px] shrink-0 rounded border px-1.5 text-[11px] font-bold uppercase leading-4 tracking-[0.04em]',
                    issue.severity === 'high' && 'border-error-line bg-error-soft text-error',
                    issue.severity === 'medium' && 'border-warning-line bg-warning-soft text-warning',
                    issue.severity === 'low' && 'border-neutral-line bg-neutral-soft text-text-2',
                  )}
                >
                  {issue.severity}
                </span>
                <span>{issue.message}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {verification.missing_information.length > 0 ? (
          <div className="mt-2 text-[13px] text-text-2">
            <b>Missing:</b> {verification.missing_information.join('; ')}
          </div>
        ) : null}
        {verification.status === 'issues_found' ? (
          <div className="mt-2.5 text-[13px] text-text-2">
            <b>What to do:</b> check which value is correct and update the form or replace the document. You can still submit; an officer
            will review this.
          </div>
        ) : null}
      </div>
    </div>
  )
}
