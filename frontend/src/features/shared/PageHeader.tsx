import type { ReactNode } from 'react'

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
