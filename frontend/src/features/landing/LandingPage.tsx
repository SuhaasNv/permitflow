import { Link, Navigate } from 'react-router-dom'

import { homeFor, useAuth } from '@/features/auth/AuthContext'
import { Logo } from '@/features/shared/Logo'
import { StatusBadge } from '@/features/shared/StatusBadge'

const Check = (
  <svg
    width="15"
    height="15"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M20 6 9 17l-5-5" />
  </svg>
)

const NEED = [
  ['ACRA business profile', 'Issued within the last 6 months'],
  ['Floor plan of the premises', 'Showing the food preparation area'],
  ['Signed tenancy agreement', 'Covering the full licence period'],
  ['Food hygiene certificate', 'For the business or a named food handler'],
]

const STEPS = [
  ['Apply', 'Four short sections: business, premises, operations and declarations. Each one validates as you go.'],
  [
    'Automatic document checks',
    'Each upload is read and compared with your form so you can fix likely problems early. The checks are advisory: they never decide the outcome.',
  ],
  [
    'Officer review',
    'A licensing officer reviews your application. If something needs changing, you receive feedback tied to the exact section or document.',
  ],
  [
    'Site visit and outcome',
    'After a satisfactory review and a visit to the premises, you are notified of the decision here and by email.',
  ],
]

/** Public landing page (FR-031, design screen S-01). Signed-in users go straight to their workspace. */
export function LandingPage() {
  const { user, ready } = useAuth()
  if (ready && user) return <Navigate to={homeFor(user.role)} replace />
  return (
    <div className="flex min-h-screen flex-col bg-surface text-text">
      <div className="flex h-7 items-center gap-2 bg-text px-4 text-xs text-[#c5cbd3] sm:px-6">
        <span className="font-semibold text-white">PermitFlow</span>
        <span>· licensing services for food establishments</span>
      </div>
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 sm:px-8">
          <Logo />
          <nav className="flex items-center gap-4 text-sm font-medium sm:gap-6" aria-label="Site">
            <a href="#how" className="hidden text-text-2 no-underline hover:text-text sm:inline">
              How it works
            </a>
            <a href="#need" className="hidden text-text-2 no-underline hover:text-text sm:inline">
              What you need
            </a>
            <Link
              to="/login"
              className="inline-flex h-9 items-center rounded-md bg-primary px-3.5 text-sm font-semibold text-white no-underline hover:bg-primary-hover hover:text-white"
            >
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      <section className="border-b border-line">
        <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-14 sm:px-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-16 lg:py-[72px]">
          <div>
            <div className="mb-3.5 text-xs font-semibold uppercase tracking-[0.08em] text-primary">Food Establishment Licence</div>
            <h1 className="max-w-[720px] text-[32px] font-semibold leading-10 tracking-tight sm:text-[40px] sm:leading-[48px]">
              Apply for a food establishment licence and respond to the licensing officer in one place.
            </h1>
            <p className="mt-4 max-w-[640px] text-base leading-7 text-text-2 sm:text-lg">
              Complete the application in sections, upload your documents and see automatic checks before you submit. If the licensing
              office needs changes, you update only what was flagged. Nothing you entered is lost.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                to="/login"
                className="inline-flex h-12 items-center rounded-md bg-primary px-6 text-sm font-semibold text-white no-underline hover:bg-primary-hover hover:text-white"
              >
                Sign in to apply
              </Link>
              <a
                href="#how"
                className="inline-flex h-12 items-center rounded-md border border-line-strong bg-surface px-6 text-sm font-semibold text-text no-underline hover:bg-surface-2"
              >
                How it works
              </a>
            </div>
            <p className="mt-4 text-xs text-text-3">Takes about 20 minutes. You can save a draft and return later.</p>
          </div>
          <div id="need" className="rounded-lg border border-line bg-surface p-5 shadow-[var(--shadow-1)] lg:mt-11">
            <div className="mb-3 text-[13px] font-semibold">What you need</div>
            <ul className="flex flex-col gap-2.5 text-[13px]">
              {NEED.map(([title, sub]) => (
                <li key={title} className="flex items-start gap-2.5">
                  <span className="mt-0.5 text-success">{Check}</span>
                  <div>
                    <b>{title}</b>
                    <div className="text-text-2">{sub}</div>
                  </div>
                </li>
              ))}
            </ul>
            <p className="mt-3.5 text-xs leading-[18px] text-text-3">
              PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: it is the only format the automatic check can read.
            </p>
          </div>
        </div>
      </section>

      <section id="how" className="border-b border-line">
        <div className="mx-auto max-w-[1440px] px-4 py-14 sm:px-8">
          <h2 className="mb-6 text-2xl font-semibold leading-8">How it works</h2>
          <ol className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map(([title, desc], i) => (
              <li key={title}>
                <div className="mb-2.5 font-mono text-[13px] font-medium text-primary">0{i + 1}</div>
                <div className="mb-1.5 text-base font-semibold">{title}</div>
                <p className="text-sm leading-[21px] text-text-2">{desc}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-[1440px] px-4 py-14 sm:px-8">
          <h2 className="mb-6 text-2xl font-semibold leading-8">Track every step</h2>
          <div className="grid max-w-[960px] gap-8 sm:grid-cols-3">
            <div>
              <div className="mb-2">
                <StatusBadge label="Under Review" tone="info" />
              </div>
              <p className="text-[13px] text-text-2">The licensing office is working on it. Nothing is needed from you.</p>
            </div>
            <div>
              <div className="mb-2">
                <StatusBadge label="Pending Pre-Site Resubmission" tone="warning" />
              </div>
              <p className="text-[13px] text-text-2">Feedback is waiting for you. Only the flagged parts reopen for editing.</p>
            </div>
            <div>
              <div className="mb-2">
                <StatusBadge label="Approved" tone="success" />
              </div>
              <p className="text-[13px] text-text-2">
                The outcome, with the officer's note, stays on your dashboard with the full history.
              </p>
            </div>
          </div>
          <p className="mt-5 max-w-[640px] text-text-2">
            Every application keeps a complete record: each revision you submitted, every comment from the licensing office, and when each
            status changed.
          </p>
        </div>
      </section>

      <footer className="mt-auto border-t border-line">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-8 text-[13px] text-text-3 sm:px-8">
          <span>© 2026 PermitFlow</span>
          <Link to="/" className="text-text-2">
            Privacy
          </Link>
          <Link to="/" className="text-text-2">
            Terms of use
          </Link>
          <Link to="/" className="text-text-2">
            Accessibility
          </Link>
          <Link to="/login" className="ml-auto text-text-2">
            Staff sign-in
          </Link>
        </div>
      </footer>
    </div>
  )
}
