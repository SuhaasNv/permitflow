import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { homeFor, useAuth } from '@/features/auth/AuthContext'
import { buttonClasses } from '@/features/shared/Button'
import { Logo } from '@/features/shared/Logo'
import { Reveal } from '@/features/shared/Reveal'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { cn } from '@/lib/cn'

const glyph = (children: ReactNode) => (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
)

/** Document-type glyphs: semantic, one per required document, never decorative. */
const NEED: { title: string; sub: string; icon: ReactNode }[] = [
  {
    title: 'Business profile (ACRA)',
    sub: 'Issued within the last 6 months',
    icon: glyph(
      <>
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z" />
        <path d="M14 2v6h6M8 13h8M8 17h5" />
      </>,
    ),
  },
  {
    title: 'Floor plan of the premises',
    sub: 'Showing the food preparation area',
    icon: glyph(
      <>
        <rect x="3" y="3" width="18" height="18" rx="1.5" />
        <path d="M3 12h9M12 3v9M12 12v9M12 12h9M16 21v-4" />
      </>,
    ),
  },
  {
    title: 'Signed tenancy agreement',
    sub: 'Covering the full licence period',
    icon: glyph(
      <>
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z" />
        <path d="M14 2v6h6" />
        <path d="M8 17c1-2 2-2 3 0s2 2 3 0 2-2 3 0" />
      </>,
    ),
  },
  {
    title: 'Food hygiene certificate',
    sub: 'For the business or a named food handler',
    icon: glyph(
      <>
        <circle cx="12" cy="9" r="5.5" />
        <path d="m9.5 13.5-1.5 7 4-2.2 4 2.2-1.5-7M9.8 9l1.6 1.6L14.3 7.6" />
      </>,
    ),
  },
]

const STEPS: [string, string][] = [
  ['Apply in sections', 'Business, premises, operations and declarations. Each section validates as you go and saves as a draft.'],
  ['Upload and check', 'Each document is read and compared with your form so likely problems surface before you submit.'],
  ['Officer review', 'A licensing officer reviews the application. Feedback is tied to the exact section or document it concerns.'],
  ['Site visit and outcome', 'After a satisfactory review and a visit to the premises, the decision appears in your workspace.'],
]

const JOURNEY: { label: string; tone: Tone; note: string }[] = [
  { label: 'Draft', tone: 'neutral', note: 'Save and return any time' },
  { label: 'Submitted', tone: 'info', note: 'Revision 1 recorded' },
  { label: 'Under Review', tone: 'info', note: 'Nothing needed from you' },
  { label: 'Pending Pre-Site Resubmission', tone: 'warning', note: 'Only flagged parts reopen' },
  { label: 'Pending Site Visit', tone: 'info', note: 'An officer contacts you' },
  { label: 'Approved', tone: 'success', note: 'Outcome and history kept' },
]

function useScrolled(threshold = 12): boolean {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [threshold])
  return scrolled
}

/** Public landing page (FR-031, design screen S-01). Signed-in users go straight to their workspace. */
export function LandingPage() {
  const { user, ready } = useAuth()
  const scrolled = useScrolled()
  if (ready && user) return <Navigate to={homeFor(user.role)} replace />
  return (
    <div className="flex min-h-screen flex-col bg-surface text-text">
      <header
        className={cn(
          'sticky top-0 z-30 border-b transition-[background-color,border-color,box-shadow] duration-[var(--dur-base)] ease-[var(--ease-out)]',
          scrolled ? 'border-line bg-surface/90 shadow-[0_1px_0_rgba(16,24,40,0.02)] backdrop-blur-md' : 'border-transparent bg-surface',
        )}
      >
        <div
          className={cn(
            'mx-auto flex max-w-[1440px] items-center justify-between px-5 transition-[height] duration-[var(--dur-base)] ease-[var(--ease-out)] sm:px-10',
            scrolled ? 'h-14' : 'h-[72px]',
          )}
        >
          <Logo />
          <nav className="flex items-center gap-3 sm:gap-5" aria-label="Site">
            <a href="#how" className="hidden text-sm font-medium text-text-2 no-underline hover:text-text md:inline">
              How it works
            </a>
            <a href="#journey" className="hidden text-sm font-medium text-text-2 no-underline hover:text-text md:inline">
              Track your application
            </a>
            <Link to="/login" className={buttonClasses('primary', 'sm', 'h-9 px-4')}>
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero: full width, two columns, editorial display type; the document panel sits on a tinted backdrop. */}
      <section className="relative overflow-hidden border-b border-line">
        <div className="mx-auto grid max-w-[1440px] gap-12 px-5 pb-16 pt-14 sm:px-10 lg:grid-cols-[58%_minmax(0,1fr)] lg:gap-20 lg:pb-24 lg:pt-20">
          <div className="pf-stagger">
            <div className="pf-eyebrow mb-5 text-primary">Food Establishment Licence · Singapore</div>
            <h1 className="font-display max-w-[16ch] text-[44px] leading-[1.02] tracking-[-0.015em] sm:text-[60px] lg:text-[72px]">
              <span className="text-primary">Apply once.</span> Respond to the officer <em className="text-text-2">in the same place.</em>
            </h1>
            <p className="mt-7 max-w-[54ch] text-[17px] leading-[27px] text-text-2 sm:text-lg sm:leading-[29px]">
              Complete the application in sections, upload your documents and see automatic checks before you submit. If the licensing
              office needs changes, you update only what was flagged. Nothing you entered is lost.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link to="/login" className={buttonClasses('primary', 'lg')}>
                Sign in to apply
              </Link>
              <a href="#how" className={buttonClasses('secondary', 'lg')}>
                How it works
              </a>
            </div>
            <dl className="mt-10 grid max-w-[520px] grid-cols-3 gap-6 border-t border-line pt-6 text-[13px] leading-[18px] text-text-3">
              <div>
                <dt className="font-semibold text-text">About 20 minutes</dt>
                <dd>to complete, with drafts saved</dd>
              </div>
              <div>
                <dt className="font-semibold text-text">4 documents</dt>
                <dd>checked automatically on upload</dd>
              </div>
              <div>
                <dt className="font-semibold text-text">One officer</dt>
                <dd>makes every decision</dd>
              </div>
            </dl>
          </div>
          {/* At lg the panel sits centred inside the ink band, which bleeds to the right edge; below lg it flows under the copy. */}
          <div
            id="need"
            className="pf-enter lg:absolute lg:inset-y-0 lg:right-0 lg:flex lg:w-[42%] lg:items-center lg:justify-center lg:overflow-hidden lg:bg-ink lg:px-10"
            style={{ animationDelay: '160ms' }}
          >
            <span className="pf-band-glow pf-band-glow-a hidden lg:block" aria-hidden="true" />
            <span className="pf-band-glow pf-band-glow-b hidden lg:block" aria-hidden="true" />
            <div className="pf-surface relative w-full overflow-hidden shadow-[var(--shadow-2)] lg:max-w-[540px] lg:shadow-[0_24px_60px_-20px_rgba(0,0,0,0.55)]">
              <div className="flex items-center justify-between border-b border-line bg-surface-2 px-5 py-3.5">
                <h2 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-text-2">What you need</h2>
                <span className="font-mono text-xs text-text-3">4 documents</span>
              </div>
              <ol className="pf-stagger divide-y divide-line">
                {NEED.map((item, i) => (
                  <li key={item.title} className="flex items-center gap-4 px-5 py-4">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
                      {item.icon}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-[11px] text-text-3">0{i + 1}</span>
                        <span className="text-[15px] font-semibold leading-[22px]">{item.title}</span>
                      </div>
                      <div className="text-[13px] leading-[18px] text-text-2">{item.sub}</div>
                    </div>
                    <span className="rounded border border-line bg-surface px-1.5 font-mono text-[11px] leading-[18px] text-text-3">
                      PDF
                    </span>
                  </li>
                ))}
              </ol>
              <p className="border-t border-line bg-surface-2 px-5 py-3 text-[12px] leading-[18px] text-text-3">
                PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: it is the only format the automatic check can read.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it works: four steps on a single rule, revealed in sequence. */}
      <section id="how" className="border-b border-line bg-bg">
        <div className="mx-auto max-w-[1440px] px-5 py-16 sm:px-10 lg:py-20">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-16">
            <Reveal>
              <div className="pf-eyebrow mb-3">How it works</div>
              <h2 className="font-display text-[34px] leading-[1.1] sm:text-[40px]">Four steps, one record.</h2>
              <p className="mt-4 text-[15px] leading-[23px] text-text-2">
                Every revision you submit, every comment from the licensing office and every status change stays with the application.
              </p>
            </Reveal>
            <ol className="grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map(([title, desc], i) => (
                <Reveal key={title} as="li" delay={i * 90} className="relative border-t border-line-strong pt-5">
                  <span className="absolute -top-px left-0 h-px w-10 bg-primary" aria-hidden="true" />
                  <div className="mb-3 font-mono text-[13px] text-text-3">0{i + 1}</div>
                  <div className="mb-2 text-[17px] font-semibold leading-6">{title}</div>
                  <p className="text-sm leading-[21px] text-text-2">{desc}</p>
                </Reveal>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* Journey: the status vocabulary on a rule that draws itself as you scroll to it. */}
      <section id="journey" className="border-b border-line">
        <div className="mx-auto max-w-[1440px] px-5 py-16 sm:px-10 lg:py-20">
          <Reveal className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="pf-eyebrow mb-3">Track your application</div>
              <h2 className="font-display text-[34px] leading-[1.1] sm:text-[40px]">Always know where it stands.</h2>
            </div>
            <p className="max-w-[46ch] text-[15px] leading-[23px] text-text-2">
              Each status tells you whether anything is needed from you. Amber means the licensing office is waiting for you.
            </p>
          </Reveal>
          <Reveal as="div" threshold={0.35} className="relative mt-10">
            <span className="absolute left-0 top-0 hidden h-px w-full bg-line lg:block" aria-hidden="true" />
            <span className="pf-journey-line absolute left-0 top-0 hidden h-px w-full bg-ink lg:block" aria-hidden="true" />
            <ol className="grid grid-cols-1 gap-6 sm:grid-cols-3 lg:grid-cols-6">
              {JOURNEY.map((s, i) => (
                <li key={s.label} className="relative pt-5" style={{ transitionDelay: `${200 + i * 180}ms` }}>
                  <span className="absolute left-0 top-0 h-px w-full bg-line lg:hidden" aria-hidden="true" />
                  <span
                    className={cn(
                      'pf-journey-dot absolute -top-[4px] left-0 h-[9px] w-[9px] rounded-full ring-4 ring-surface',
                      i === JOURNEY.length - 1 ? 'bg-success' : s.tone === 'warning' ? 'bg-warning' : 'bg-ink',
                    )}
                    style={{ transitionDelay: `${260 + i * 200}ms` }}
                    aria-hidden="true"
                  />
                  <div className="pf-reveal is-in" style={{ transitionDelay: `${300 + i * 200}ms` }}>
                    <StatusBadge label={s.label} tone={s.tone} />
                    <p className="mt-2.5 text-[13px] leading-[18px] text-text-2">{s.note}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Reveal>
        </div>
      </section>

      {/* Advisory AI: what the checks do and do not do. */}
      <section className="bg-ink text-white">
        <div className="mx-auto grid max-w-[1440px] gap-10 px-5 py-16 sm:px-10 lg:grid-cols-2 lg:gap-20 lg:py-20">
          <Reveal>
            <div className="pf-eyebrow mb-3 text-[#aeb6c2]">Automatic document checks</div>
            <h2 className="font-display text-[34px] leading-[1.1] sm:text-[40px]">Checks help you. Officers decide.</h2>
          </Reveal>
          <dl className="grid grid-cols-1 gap-8 text-[15px] leading-[23px] sm:grid-cols-2">
            <Reveal delay={100} className="border-t border-white/20 pt-4">
              <dt className="mb-2 font-semibold">What the check does</dt>
              <dd className="text-[#c5cbd3]">
                Reads each PDF you upload, picks out the business name, UEN, address and dates, and compares them with your form. It tells
                you plainly when something differs.
              </dd>
            </Reveal>
            <Reveal delay={200} className="border-t border-white/20 pt-4">
              <dt className="mb-2 font-semibold">What it never does</dt>
              <dd className="text-[#c5cbd3]">
                Approve, reject or change your application. Every decision is made by a licensing officer, who sees the same findings and
                the evidence behind them.
              </dd>
            </Reveal>
          </dl>
        </div>
      </section>

      <footer className="mt-auto">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-5 py-8 text-[13px] text-text-3 sm:flex-row sm:items-center sm:px-10">
          <span>© 2026 PermitFlow</span>
          <span className="hidden sm:inline">·</span>
          <span>A fictional licensing service built for an engineering assessment. Not a government service.</span>
        </div>
      </footer>
    </div>
  )
}
