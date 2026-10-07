import { Link } from 'react-router-dom'

import { cn } from '@/lib/cn'

export interface StatCell {
  value: number | string
  label: string
  context?: string
  /** The one cell that needs attention, in the brand colour. */
  hot?: boolean
  to?: string
}

/** Four numbers in one bar: number, uppercase label, a context line (S-40; the design system's `StatStrip`). */
export function StatStrip({ cells, label = 'Key numbers', className }: { cells: StatCell[]; label?: string; className?: string }) {
  return (
    <div className={cn('pf-surface grid grid-cols-2 overflow-hidden lg:grid-cols-4', className)} role="list" aria-label={label}>
      {cells.map((cell, i) => {
        const inner = (
          <>
            <span
              className={cn(
                'text-[28px] font-semibold leading-9 tracking-[-0.015em] tabular-nums',
                cell.hot ? 'text-primary' : 'text-text',
              )}
            >
              {cell.value}
            </span>
            <span className="pf-eyebrow">{cell.label}</span>
            {cell.context ? <span className="text-[13px] leading-[18px] text-text-2">{cell.context}</span> : null}
          </>
        )
        const classes = cn(
          'flex min-w-0 flex-col gap-0.5 px-5 py-4 no-underline',
          i % 2 === 1 && 'border-l border-line',
          i >= 2 && 'border-t border-line lg:border-t-0',
          i === 2 && 'lg:border-l',
          i === 3 && 'lg:border-l',
        )
        return cell.to ? (
          <Link key={cell.label} to={cell.to} className={cn(classes, 'text-text hover:bg-surface-2')} role="listitem">
            {inner}
          </Link>
        ) : (
          <div key={cell.label} className={classes} role="listitem">
            {inner}
          </div>
        )
      })}
    </div>
  )
}
