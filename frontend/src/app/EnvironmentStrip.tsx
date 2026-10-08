import { useBuildInfo } from '@/features/releases/queries'

/** A thin amber strip above every page while the API reports any environment other than production (US-109),
 * so test data is never mistaken for real applications. Nothing while /health is loading or has failed, so
 * production never flashes it. Static and in the normal flow; the words carry the meaning, with an icon. */
export function EnvironmentStrip() {
  const { data } = useBuildInfo()
  if (!data || data.environment === 'production') return null
  return (
    <div
      role="region"
      aria-label="Environment notice"
      className="pf-env-strip flex min-h-7 items-center gap-2 border-b border-warning-line bg-warning-soft px-4 text-xs font-medium text-warning sm:px-6"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className="shrink-0"
      >
        <path d="m10.29 3.86-8.18 14.14A2 2 0 0 0 3.82 21h16.36a2 2 0 0 0 1.71-3l-8.18-14.14a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" />
      </svg>
      <span className="py-1">
        Development environment: test data only<span className="hidden sm:inline">, not the live service</span>
      </span>
    </div>
  )
}
