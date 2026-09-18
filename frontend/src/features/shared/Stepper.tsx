import { Link } from 'react-router-dom'

import { cn } from '@/lib/cn'

type StepState = 'done' | 'current' | 'todo' | 'attention'

export interface Step {
  label: string
  state: StepState
  /** Completed and current steps link back; future steps stay quiet. */
  to?: string
}

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
        const filled = step.state === 'done' || step.state === 'attention'
        const marker = (
          <span
            className={cn(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[12px] font-semibold tabular-nums',
              'transition-[background-color,border-color,color,box-shadow] duration-[var(--dur-base)] ease-[var(--ease-out)]',
              step.state === 'done' && 'border-success bg-success text-white',
              step.state === 'attention' && 'border-warning bg-warning text-white',
              step.state === 'current' && 'border-text bg-text text-white shadow-[0_0_0_4px_var(--color-surface-3)]',
              step.state === 'todo' && 'border-line-strong bg-surface text-text-3',
            )}
            aria-hidden="true"
          >
            {step.state === 'done' ? CheckPath : i + 1}
          </span>
        )
        const label = (
          <span
            className={cn(
              'mt-2 max-w-full truncate px-0.5 text-[11px] leading-4 sm:text-[13px] sm:leading-[18px]',
              step.state === 'current' ? 'font-semibold text-text' : step.state === 'todo' ? 'text-text-3' : 'font-medium text-text-2',
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
          <li key={step.label} className="relative flex flex-col items-center" aria-current={step.state === 'current' ? 'step' : undefined}>
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
            {step.to && step.state !== 'todo' ? (
              <Link
                to={step.to}
                className="group flex flex-col items-center rounded-md px-1 no-underline hover:text-text"
                aria-label={`${step.label}: ${step.state === 'done' ? 'complete' : step.state === 'attention' ? 'needs attention' : 'current step'}`}
              >
                {inner}
              </Link>
            ) : (
              <span className="flex flex-col items-center px-1">{inner}</span>
            )}
          </li>
        )
      })}
    </ol>
  )
}
