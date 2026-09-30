import { Link } from 'react-router-dom'

import { cn } from '@/lib/cn'

interface PolicyLinksProps {
  className?: string
  /** Landmark name; override it where the page already has a nav called "Policies" (the policy pages). */
  label?: string
}

/** The footer's policy links (Privacy, Terms, Cookies), shared by every public page. */
export function PolicyLinks({ className, label = 'Policies' }: PolicyLinksProps) {
  return (
    <nav aria-label={label} className={cn('flex gap-4', className)}>
      <Link to="/privacy" className="text-text-3 no-underline hover:text-text">
        Privacy
      </Link>
      <Link to="/terms" className="text-text-3 no-underline hover:text-text">
        Terms
      </Link>
      <Link to="/cookies" className="text-text-3 no-underline hover:text-text">
        Cookies
      </Link>
    </nav>
  )
}
