import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export interface Crumb {
  label: string
  to?: string
}

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] leading-[18px] text-text-3">
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`} className="flex items-center gap-2">
          {i > 0 ? (
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              aria-hidden="true"
              className="text-line-strong"
            >
              <path d="m9 6 6 6-6 6" />
            </svg>
          ) : null}
          {item.to ? (
            <Link to={item.to} className="text-text-2 no-underline hover:text-text hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="font-medium text-text" aria-current="page">
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  )
}

export interface PageHeaderProps {
  title: ReactNode
  eyebrow?: ReactNode
  subtitle?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
  className?: string
}

/** One per screen: optional eyebrow (reference, section), 28 px title, supporting line, right-aligned actions. */
export function PageHeader({ title, eyebrow, subtitle, meta, actions, className = '' }: PageHeaderProps) {
  return (
    <div className={`mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-8 ${className}`}>
      <div className="min-w-0">
        {eyebrow ? <div className="pf-eyebrow mb-2">{eyebrow}</div> : null}
        <h1 className="text-[28px] font-semibold leading-9 tracking-[-0.015em] text-text">{title}</h1>
        {subtitle ? <p className="mt-1.5 max-w-[68ch] text-[15px] leading-[22px] text-text-2">{subtitle}</p> : null}
        {meta ? <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-text-3">{meta}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}
