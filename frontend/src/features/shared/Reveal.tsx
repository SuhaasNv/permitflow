import type { ElementType, ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/cn'

export interface RevealProps {
  children: ReactNode
  className?: string
  /** Milliseconds to wait after entering the viewport (used to stagger siblings). */
  delay?: number
  as?: ElementType
  /** Fraction of the element that must be visible before it reveals. */
  threshold?: number
}

/**
 * Scroll reveal: renders hidden (`.pf-reveal`) and adds `is-in` once the element enters the viewport.
 * Reveals immediately where IntersectionObserver is unavailable (tests, old browsers) and under reduced motion the
 * CSS collapses the transition, so nothing is ever stuck invisible.
 */
export function Reveal({ children, className, delay = 0, as: Tag = 'div', threshold = 0.2 }: RevealProps) {
  const ref = useRef<HTMLElement | null>(null)
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined')

  useEffect(() => {
    const el = ref.current
    if (!el || visible) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold, rootMargin: '0px 0px -8% 0px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold, visible])

  return (
    <Tag ref={ref} className={cn('pf-reveal', visible && 'is-in', className)} style={delay ? { transitionDelay: `${delay}ms` } : undefined}>
      {children}
    </Tag>
  )
}
