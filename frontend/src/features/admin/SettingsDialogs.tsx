import type { ReactNode } from 'react'
import { useId, useState } from 'react'

import type { PlatformSetting, SettingHistoryEntry, SettingValue } from '@/api/admin'
import { Alert } from '@/features/shared/Alert'
import { Dialog } from '@/features/shared/Dialog'
import { SelectField } from '@/features/shared/Controls'
import { Field, FieldLabel, FieldMessage, inputClasses } from '@/features/shared/Field'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { cleanText, lengthOf } from '@/lib/cleanText'
import { useChangeSetting, useRevertSetting } from './queries'
import {
  boundError,
  formatSpan,
  formatValue,
  formatWhen,
  formatWithUnit,
  inputSuffix,
  inputText,
  parseNumber,
  rangeText,
  unitLabel,
  writeFailure,
} from './settingsFormat'
import type { WriteFailure } from './settingsFormat'
import { PASSWORD_NEEDED, StepUpField } from './UsersPage'

const REASON_MIN = 3
const REASON_MAX = 280
const WITHIN = 'Takes effect within 10 seconds.'

/** "Requests per minute per client" reads as a sentence; "AI checks per day" keeps its capitals. */
const lowerFirst = (text: string): string => (/^[A-Z][a-z]/.test(text) ? text.charAt(0).toLowerCase() + text.slice(1) : text)

interface FormErrors {
  value?: string
  reason?: string
  password?: string
  general?: string
}

/** The fields every write shares, reset when a different row opens the dialog (adjusting state during render). */
function useWriteForm(resetKey: string | null, initialValue = '') {
  const [seen, setSeen] = useState<string | null>(resetKey)
  const [value, setValue] = useState(initialValue)
  const [reason, setReason] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})
  if (seen !== resetKey) {
    setSeen(resetKey)
    setValue(initialValue)
    setReason('')
    setPassword('')
    setErrors({})
  }
  /** The reason and password problems, merged with any problem found in the value. */
  const problems = (valueProblem?: string): FormErrors => {
    const found: FormErrors = {}
    if (valueProblem) found.value = valueProblem
    if (lengthOf(cleanText(reason)) < REASON_MIN) found.reason = `Say why in at least ${REASON_MIN} characters.`
    if (!password) found.password = PASSWORD_NEEDED
    return found
  }
  const fail = (failure: WriteFailure) => setErrors({ [failure.field]: failure.message })
  const clear = (field: keyof FormErrors) => setErrors((e) => ({ ...e, [field]: undefined, general: undefined }))
  return {
    value,
    reason,
    password,
    errors,
    setErrors,
    problems,
    fail,
    setValue: (v: string) => {
      setValue(v)
      clear('value')
    },
    setReason: (v: string) => {
      setReason(v)
      clear('reason')
    },
    setPassword: (v: string) => {
      setPassword(v)
      clear('password')
    },
  }
}

/** The required reason: 3 to 280 characters, with a counter. Shown in the history and sent to Telegram. */
function ReasonField({ value, error, onChange, autoFocus }: { value: string; error?: string; onChange: (v: string) => void; autoFocus?: boolean }) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1.5">
      <FieldLabel htmlFor={id} required>
        Reason
      </FieldLabel>
      <textarea
        id={id}
        rows={3}
        maxLength={REASON_MAX}
        required
        value={value}
        placeholder="Say why in a sentence"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error ${id}-help` : `${id}-help`}
        data-autofocus={autoFocus ? '' : undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn(inputClasses(Boolean(error)), 'h-auto min-h-24 resize-y py-2.5 leading-[22px]')}
      />
      {error ? <FieldMessage id={id} error={error} /> : null}
      <div className="flex justify-between gap-3 text-[13px] leading-[18px] text-text-3">
        <span id={`${id}-help`}>Shown in the history and sent to Telegram.</span>
        <span className="shrink-0 tabular-nums">
          {lengthOf(value)} / {REASON_MAX}
        </span>
      </div>
    </div>
  )
}

function Sub({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="text-[13px] leading-5 text-text-3">
      {children}
    </p>
  )
}

/** The arrow between an old and a new value: a screen reader says "changed to" instead. */
function ChangedTo() {
  return (
    <>
      <span aria-hidden="true">&rarr;</span>
      <span className="sr-only">changed to</span>
    </>
  )
}

/** Lets Enter send the form from a field: the dialog's own button sits outside it. */
function SubmitOnEnter() {
  return <button type="submit" tabIndex={-1} aria-hidden="true" className="sr-only" />
}

function Mono({ children, strong }: { children: ReactNode; strong?: boolean }) {
  return <span className={cn('font-mono text-[13px]', strong && 'font-semibold text-text')}>{children}</span>
}

function GeneralError({ message }: { message?: string }) {
  return message ? (
    <Alert tone="error">
      <span>{message}</span>
    </Alert>
  ) : null
}

/** Change one number or choice: what applies now, the new value, the old-to-new line, the reason and the password. */
export function ChangeDialog({ setting, onClose }: { setting: PlatformSetting | null; onClose: () => void }) {
  const change = useChangeSetting()
  const toast = useToast()
  const form = useWriteForm(setting?.key ?? null, setting ? inputText(setting, setting.value) : '')
  const subId = useId()
  const isChoice = setting?.kind === 'choice'

  const typed = setting && !isChoice ? parseNumber(setting, form.value) : null
  const next: SettingValue | null = !setting ? null : isChoice ? form.value : (typed?.value ?? null)
  const showDelta = setting !== null && next !== null && next !== setting.value && form.errors.value === undefined

  const submit = () => {
    if (!setting || change.isPending) return
    let valueProblem: string | undefined
    if (isChoice) {
      if (!setting.choices.includes(form.value)) valueProblem = `${setting.label} must be one of: ${setting.choices.join(', ')}.`
    } else if (typed?.error) {
      valueProblem = typed.error
    } else if (typed?.value !== undefined) {
      valueProblem = boundError(setting, typed.value) ?? undefined
    }
    if (!valueProblem && next === setting.value) valueProblem = `${setting.label} is already ${isChoice ? formatValue(setting, setting.value).toLowerCase() : formatWithUnit(setting, setting.value)}.`
    const found = form.problems(valueProblem)
    form.setErrors(found)
    if (Object.keys(found).length || next === null) return
    change.mutate(
      { key: setting.key, value: next, reason: cleanText(form.reason), password: form.password },
      {
        onSuccess: (s) => {
          toast.push({ title: 'Setting changed', body: `${s.label} is now ${formatWithUnit(s, s.value)}. ${WITHIN}`, tone: 'success' })
          close()
        },
        onError: (e) => form.fail(writeFailure(e, setting)),
      },
    )
  }

  const close = () => {
    change.reset()
    onClose()
  }

  return (
    <Dialog
      open={setting !== null}
      title={setting ? `Change ${lowerFirst(setting.label)}?` : ''}
      confirmLabel="Save change"
      busy={change.isPending}
      describedBy={subId}
      onConfirm={submit}
      onCancel={close}
    >
      {setting ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          <Sub id={subId}>{setting.description}</Sub>
          <dl className="flex flex-wrap gap-x-6 gap-y-2 border-y border-line py-2.5">
            {[
              ['Now', formatWithUnit(setting, setting.value)],
              ['Default', formatWithUnit(setting, setting.default)],
              ['Allowed', rangeText(setting)],
            ].map(([term, text]) => (
              <div key={term}>
                <dt className="text-xs font-semibold uppercase leading-4 tracking-[0.06em] text-text-3">{term}</dt>
                <dd className="text-sm font-semibold tabular-nums text-text">{text}</dd>
              </div>
            ))}
          </dl>
          {isChoice ? (
            <SelectField
              label="New value"
              required
              data-autofocus=""
              options={setting.choices.map((c) => ({ value: c, label: formatValue(setting, c) }))}
              value={form.value}
              error={form.errors.value}
              onChange={(e) => form.setValue(e.target.value)}
            />
          ) : (
            <Field
              label="New value"
              required
              data-autofocus=""
              inputMode={setting.unit === 'bytes' ? 'decimal' : 'numeric'}
              autoComplete="off"
              value={form.value}
              error={form.errors.value}
              help={`${setting.unit === 'bytes' ? 'In megabytes.' : 'Whole number.'} ${WITHIN}`}
              trailing={<span className="pr-2 text-[13px]">{inputSuffix(setting)}</span>}
              onChange={(e) => form.setValue(e.target.value)}
            />
          )}
          {showDelta && next !== null ? (
            <div className="flex flex-wrap items-baseline gap-x-2 text-[15px] text-text" aria-live="polite">
              <span className="pf-eyebrow">Change</span>
              <Mono>{formatValue(setting, setting.value)}</Mono>
              <ChangedTo />
              <Mono strong>{formatValue(setting, next)}</Mono>
              <span className="text-[13px] text-text-3">{unitLabel(setting)}</span>
            </div>
          ) : null}
          <ReasonField value={form.reason} error={form.errors.reason} onChange={form.setReason} />
          <StepUpField value={form.password} error={form.errors.password} onChange={form.setPassword} />
          <GeneralError message={form.errors.general} />
          <SubmitOnEnter />
        </form>
      ) : null}
    </Dialog>
  )
}

/** A switch's confirmation. The AI pause has its own words; any other switch gets the plain ones. */
export function ToggleDialog({
  setting,
  openedAt,
  onSaved,
  onClose,
}: {
  setting: PlatformSetting | null
  openedAt: number
  /** Called once a write went through, before the dialog closes. */
  onSaved?: () => void
  onClose: () => void
}) {
  const change = useChangeSetting()
  const toast = useToast()
  const form = useWriteForm(setting?.key ?? null)
  const subId = useId()
  const next = setting ? setting.value !== true : false
  const paused = setting?.key === 'ai_paused'

  const submit = () => {
    if (!setting || change.isPending) return
    const found = form.problems()
    form.setErrors(found)
    if (Object.keys(found).length) return
    change.mutate(
      { key: setting.key, value: next, reason: cleanText(form.reason), password: form.password },
      {
        onSuccess: (s) => {
          toast.push({
            title: paused ? (next ? 'AI checks paused' : 'AI checks are back on') : 'Setting changed',
            body: paused ? (next ? 'New uploads are stored without a check.' : 'New uploads are checked again.') : `${s.label} is now ${formatValue(s, s.value).toLowerCase()}. ${WITHIN}`,
            tone: 'success',
          })
          onSaved?.()
          close()
        },
        onError: (e) => form.fail(writeFailure(e, setting)),
      },
    )
  }

  const close = () => {
    change.reset()
    onClose()
  }

  let title = ''
  let sub: ReactNode = null
  let confirm = ''
  let body: ReactNode = null
  if (setting && paused && next) {
    title = 'Pause AI checks?'
    confirm = 'Pause AI checks'
    sub = 'Stops spend and provider calls at once. Nothing already checked is changed.'
    body = (
      <p>
        While paused, no new document check is sent to the AI provider. Each new upload is stored as &quot;Check unavailable&quot; and the
        application can still be submitted. Officers review those documents as normal.
      </p>
    )
  } else if (setting && paused) {
    title = 'Switch AI checks back on?'
    confirm = 'Switch on'
    sub = setting.updated_at ? `The pause started ${formatWhen(setting.updated_at)} and ran for ${formatSpan(openedAt - new Date(setting.updated_at).getTime())}.` : null
    body = (
      <p>
        New uploads are checked again at once. Documents stored as &quot;Check unavailable&quot; while the pause was on stay that way until
        the operator or an officer re-runs the check.
      </p>
    )
  } else if (setting) {
    title = `Switch ${setting.label} ${next ? 'on' : 'off'}?`
    confirm = next ? 'Switch on' : 'Switch off'
    sub = setting.description
    body = <p>{WITHIN}</p>
  }

  return (
    <Dialog
      open={setting !== null}
      title={title}
      confirmLabel={confirm}
      danger={paused && next}
      busy={change.isPending}
      describedBy={sub ? subId : null}
      onConfirm={submit}
      onCancel={close}
    >
      {setting ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          {sub ? <Sub id={subId}>{sub}</Sub> : null}
          {body}
          <ReasonField value={form.reason} error={form.errors.reason} onChange={form.setReason} autoFocus />
          <StepUpField value={form.password} error={form.errors.password} onChange={form.setPassword} />
          <GeneralError message={form.errors.general} />
          <SubmitOnEnter />
        </form>
      ) : null}
    </Dialog>
  )
}

/** Undo one history entry: shows exactly what it will set, and says so when today's bounds refuse it. */
export function RevertDialog({ entry, setting, onClose }: { entry: SettingHistoryEntry | null; setting: PlatformSetting | undefined; onClose: () => void }) {
  const revert = useRevertSetting()
  const toast = useToast()
  const form = useWriteForm(entry?.id ?? null)
  const noteId = useId()

  const target: SettingValue | null = !entry ? null : entry.old_was_default && setting ? setting.default : entry.old
  const tooOld =
    entry && !entry.old_was_default && setting && setting.kind === 'int' && typeof target === 'number'
      ? boundError(setting, target)
      : null
  const refusal = tooOld ?? form.errors.value

  const submit = () => {
    if (!entry || revert.isPending) return
    const found = form.problems()
    form.setErrors(found)
    if (Object.keys(found).length) return
    revert.mutate(
      { entryId: entry.id, reason: cleanText(form.reason), password: form.password },
      {
        onSuccess: (s) => {
          toast.push({ title: 'Change reverted', body: `${s.label} is back to ${formatWithUnit(s, s.value)}. ${WITHIN}`, tone: 'success' })
          close()
        },
        onError: (e) => form.fail(writeFailure(e, setting ?? null)),
      },
    )
  }

  const close = () => {
    revert.reset()
    onClose()
  }

  const shown = (v: SettingValue) => (setting ? formatWithUnit(setting, v) : String(v))

  return (
    <Dialog
      open={entry !== null}
      title="Revert this change?"
      confirmLabel="Revert change"
      busy={revert.isPending}
      describedBy={refusal && !tooOld ? null : noteId}
      onConfirm={submit}
      onCancel={close}
    >
      {entry ? (
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          {tooOld ? <Sub id={noteId}>Checked against today&apos;s bounds before anything is changed.</Sub> : null}
          <dl className="grid gap-2 border-y border-line py-3">
            {[
              ['Change', <>{entry.label}, <Mono>{setting ? formatValue(setting, entry.old) : String(entry.old)}</Mono> <ChangedTo /> <Mono strong>{setting ? formatValue(setting, entry.new) : String(entry.new)}</Mono></>],
              ['Made', `${formatWhen(entry.created_at)} by ${entry.actor_name ?? 'unknown'}`],
              ['Reason then', entry.reason],
            ].map(([term, text]) => (
              <div key={String(term)} className="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
                <dt className="text-xs font-semibold uppercase leading-5 tracking-[0.06em] text-text-3">{term}</dt>
                <dd className="text-text">{text}</dd>
              </div>
            ))}
          </dl>
          {refusal ? (
            <Alert tone="error" title="This change cannot be reverted">
              {refusal}
              {tooOld ? ' The bounds changed after this change, so the old value is no longer allowed.' : ''}
            </Alert>
          ) : target !== null ? (
            <p id={noteId}>
              This sets it back to <b className="text-text">{shown(target)}</b>
              {setting ? <>, replacing {shown(setting.value)} now</> : null}. The value is checked against today&apos;s bounds.
            </p>
          ) : null}
          <ReasonField value={form.reason} error={form.errors.reason} onChange={form.setReason} autoFocus />
          <StepUpField value={form.password} error={form.errors.password} onChange={form.setPassword} />
          <GeneralError message={form.errors.general} />
          <SubmitOnEnter />
        </form>
      ) : null}
    </Dialog>
  )
}
