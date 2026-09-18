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
