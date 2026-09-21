import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'

import raw from 'virtual:release-notes'

import { AppShell } from '@/app/AppShell'
import { useAuth } from '@/features/auth/AuthContext'
import { buttonClasses } from '@/features/shared/Button'
import { Logo } from '@/features/shared/Logo'
import { PageHeader } from '@/features/shared/PageHeader'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { cn } from '@/lib/cn'
import { orderBlocks, parseReleaseNotes, releaseFor, tokenizeInline } from './notes'
import type { Audience, NoteBlock, Release } from './notes'
import { useBuildInfo } from './queries'
import { markReleaseSeen } from './seen'
import { VersionChip } from './VersionChip'

/** Parsed once per load; the notes are part of the build (see vite.config.ts). */
export const RELEASE_NOTES = parseReleaseNotes(raw)

const ENVIRONMENT_LABEL: Record<string, string> = {
  development: 'development environment',
  production: 'production',
  test: 'test environment',
}

function Inline({ text }: { text: string }) {
  return (
    <>
      {tokenizeInline(text).map((t, i) => {
        if (t.kind === 'code') {
          return (
            <code key={i} className="rounded bg-surface-3 px-1 font-mono text-[0.9em]">
              {t.text}
            </code>
          )
        }
        if (t.kind === 'strong') return <strong key={i}>{t.text}</strong>
        if (t.kind === 'link') {
          return (
            <a key={i} href={t.href} rel="noreferrer">
              {t.text}
            </a>
          )
        }
        return <span key={i}>{t.text}</span>
      })}
    </>
  )
}

function BlockBody({ block }: { block: NoteBlock }) {
  return (
    <>
      {block.paragraphs.map((p) => (
        <p key={p} className="mt-2 text-[15px] leading-[22px] text-text-2">
          <Inline text={p} />
        </p>
      ))}
      <ul className="mt-2 list-disc space-y-2 pl-5 text-[15px] leading-[22px]">
        {block.items.map((item) => (
          <li key={item}>
            <Inline text={item} />
          </li>
        ))}
      </ul>
    </>
  )
}

function OpenBlock({ block, kicker }: { block: NoteBlock; kicker?: string }) {
  return (
    <section className="pt-6" aria-label={block.heading}>
      {kicker ? <p className="pf-eyebrow mb-1">{kicker}</p> : null}
      <div className="flex flex-wrap items-baseline gap-x-2">
        <h3 className="text-[20px] font-semibold leading-7">{block.heading}</h3>
        {block.note ? (
          <span className="text-[13px] text-text-3">
            <Inline text={block.note} />
          </span>
        ) : null}
      </div>
      <BlockBody block={block} />
    </section>
  )
}

/** A folded audience block: a bounded disclosure row with the count; native details keep it keyboard-reachable. */
function FoldedBlock({ block }: { block: NoteBlock }) {
  return (
    <details className="group mt-2 rounded-lg border border-line bg-surface">
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-3.5 text-[15px] font-semibold marker:hidden [&::-webkit-details-marker]:hidden">
        <span>{block.heading}</span>
        <span className="flex items-center gap-2 text-text-3">
          <span className="font-mono text-xs">{block.items.length}</span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="transition-transform group-open:rotate-90"
          >
            <path d="m9 18 6-6-6-6" />
          </svg>
        </span>
      </summary>
      <div className="px-3.5 pb-4">
        <BlockBody block={block} />
      </div>
    </details>
  )
}

function ReleaseArticle({ release, reader }: { release: Release; reader: Audience | null }) {
  const { own, others, shared } = orderBlocks(release.blocks, reader)
  const ownKicker = reader && reader !== 'admin' ? 'For you' : undefined
  return (
    <article className="min-w-0 max-w-[760px]">
      <div className="flex flex-wrap items-baseline gap-x-2.5">
        <span className="font-mono text-[15px] text-text-2">{release.version}</span>
        <span className="text-[13px] text-text-3">{release.date}</span>
      </div>
      <h2 className="mt-1.5 text-[24px] font-semibold leading-[30px] tracking-[-0.015em] sm:text-[28px] sm:leading-9">
        {capitalize(release.title)}
      </h2>
      {release.note ? <p className="mt-1.5 text-[13px] text-text-3">{capitalize(release.note)}.</p> : null}
      {release.intro.map((p) => (
        <p key={p} className="mt-3 text-[15px] leading-[22px] text-text-2">
          <Inline text={p} />
        </p>
      ))}
      {own.map((b) => (
        <OpenBlock key={b.heading} block={b} kicker={ownKicker} />
      ))}
      {others.length > 0 ? (
        <div className="mt-6">
          <p className="pf-eyebrow">Also in this release</p>
          {others.map((b) => (
            <FoldedBlock key={b.heading} block={b} />
          ))}
        </div>
      ) : null}
      {shared.map((b) => (
        <OpenBlock key={b.heading} block={b} kicker={reader && reader !== 'admin' ? 'For everyone' : undefined} />
      ))}
    </article>
  )
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/** The page body: the build line, the releases list (the running one marked), Coming next, the selected release. */
function ReleasesBody({ selected, reader }: { selected: Release; reader: Audience | null }) {
  const build = useBuildInfo()
  const current = releaseFor(RELEASE_NOTES, __APP_VERSION__)
  const commit = build.data?.commit && build.data.commit !== 'local' ? build.data.commit : null
  const environment = build.data ? (ENVIRONMENT_LABEL[build.data.environment] ?? build.data.environment) : null
  return (
    <>
      <PageHeader
        eyebrow="Releases"
        title="What's new"
        subtitle="What each version changed, in the words of the people who use PermitFlow. Your own changes come first."
      />
      <p className="mb-6 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]" data-testid="build-line">
        <span className="font-medium text-text-2">This build</span>
        <span className="font-mono text-text">
          v{__APP_VERSION__}
          {commit ? ` (${commit})` : ''}
        </span>
        {environment ? <span className="text-text-3">· {environment}</span> : null}
        {current ? <span className="text-text-3">· {current.date}</span> : null}
      </p>
      <div className="lg:grid lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-x-12 lg:items-start">
        <div className="lg:sticky lg:top-6 lg:flex lg:flex-col lg:gap-5">
          <nav aria-label="Releases" className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 lg:flex-col lg:gap-0.5 lg:overflow-visible">
            <p className="pf-eyebrow hidden px-2.5 pb-1.5 lg:block">Releases</p>
            {RELEASE_NOTES.releases.map((r) => {
              const isCurrent = r.version === current?.version
              const isSelected = r.version === selected.version
              return (
                <Link
                  key={r.version}
                  to={`/releases/${r.version}`}
                  aria-current={isSelected ? 'page' : undefined}
                  className={cn(
                    'inline-flex shrink-0 items-center rounded-md no-underline transition-colors',
                    'h-9 px-3 text-sm lg:h-auto lg:min-h-11 lg:flex-col lg:items-stretch lg:justify-center lg:gap-0.5 lg:px-2.5 lg:py-1.5',
                    isSelected ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                  )}
                >
                  <span className="flex items-baseline gap-2 whitespace-nowrap">
                    <span className={cn('font-mono text-[13px]', isSelected ? 'font-semibold' : '')}>{r.version}</span>
                    <span className="hidden text-xs text-text-3 lg:inline">{r.date}</span>
                  </span>
                  <span className={cn('hidden truncate text-[13px] lg:block', isSelected ? 'font-medium' : '')}>{capitalize(r.title)}</span>
                  {isCurrent ? (
                    <span className="mt-1 hidden lg:block">
                      <StatusBadge label="This build" tone="info" />
                    </span>
                  ) : null}
                </Link>
              )
            })}
          </nav>
          {RELEASE_NOTES.comingNext.length > 0 ? (
            <aside className="hidden rounded-[10px] border border-line bg-surface px-4 py-3.5 lg:block" aria-label="Coming next">
              <p className="pf-eyebrow">Coming next</p>
              {RELEASE_NOTES.comingNext.map((p) => (
                <p key={p} className="mt-2 text-[13px] leading-[18px] text-text-2">
                  <Inline text={p} />
                </p>
              ))}
            </aside>
          ) : null}
        </div>
        <div className="mt-6 lg:mt-0">
          <ReleaseArticle release={selected} reader={reader} />
          {RELEASE_NOTES.comingNext.length > 0 ? (
            <aside className="mt-8 rounded-[10px] border border-line bg-surface px-4 py-3.5 lg:hidden" aria-label="Coming next">
              <p className="pf-eyebrow">Coming next</p>
              {RELEASE_NOTES.comingNext.map((p) => (
                <p key={p} className="mt-2 text-[13px] leading-[18px] text-text-2">
                  <Inline text={p} />
                </p>
              ))}
            </aside>
          ) : null}
        </div>
      </div>
    </>
  )
}

/** What's new (US-094, S-44): `/releases` and `/releases/:version`. Signed in, inside the app shell with the
 * reader's own block first; signed out, the public frame with everything open. Opening it clears the "New"
 * mark for this build. An unknown version shows the newest release. */
export function ReleasesPage() {
  const { version } = useParams()
  const { user, ready } = useAuth()
  const selected = (version ? releaseFor(RELEASE_NOTES, version) : undefined) ?? RELEASE_NOTES.releases[0]
  useEffect(() => {
    markReleaseSeen(__APP_VERSION__)
  }, [])
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [version])
  if (user && ready) {
    return (
      <AppShell>
        <ReleasesBody selected={selected} reader={user.role} />
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
        <ReleasesBody selected={selected} reader={null} />
      </main>
      <footer className="mt-auto border-t border-line">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-5 py-8 text-[13px] text-text-3 sm:flex-row sm:items-center sm:gap-4 sm:px-10">
          <span>© 2026 PermitFlow</span>
          <VersionChip variant="rail" />
          <span>A fictional licensing service built for an engineering assessment. Not a government service.</span>
        </div>
      </footer>
    </div>
  )
}
