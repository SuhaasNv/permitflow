import { useEffect, useState } from 'react'

import type { VerificationView } from '@/api/documents'
import { cn } from '@/lib/cn'

type Kind = 'pending' | 'running' | 'verified' | 'issues' | 'review' | 'unreadable' | 'failed' | 'unavailable'

const COPY: Record<VerificationView['status'], { kind: Kind; title: string; text: string }> = {
  pending: { kind: 'pending', title: 'Queued for checking', text: 'The automatic check will start shortly.' },
  running: {
    kind: 'running',
    title: 'Checking your document',
    text: 'Reading the file and comparing it with your form. Usually under a minute.',
  },
  verified: { kind: 'verified', title: 'Verified', text: 'The details in this document match your form.' },
  issues_found: {
    kind: 'issues',
    title: 'Needs your attention',
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
    title: 'Check did not complete',
    text: 'Your upload is safe. You can re-run the check, or continue and let the officer review it.',
  },
  unavailable: {
    kind: 'unavailable',
    title: 'Check unavailable right now',
    text: 'Your upload is safe. You can still submit; an officer will review the document.',
  },
}

const TINT: Record<Kind, string> = {
  pending: 'bg-surface-3 text-text-2',
  running: 'bg-info-soft text-info',
  verified: 'bg-success-soft text-success',
  issues: 'bg-warning-soft text-warning',
  review: 'bg-warning-soft text-warning',
  unreadable: 'bg-surface-3 text-text-2',
  failed: 'bg-error-soft text-error',
  unavailable: 'bg-surface-3 text-text-2',
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
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path className={kind === 'verified' ? 'pf-check' : undefined} d={PATHS[kind]} />
    </svg>
  )
}

const CHECK_STEPS = ['Reading the document', 'Extracting key details', 'Comparing with your application', 'Checking dates in the document']

/** Visual progress through the check while the server run is pending/running. The result always comes from the server. */
function CheckProgress({ started }: { started: boolean }) {
  const [step, setStep] = useState(started ? 1 : 0)
  useEffect(() => {
    if (!started) return
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, CHECK_STEPS.length - 1)), 700)
    return () => clearInterval(timer)
  }, [started])
  return (
    <ol className="mt-3 flex flex-col gap-1.5" aria-label="Check progress">
      {CHECK_STEPS.map((label, i) => {
        const state = i < step ? 'done' : i === step && started ? 'active' : 'todo'
        return (
          <li
            key={label}
            className={cn(
              'flex items-center gap-2.5 text-[13px] transition-colors duration-[var(--dur-base)]',
              state === 'todo' ? 'text-text-3' : 'text-text-2',
            )}
          >
            <span className="flex h-4 w-4 items-center justify-center" aria-hidden="true">
              {state === 'done' ? (
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="text-success"
                >
                  <path className="pf-check" d="M20 6 9 17l-5-5" />
                </svg>
              ) : state === 'active' ? (
                <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-info-line border-t-info" />
              ) : (
                <span className="h-[5px] w-[5px] rounded-full bg-line-strong" />
              )}
            </span>
            {label}
          </li>
        )
      })}
    </ol>
  )
}

/** Operator-facing verification result: state, plain explanation, issues, what to do. No confidence numbers. */
export function VerificationBlock({ verification, stale = false }: { verification: VerificationView; stale?: boolean }) {
  const copy = COPY[verification.status]
  const live = verification.status === 'running' || verification.status === 'pending'
  const showSummary = Boolean(verification.summary) && !live
  const title =
    live && stale
      ? 'This check is taking longer than expected'
      : verification.status === 'issues_found'
        ? `${verification.issues.length} ${verification.issues.length === 1 ? 'issue' : 'issues'} to check`
        : copy.title
  const text =
    live && stale
      ? 'Your upload is safe. Re-run the check, or continue and let the officer review the document.'
      : verification.error_reason === 'daily_limit_reached'
        ? 'The daily limit on automatic checks has been reached. Your upload is safe; you can still submit and an officer will review the document.'
        : copy.text
  return (
    <div
      key={verification.status}
      className="pf-enter-fast flex gap-3 border-t border-line px-4 py-4 sm:px-5"
      data-verification={verification.status}
    >
      <span
        className={cn(
          'mt-px flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors duration-[var(--dur-base)]',
          TINT[copy.kind],
        )}
      >
        <Icon kind={copy.kind} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sm font-semibold">{title}</span>
          <span className="text-xs text-text-3">AI-assisted check</span>
        </div>
        <div className="mt-0.5 text-[13px] leading-[19px] text-text-2">{showSummary ? verification.summary : text}</div>
        {live && !stale ? <CheckProgress started={verification.status === 'running'} /> : null}
        {verification.issues.length > 0 ? (
          <ul className="mt-3 divide-y divide-line rounded-md border border-line bg-surface-2">
            {verification.issues.map((issue, i) => (
              <li key={i} className="flex gap-3 px-3 py-2.5 text-[13px] leading-[19px]">
                <span
                  className={cn(
                    'mt-[3px] h-[7px] w-[7px] shrink-0 rounded-full',
                    issue.severity === 'high' && 'bg-error',
                    issue.severity === 'medium' && 'bg-warning',
                    issue.severity === 'low' && 'bg-line-strong',
                  )}
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1">{issue.message}</span>
                <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">{issue.severity}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {verification.missing_information.length > 0 ? (
          <div className="mt-2 text-[13px] leading-[19px] text-text-2">
            <span className="font-semibold">Could not find:</span> {verification.missing_information.join('; ')}
          </div>
        ) : null}
        {verification.status === 'issues_found' ? (
          <div className="mt-2.5 text-[13px] leading-[19px] text-text-2">
            <span className="font-semibold">What to do:</span> check which value is correct, then update the form or replace the document.
            You can still submit; the licensing officer sees the same findings.
          </div>
        ) : null}
      </div>
    </div>
  )
}
