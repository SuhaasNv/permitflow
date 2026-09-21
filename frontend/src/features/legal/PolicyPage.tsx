import { useEffect } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { AppShell } from '@/app/AppShell'
import { useAuth } from '@/features/auth/AuthContext'
import { buttonClasses } from '@/features/shared/Button'
import { Logo } from '@/features/shared/Logo'
import { OPERATOR_URL, POLICIES } from './content'
import type { PolicySlug } from './content'

const SLUGS: PolicySlug[] = ['privacy', 'terms', 'cookies']

function isSlug(value: string | undefined): value is PolicySlug {
  return SLUGS.includes(value as PolicySlug)
}

function anchorOf(heading: string): string {
  return heading
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

/** The policy itself: the policy switcher and the section list on the left from 1024 px, the text on the
 * right at a reading measure; one column below that. Used standalone and inside the app shell. */
function PolicyBody({ slug }: { slug: PolicySlug }) {
  const policy = POLICIES[slug]
  return (
    <div className="lg:grid lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-x-14">
      <aside className="mb-8 lg:mb-0">
        <div className="lg:sticky lg:top-6">
          <nav aria-label="Policies" className="flex flex-wrap gap-x-5 gap-y-1 text-sm lg:flex-col lg:gap-y-0">
            {SLUGS.map((s) => (
              <Link
                key={s}
                to={`/${s}`}
                aria-current={s === slug ? 'page' : undefined}
                // Every link at least 24 px tall (the accessibility gate's target-size rule) with a little air between rows.
                className={`inline-flex min-h-7 items-center no-underline ${s === slug ? 'font-semibold text-text' : 'text-text-2 hover:text-text'}`}
              >
                {POLICIES[s].title}
              </Link>
            ))}
          </nav>
          <nav aria-label="On this page" className="mt-6 hidden lg:block">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-text-3">On this page</p>
            <ol className="mt-1 flex flex-col text-[13px] leading-[18px]">
              {policy.sections.map((section) => (
                <li key={section.heading}>
                  <a href={`#${anchorOf(section.heading)}`} className="inline-flex min-h-7 items-center py-1 text-text-2 no-underline hover:text-text">
                    {section.heading}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        </div>
      </aside>
      <article className="max-w-[820px]">
        <h1 className="font-display text-[36px] leading-[1.05] sm:text-[42px]">{policy.title}</h1>
        <p className="mt-3 text-[13px] text-text-3">Last reviewed {policy.reviewed}</p>
        <p className="mt-6 text-[17px] leading-[26px] text-text-2">{policy.summary}</p>

        {policy.sections.map((section) => (
          <section key={section.heading} id={anchorOf(section.heading)} className="mt-10 scroll-mt-6">
            <h2 className="text-[20px] font-semibold leading-[28px]">{section.heading}</h2>
            {section.paragraphs.map((p) => (
              <p key={p} className="mt-3 leading-[24px]">
                {p}
              </p>
            ))}
            {section.bullets && (
              <ul className="mt-3 list-disc space-y-2 pl-6 leading-[24px]">
                {section.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            )}
          </section>
        ))}

        <p className="mt-12 border-t border-line pt-6 text-sm text-text-3">
          Questions or requests: open an issue at{' '}
          <a href={OPERATOR_URL} rel="noreferrer">
            {OPERATOR_URL.replace('https://', '')}
          </a>
          .
        </p>
      </article>
    </div>
  )
}

/** Public policy pages (US-057): privacy, terms, cookies. One layout, content from `content.ts`.
 * Signed in, the policy opens inside the app shell (the rail, the bottom tabs, the footer) so it reads
 * like any other page and follows the rail as it opens and collapses; signed out, the public frame. */
export function PolicyPage() {
  const slug = useLocation().pathname.replace(/^\//, '')
  const { user, ready } = useAuth()
  // The public routes sit outside the app shell's ScrollRestoration, so a footer link at the bottom of the
  // landing page would otherwise open the policy still scrolled to the bottom.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [slug])
  if (!isSlug(slug)) return <Navigate to="/privacy" replace />
  // Only once the provider is ready: the shell's bell fetches on mount, and a child's effect runs before
  // the provider's, so a shell mounted from the stored session alone would call without the token.
  if (user && ready) {
    return (
      <AppShell>
        <PolicyBody slug={slug} />
      </AppShell>
    )
  }
  if (user) return null
  return (
    <div className="flex min-h-screen flex-col bg-surface text-text">
      <a href="#main" className="pf-skip-link">
        Skip to content
      </a>
      <header className="border-b border-line">
        <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-5 sm:px-10">
          <Logo />
          <nav className="flex items-center gap-3 sm:gap-5" aria-label="Site">
            <Link to="/login" className={buttonClasses('primary', 'sm', 'h-9 px-4')}>
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1200px] px-5 py-12 outline-none sm:px-10 sm:py-16">
        <PolicyBody slug={slug} />
      </main>

      <footer className="mt-auto border-t border-line">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-5 py-8 text-[13px] text-text-3 sm:flex-row sm:items-center sm:gap-4 sm:px-10">
          <span>© 2026 PermitFlow</span>
          <span>A fictional licensing service built for an engineering assessment. Not a government service.</span>
        </div>
      </footer>
    </div>
  )
}

