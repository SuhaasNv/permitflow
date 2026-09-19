import { useId } from 'react'

import { cn } from '@/lib/cn'

interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  /** Accessible name. */
  label: string
  /** Short placeholder; defaults to the label. */
  placeholder?: string
  className?: string
}

/** Compact search input for list screens. Filters client-side; the parent decides what "matches" means. */
export function SearchBox({ value, onChange, label, placeholder, className }: SearchBoxProps) {
  const id = useId()
  return (
    <div className={cn('relative', className)}>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        aria-hidden="true"
        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-3"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input
        id={id}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? label}
        autoComplete="off"
        spellCheck={false}
        className={cn(
          'h-10 w-full rounded-md border border-line-strong bg-surface pl-8 pr-2.5 text-[13px] sm:h-8 text-text placeholder:text-text-3/70',
          'transition-[border-color,box-shadow] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
          'hover:border-text-3 focus:border-focus focus:shadow-[0_0_0_3px_rgba(23,92,211,0.16)] focus:outline-none',
          '[&::-webkit-search-cancel-button]:cursor-pointer',
        )}
      />
    </div>
  )
}
