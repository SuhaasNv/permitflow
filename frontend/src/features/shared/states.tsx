import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { AppError } from '@/api/client'
import { cn } from '@/lib/cn'
import { Button } from './Button'

interface PanelProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
  tone?: 'neutral' | 'error'
  footnote?: string
  bordered?: boolean
}

/** Balanced empty/error state: small icon, one-line title, one sentence, optional action. Never a giant white box. */
function Panel({ icon, title, description, action, tone = 'neutral', footnote, bordered = true }: PanelProps) {
  return (
    <div
      className={cn(
        'pf-enter flex flex-col items-center px-6 py-14 text-center text-text-2',
        bordered && 'rounded-lg border border-dashed border-line-strong/70 bg-surface/60',
      )}
      role="status"
    >
      <div
        className={cn(
          'mb-4 flex h-11 w-11 items-center justify-center rounded-full',
          tone === 'error' ? 'bg-error-soft text-error' : 'bg-surface-3 text-text-2',
        )}
      >
        {icon}
      </div>
      <div className="text-[17px] font-semibold leading-6 text-text">{title}</div>
      <div className="mt-1 max-w-[44ch] text-sm leading-[21px]">{description}</div>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
      {footnote ? <div className="mt-6 text-xs text-text-3">{footnote}</div> : null}
    </div>
  )
}

const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' } as const

const LockIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)
const XIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
)
const SearchIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </svg>
)
const FolderIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
)
const CheckIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
    <path d="M20 6 9 17l-5-5" />
  </svg>
)

export function NotAvailableForRole() {
  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <Panel
        icon={LockIcon}
        title="Not available for your role"
        description="This page is for a different type of account. If you think this is a mistake, contact your administrator."
        action={
          <Link to="/" className="text-sm font-semibold">
            Go to my workspace
          </Link>
        }
      />
    </div>
  )
}

export function NotFoundPanel({
  backTo,
  backLabel,
  title = 'Application not found',
  description = 'It may have been removed, or the link is incorrect.',
}: {
  backTo: string
  backLabel: string
  title?: string
  description?: string
}) {
  return (
    <Panel
      icon={SearchIcon}
      title={title}
      description={description}
      action={
        <Link to={backTo} className="text-sm font-semibold">
          {backLabel}
        </Link>
      }
    />
  )
}

/** What happened, and what the user can do. Never a stack trace; the request ID is there for support. */
export function ErrorPanel({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const requestId = error instanceof AppError ? error.requestId : undefined
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <Panel
      icon={XIcon}
      tone="error"
      title="We could not load this page"
      description={`${message} Nothing you entered has been lost.`}
      footnote={requestId ? `Request ID ${requestId}` : undefined}
      action={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Try again
          </Button>
        ) : undefined
      }
    />
  )
}

export function EmptyPanel({
  title,
  description,
  action,
  footnote,
  done,
}: {
  title: string
  description: string
  action?: ReactNode
  footnote?: string
  /** "All caught up" flavour: check icon instead of a folder. */
  done?: boolean
}) {
  return <Panel icon={done ? CheckIcon : FolderIcon} title={title} description={description} action={action} footnote={footnote} />
}

/** Shimmering placeholder. Compose several to mirror the layout that is loading. */
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={cn('pf-skeleton', className)} aria-hidden="true" />
}

/** Header skeleton shared by the application screens (eyebrow, title, subtitle). */
export function PageSkeleton({ children, label }: { children?: ReactNode; label: string }) {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label={label}>
      <div className="flex flex-col gap-2.5">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-8 w-2/5" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      {children}
    </div>
  )
}
