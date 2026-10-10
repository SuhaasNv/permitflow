import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import type { PlatformSetting, SettingHistoryEntry } from '@/api/admin'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { selectChevron } from '@/features/shared/Controls'
import { inputClasses } from '@/features/shared/Field'
import { PageHeader } from '@/features/shared/PageHeader'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { usePlatformSettings, useSettingsHistory } from './queries'
import { ChangeDialog, RevertDialog, ToggleDialog } from './SettingsDialogs'
import { formatValue, formatWhen, rangeSource, rangeText, unitLabel } from './settingsFormat'

type GroupId = 'traffic' | 'ai' | 'uploads'

const GROUPS: { id: GroupId; title: string; blurb: string }[] = [
  { id: 'traffic', title: 'Traffic', blurb: 'How much one client may ask of the service.' },
  { id: 'ai', title: 'AI checks', blurb: 'Document checks, the cost brake and the worker.' },
  { id: 'uploads', title: 'Uploads', blurb: 'What the service accepts, and what it does when the scanner is down.' },
]

/** The order rows appear in, within their group. A setting the page does not know yet goes last in its server group. */
const ORDER = [
  'rate_limit_per_minute',
  'login_attempts_per_minute',
  'ai_runs_per_user_per_day',
  'ai_runs_per_day',
  'ai_max_text_chars',
  'ai_paused',
  'telegram_per_check_messages',
  'worker_concurrency',
  'upload_max_bytes',
  'max_drafts_per_user',
  'scanner_fail_mode',
]

/** The design groups drafts per person under Uploads and the Telegram switch under AI checks; the server files them elsewhere. */
function groupOf(s: PlatformSetting): GroupId {
  if (s.key === 'max_drafts_per_user') return 'uploads'
  if (s.group === 'traffic' || s.group === 'uploads') return s.group
  return 'ai'
}

/** Where the server's wording is for developers, the page says it for the administrator. */
const DESCRIPTIONS: Record<string, string> = {
  upload_max_bytes: 'Largest single file accepted. Never above 10 MB.',
  worker_concurrency: 'Checks the worker runs at the same time. The worker reads this live.',
  ai_paused:
    'While on, no new check is sent to the AI provider: each is stored as unavailable and the application can still be submitted.',
  telegram_per_check_messages: 'Send one Telegram message for every document check, without names.',
  scanner_fail_mode:
    'What happens to an upload when the scanner is down: retry checks it again automatically (up to 3 times), hold waits for a person to re-run it. A file is never opened before it passes.',
}

/** A stored but unread setting says when it will start to matter. */
const NOT_LIVE: Record<string, string> = {
  telegram_per_check_messages: 'Takes effect once AI usage records are live.',
  scanner_fail_mode: 'Takes effect once the virus scan is live.',
}

function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'info' }) {
  return (
    <span
      className={cn(
        'inline-flex min-h-[22px] items-center whitespace-nowrap rounded-[4px] border px-2 py-px text-xs font-medium leading-4',
        tone === 'info' ? 'border-info-line bg-info-soft text-info' : 'border-neutral-line bg-neutral-soft text-neutral',
      )}
    >
      {children}
    </span>
  )
}

/** On or off. It never flips by itself: pressing it asks first, and the page shows what the server then says. */
function Switch({ on, label, settingKey, shown, onPress }: { on: boolean; label: string; settingKey: string; shown: string; onPress: () => void }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        data-setting={settingKey}
        onClick={onPress}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-xl border-2 p-0 transition-colors duration-[var(--dur-fast)] focus-visible:rounded-xl',
          "after:absolute after:-inset-x-0.5 after:-inset-y-3 after:content-['']",
          on ? 'border-ink bg-ink' : 'border-line-strong bg-surface',
        )}
      >
        <span
          className={cn(
            'absolute left-0.5 top-0.5 h-4 w-4 rounded-full transition-transform duration-[var(--dur-fast)] ease-[var(--ease-out)]',
            on ? 'translate-x-5 bg-white' : 'translate-x-0 bg-line-strong',
          )}
        />
      </button>
      <span className="text-sm font-semibold">{shown}</span>
    </span>
  )
}

const FACT_TERM = 'mb-1 text-xs font-semibold uppercase leading-4 tracking-[0.06em] text-text-3 @min-[1050px]:sr-only'
const COLUMNS = '@min-[1050px]:grid-cols-[minmax(0,1fr)_150px_84px_170px_200px_76px]'

function SettingRow({ s, onChange, onSwitch }: { s: PlatformSetting; onChange: () => void; onSwitch: () => void }) {
  const unit = unitLabel(s)
  const current =
    s.kind === 'bool' ? (
      <Switch
        on={s.value === true}
        label={s.label}
        settingKey={s.key}
        shown={s.value === true && s.key === 'ai_paused' ? 'On, paused' : formatValue(s, s.value)}
        onPress={onSwitch}
      />
    ) : (
      <>
        <span className={cn('tabular-nums', s.overridden ? 'text-base font-semibold text-text' : 'text-text-2')}>
          {formatValue(s, s.value)}
        </span>
        {unit ? <span className="text-[13px] text-text-3"> {unit}</span> : null}
      </>
    )
  const source = rangeSource(s)
  const note = s.in_use ? null : (NOT_LIVE[s.key] ?? 'Takes effect once it is live.')
  return (
    <li
      className={cn(
        'grid grid-cols-[minmax(0,1fr)] gap-3.5 p-4 @min-[600px]:grid-cols-[minmax(0,1fr)_auto] @min-[600px]:gap-x-5 @min-[600px]:gap-y-4 @min-[600px]:px-6 @min-[600px]:py-5',
        COLUMNS,
        '@min-[1050px]:items-start @min-[1050px]:gap-x-4 @min-[1050px]:gap-y-0',
        s.overridden && 'shadow-[inset_3px_0_0_var(--color-ink)]',
      )}
    >
      <div className="min-w-0 @min-[600px]:col-start-1 @min-[600px]:row-start-1 @min-[1050px]:col-auto @min-[1050px]:row-auto">
        <div className="text-[15px] font-semibold leading-[22px]">{s.label}</div>
        <div className="mt-px font-mono text-xs leading-4 text-text-3">{s.key}</div>
        <p className="mt-1.5 max-w-[60ch] text-[13px] leading-5 text-text-2">{DESCRIPTIONS[s.key] ?? s.description}</p>
        {note ? <div className="mt-1.5 text-xs leading-4 text-text-3">{note}</div> : null}
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3.5 @min-[600px]:col-span-2 @min-[600px]:row-start-2 @min-[600px]:grid-cols-4 @min-[1050px]:contents">
        <div className="min-w-0">
          <dt className={FACT_TERM}>Current</dt>
          <dd className="min-w-0 text-sm leading-5">
            {current}
            <div className="mt-1.5">
              {s.overridden ? <Tag tone="info">Overridden</Tag> : <span className="text-[13px] text-text-3">Default in force</span>}
            </div>
          </dd>
        </div>
        <div className="min-w-0">
          <dt className={FACT_TERM}>Default</dt>
          <dd className="text-sm leading-5 tabular-nums text-text-2">{formatValue(s, s.default)}</dd>
        </div>
        <div className="min-w-0">
          <dt className={FACT_TERM}>Allowed range</dt>
          <dd className="text-sm leading-5 text-text-2">
            <span className="tabular-nums">{rangeText(s)}</span>
            {source ? <span className="mt-0.5 block text-xs leading-4 text-text-3">{source}</span> : null}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className={FACT_TERM}>Last change</dt>
          <dd className="text-sm leading-5">
            {s.updated_at ? (
              <>
                {s.updated_by_name ? <span className="block font-medium">{s.updated_by_name}</span> : null}
                <span className="block text-[13px] text-text-2">{formatWhen(s.updated_at)}</span>
                {s.reason ? <span className="mt-0.5 block text-xs leading-4 text-text-3">{s.reason}</span> : null}
              </>
            ) : (
              <span className="text-[13px] text-text-3">No change yet</span>
            )}
          </dd>
        </div>
      </dl>
      {s.kind === 'bool' ? null : (
        <div className="flex @min-[600px]:col-start-2 @min-[600px]:row-start-1 @min-[600px]:justify-end @min-[1050px]:col-auto @min-[1050px]:row-auto">
          <Button
            variant="secondary"
            size="sm"
            className="flex-1 @min-[600px]:flex-none"
            aria-label={`Change ${s.label}`}
            onClick={onChange}
          >
            Change
          </Button>
        </div>
      )}
    </li>
  )
}

/** One bordered panel: the eyebrow and a sentence on the left, a count or a control on the right. */
function Group({ title, blurb, aside, children }: { title: string; blurb: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="pf-surface @container overflow-hidden" aria-label={title}>
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line px-4 pb-3.5 pt-4 @min-[600px]:px-6">
        <div>
          <div className="pf-eyebrow">{title}</div>
          <h2 className="mt-1 text-[17px] font-semibold leading-6">{blurb}</h2>
        </div>
        {aside}
      </div>
      {children}
    </section>
  )
}

function ColumnHeads() {
  return (
    <div
      className={cn(
        'hidden gap-x-4 border-b border-line bg-surface-2 px-6 py-2.5 text-xs font-semibold uppercase leading-4 tracking-[0.04em] text-text-3',
        '@min-[1050px]:grid',
        COLUMNS,
      )}
      aria-hidden="true"
    >
      <span>Setting</span>
      <span>Current</span>
      <span>Default</span>
      <span>Allowed range</span>
      <span>Last change</span>
      <span />
    </div>
  )
}

function HistoryRow({ e, setting, onRevert }: { e: SettingHistoryEntry; setting?: PlatformSetting; onRevert: () => void }) {
  const show = (v: SettingHistoryEntry['old']) => (setting ? formatValue(setting, v) : String(v))
  const unit = setting ? unitLabel(setting) : ''
  return (
    <li className="grid grid-cols-[minmax(0,1fr)] gap-2 p-4 @min-[600px]:grid-cols-[150px_minmax(0,1fr)_auto] @min-[600px]:gap-x-5 @min-[600px]:px-6 @min-[1050px]:grid-cols-[170px_340px_minmax(0,1fr)_84px] @min-[1050px]:items-start">
      <div className="flex flex-wrap gap-x-2.5 gap-y-0.5 text-[13px] text-text-2 @min-[600px]:block">
        <span className="tabular-nums">{formatWhen(e.created_at)}</span>
        <span className="block text-text-3">{e.actor_name ?? 'Unknown'}</span>
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm font-semibold">
          {e.label}
          {e.kind === 'reverted' ? <Tag>Revert</Tag> : null}
        </div>
        <div className="mt-0.5 flex flex-wrap items-baseline gap-x-1.5">
          <span className="font-mono text-[13px]">{show(e.old)}</span>
          <span className="text-text-3" aria-hidden="true">
            &rarr;
          </span>
          <span className="sr-only">changed to</span>
          <span className="font-mono text-[13px] font-semibold">{show(e.new)}</span>
          {unit ? <span className="text-[13px] text-text-3">{unit}</span> : null}
        </div>
      </div>
      <p className="text-[13px] leading-5 text-text-2 @min-[600px]:col-start-2 @min-[1050px]:col-auto">
        <span className="mr-2 text-xs font-semibold uppercase tracking-[0.06em] text-text-3">Reason</span>
        {e.reason}
      </p>
      <div className="flex @min-[600px]:col-start-3 @min-[600px]:row-span-2 @min-[600px]:row-start-1 @min-[600px]:items-center @min-[1050px]:col-auto @min-[1050px]:row-auto @min-[1050px]:justify-end">
        <Button variant="ghost" size="sm" aria-label={`Revert ${e.label} change of ${formatWhen(e.created_at)}`} onClick={onRevert}>
          Revert
        </Button>
      </div>
    </li>
  )
}

function SettingsSkeleton() {
  return (
    <div className="flex flex-col gap-6" role="status" aria-busy="true" aria-label="Loading settings">
      {[2, 3].map((rows) => (
        <div key={rows} className="pf-surface overflow-hidden">
          <div className="border-b border-line px-6 py-4">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-2 h-5 w-2/5" />
          </div>
          {Array.from({ length: rows }, (_, i) => (
            <div key={i} className="grid grid-cols-[minmax(0,1fr)_120px_80px] gap-4 border-b border-line px-6 py-5 last:border-b-0">
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-16" />
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

/** Settings (US-101): limits and switches the service reads live, changed with a reason and the administrator's password. */
export function AdminSettingsPage() {
  const settings = usePlatformSettings()
  const [filter, setFilter] = useState('')
  const history = useSettingsHistory(filter || null)
  // The header's "last change" is the newest entry of the whole history, whatever the filter says.
  const everything = useSettingsHistory(null)
  const filterId = useId()
  const [changingKey, setChangingKey] = useState<string | null>(null)
  const [toggling, setToggling] = useState<{ key: string; at: number } | null>(null)
  const askToggle = (key: string) => setToggling({ key, at: Date.now() })
  const [revertingId, setRevertingId] = useState<string | null>(null)

  const list = useMemo(() => {
    const rank = (key: string) => (ORDER.includes(key) ? ORDER.indexOf(key) : ORDER.length)
    return [...(settings.data?.settings ?? [])].sort((a, b) => rank(a.key) - rank(b.key))
  }, [settings.data])
  const byKey = (key: string | null) => list.find((s) => s.key === key)
  const entries = useMemo(() => history.data?.pages.flatMap((p) => p.entries) ?? [], [history.data])
  const reverting = entries.find((e) => e.id === revertingId) ?? null

  const overridden = list.filter((s) => s.overridden).length
  const latest = everything.data?.pages[0]?.entries[0]
  const paused = list.find((s) => s.key === 'ai_paused' && s.value === true)

  // After "Switch back on" the banner and its button are gone: focus goes to the switch, once the dialog has closed.
  const refocus = useRef(false)
  useEffect(() => {
    if (!refocus.current || paused || toggling !== null) return
    refocus.current = false
    document.querySelector<HTMLElement>('[role="switch"][data-setting="ai_paused"]')?.focus()
  }, [paused, toggling])

  const filterSelect = (
    <div className="flex w-full max-w-[300px] flex-col gap-1.5">
      <label htmlFor={filterId} className="text-[13px] font-semibold leading-[18px] text-text">
        Setting
      </label>
      <select id={filterId} value={filter} onChange={(e) => setFilter(e.target.value)} className={cn(inputClasses(), selectChevron)}>
        <option value="">All settings</option>
        {list.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  )

  return (
    <>
      <PageHeader
        eyebrow="Administrator"
        title="Settings"
        subtitle="Limits and switches the service reads live, within safe bounds. Defaults and ceilings come from the environment: a change here can lower a limit, never raise it past its ceiling."
        meta={
          <>
            {settings.data ? (
              <>
                <span>
                  {overridden} of {list.length} overridden
                </span>
                {latest ? (
                  <>
                    <span aria-hidden="true">&middot;</span>
                    <span>
                      Last change {formatWhen(latest.created_at)}
                      {latest.actor_name ? ` by ${latest.actor_name}` : ''}
                    </span>
                  </>
                ) : null}
                <span aria-hidden="true">&middot;</span>
              </>
            ) : null}
            <span>A change takes effect within 10 seconds</span>
          </>
        }
      />
      {settings.isPending ? (
        <SettingsSkeleton />
      ) : settings.isError ? (
        <ErrorPanel error={settings.error} onRetry={() => void settings.refetch()} />
      ) : list.length === 0 ? (
        <EmptyPanel title="No settings to show" description="The service has not published any settings an administrator can change." />
      ) : (
        <div className="flex flex-col gap-6">
          {paused ? (
            <Alert
              tone="warning"
              title="AI checks are paused"
              action={
                <Button size="sm" onClick={() => askToggle(paused.key)}>
                  Switch back on
                </Button>
              }
            >
              New uploads are stored without a check.
              {paused.updated_at
                ? ` Switched on ${formatWhen(paused.updated_at)}${paused.updated_by_name ? ` by ${paused.updated_by_name}` : ''}.`
                : ''}
            </Alert>
          ) : null}
          {GROUPS.map((g) => {
            const rows = list.filter((s) => groupOf(s) === g.id)
            return (
              <Group
                key={g.id}
                title={g.title}
                blurb={g.blurb}
                aside={
                  <span className="text-xs text-text-3">
                    {rows.length} {rows.length === 1 ? 'setting' : 'settings'}
                  </span>
                }
              >
                <ColumnHeads />
                <ul className="divide-y divide-line">
                  {rows.map((s) => (
                    <SettingRow key={s.key} s={s} onChange={() => setChangingKey(s.key)} onSwitch={() => askToggle(s.key)} />
                  ))}
                </ul>
              </Group>
            )
          })}
          <Group title="History" blurb="Every change and revert, newest first" aside={filterSelect}>
            {history.isPending ? (
              <div role="status" aria-busy="true" aria-label="Loading history" className="divide-y divide-line">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="grid grid-cols-[120px_minmax(0,1fr)] gap-4 px-6 py-4">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-3/5" />
                  </div>
                ))}
              </div>
            ) : history.isError ? (
              <ErrorPanel error={history.error} onRetry={() => void history.refetch()} />
            ) : entries.length === 0 ? (
              <EmptyPanel
                title={filter ? 'No changes to this setting yet' : 'No changes yet'}
                description="Every change and revert will be listed here, with who made it and why."
              />
            ) : (
              <>
                <ul className="divide-y divide-line" aria-label="Changes and reverts">
                  {entries.map((e) => (
                    <HistoryRow key={e.id} e={e} setting={byKey(e.key)} onRevert={() => setRevertingId(e.id)} />
                  ))}
                </ul>
                <div className="flex items-center justify-between gap-3 border-t border-line bg-surface-2 px-4 py-2.5 @min-[600px]:px-6">
                  <span className="text-xs text-text-3">
                    {entries.length} {entries.length === 1 ? 'entry' : 'entries'} shown
                  </span>
                  {history.hasNextPage ? (
                    <Button variant="ghost" size="sm" loading={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>
                      Show older changes
                    </Button>
                  ) : null}
                </div>
              </>
            )}
          </Group>
        </div>
      )}

      <ChangeDialog setting={byKey(changingKey) ?? null} onClose={() => setChangingKey(null)} />
      <ToggleDialog
        setting={byKey(toggling?.key ?? null) ?? null}
        openedAt={toggling?.at ?? 0}
        onSaved={() => {
          refocus.current = paused !== undefined && toggling?.key === 'ai_paused'
        }}
        onClose={() => setToggling(null)}
      />
      <RevertDialog entry={reverting} setting={byKey(reverting?.key ?? null)} onClose={() => setRevertingId(null)} />
    </>
  )
}
