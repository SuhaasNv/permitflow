import { Link } from "react-router-dom";

/** Brand mark (docs/design/brand) + wordmark. Never coloured red in the wordmark. */
export function Logo() {
  return (
    <Link
      to="/"
      className="flex items-center gap-2.5 text-text no-underline hover:text-text"
      aria-label="PermitFlow home"
    >
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#A8192A" />
        <path
          d="M9 10h14M9 16h9M9 22h4M16.5 22l2.5 2.5L24 18"
          fill="none"
          stroke="#fff"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-base font-bold tracking-tight">PermitFlow</span>
      <span className="hidden border-l border-line pl-2.5 text-xs text-text-3 sm:inline">
        Licensing Services
      </span>
    </Link>
  );
}
