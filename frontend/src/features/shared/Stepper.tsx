import { Link } from 'react-router-dom'

import { cn } from '@/lib/cn'

type StepState = 'done' | 'current' | 'todo' | 'attention' | 'locked'

export interface Step {
  label: string
  state: StepState
  /** Completed and current steps link back; future steps stay quiet. */
  to?: string
}

const LockPath = (
  <svg
    width="11"
    height="11"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    aria-hidden="true"
  >
    <rect x="4" y="11" width="16" height="10" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
)

const CheckPath = (
  <svg
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path className="pf-check" d="M20 6 9 17l-5-5" />
  </svg>
)

/** Journey indicator: number circles joined by rules that fill as steps complete. */
export function Stepper({ steps, className }: { steps: Step[]; className?: string }) {
  return (
    <ol className={cn('grid auto-cols-fr grid-flow-col', className)} aria-label="Application steps">
      {steps.map((step, i) => {
        const last = i === steps.length - 1
        const filled = step.state === 'done'
        const marker = (
          <span
            className={cn(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[12px] font-semibold tabular-nums',
              'transition-[background-color,border-color,color,box-shadow] duration-[var(--dur-base)] ease-[var(--ease-out)]',
              step.state === 'done' && 'border-success bg-success text-white',
              step.state === 'attention' && 'border-warning bg-warning text-white',
              step.state === 'current' && 'border-text bg-text text-white shadow-[0_0_0_4px_var(--color-surface-3)]',
              step.state === 'todo' && 'border-line-strong bg-surface text-text-3',
              step.state === 'locked' && 'border-line bg-surface-2 text-text-3',
            )}
            aria-hidden="true"
          >
            {step.state === 'done' ? CheckPath : step.state === 'locked' ? LockPath : i + 1}
          </span>
        )
        const label = (
          <span
            className={cn(
              'mt-2 max-w-full truncate px-0.5 text-[11px] leading-4 sm:text-[13px] sm:leading-[18px]',
              step.state === 'current'
                ? 'font-semibold text-text'
                : step.state === 'todo' || step.state === 'locked'
                  ? 'text-text-3'
                  : 'font-medium text-text-2',
            )}
          >
            {step.label}
          </span>
        )
        const inner = (
          <>
            {marker}
            {label}
          </>
        )
        return (
          <li
            key={step.label}
            className="relative flex min-w-0 flex-col items-center"
            aria-current={step.state === 'current' ? 'step' : undefined}
          >
            {!last ? (
              <span className="absolute left-[calc(50%+18px)] right-[calc(-50%+18px)] top-[13px] h-px bg-line" aria-hidden="true">
                <span
                  className={cn(
                    'block h-full origin-left bg-success transition-transform duration-[var(--dur-slow)] ease-[var(--ease-out)]',
                    filled ? 'scale-x-100' : 'scale-x-0',
                  )}
                />
              </span>
            ) : null}
            {step.to && step.state !== 'todo' && step.state !== 'locked' ? (
              <Link
                to={step.to}
                className="group flex w-full flex-col items-center rounded-md px-1 no-underline hover:text-text"
                aria-label={`${step.label}: ${step.state === 'done' ? 'complete' : step.state === 'attention' ? 'needs attention' : 'current step'}`}
              >
                {inner}
              </Link>
            ) : (
              <span
                className="flex w-full flex-col items-center px-1"
                aria-label={step.state === 'locked' ? `${step.label}: locked` : undefined}
              >
                {inner}
              </span>
            )}
          </li>
        )
      })}
    </ol>
  )
}
