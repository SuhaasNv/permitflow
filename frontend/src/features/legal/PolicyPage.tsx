import { useEffect } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { buttonClasses } from '@/features/shared/Button'
import { Logo } from '@/features/shared/Logo'
import { OPERATOR_URL, POLICIES } from './content'
import type { PolicySlug } from './content'

const SLUGS: PolicySlug[] = ['privacy', 'terms', 'cookies']

function isSlug(value: string | undefined): value is PolicySlug {
  return SLUGS.includes(value as PolicySlug)
}

/** Public policy pages (US-057): privacy, terms, cookies. One layout, content from `content.ts`. */
export function PolicyPage() {
  const slug = useLocation().pathname.replace(/^\//, '')
  // The public routes sit outside the app shell's ScrollRestoration, so a footer link at the bottom of the
  // landing page would otherwise open the policy still scrolled to the bottom.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [slug])
  if (!isSlug(slug)) return <Navigate to="/privacy" replace />
  const policy = POLICIES[slug]
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

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[720px] px-5 py-12 outline-none sm:px-10 sm:py-16">
        <nav aria-label="Policies" className="mb-8 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {SLUGS.map((s) => (
            <Link
              key={s}
              to={`/${s}`}
              aria-current={s === slug ? 'page' : undefined}
              className={s === slug ? 'font-semibold text-text no-underline' : 'text-text-2 no-underline hover:text-text'}
            >
              {POLICIES[s].title}
            </Link>
          ))}
        </nav>
        <h1 className="font-display text-[36px] leading-[1.05] sm:text-[42px]">{policy.title}</h1>
        <p className="mt-3 text-[13px] text-text-3">Last reviewed {policy.reviewed}</p>
        <p className="mt-6 text-[17px] leading-[26px] text-text-2">{policy.summary}</p>

        {policy.sections.map((section) => (
          <section key={section.heading} className="mt-10">
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
