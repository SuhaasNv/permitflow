import { useMemo, useState } from 'react'

import type { AdminUser, UserCreate } from '@/api/admin'
import type { Role } from '@/api/auth'
import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { SelectField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { Field } from '@/features/shared/Field'
import { PageHeader } from '@/features/shared/PageHeader'
import { SearchBox } from '@/features/shared/SearchBox'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { formatDate } from '@/lib/format'
import { matchesQuery } from '@/lib/search'
import { useAdminUsers, useCreateUser, usePatchUser } from './queries'

const ROLE_LABEL: Record<Role, string> = { operator: 'Operator', officer: 'Licensing officer', admin: 'Administrator' }
const ROLE_OPTIONS = (Object.keys(ROLE_LABEL) as Role[]).map((value) => ({ value, label: ROLE_LABEL[value] }))
type Filter = 'all' | Role
const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'operator', label: 'Operators' },
  { key: 'officer', label: 'Licensing officers' },
  { key: 'admin', label: 'Administrators' },
]

/** Why a row's controls are off, in the words the design names (S-41). */
export function lockedReason(user: AdminUser, selfId: string): string | null {
  if (user.id === selfId) return 'You cannot change your own account'
  if (user.is_protected) return 'Demonstration account, protected'
  return null
}

/** The server's 409 codes in the dialog, as the design words them; other errors as the server says them. */
export function conflictMessage(error: unknown): string {
  if (error instanceof AppError) {
    if (error.code === 'last_admin') return 'This is the last active administrator.'
    if (error.code === 'self_change') return 'You cannot change your own account.'
    if (error.code === 'protected_account') return 'Demonstration account, protected.'
    if (error.code === 'try_again') return 'Another administrator changed users at the same moment. Try again.'
    return error.message
  }
  return 'Something went wrong. Try again.'
}

type Pending = { kind: 'role'; user: AdminUser } | { kind: 'active'; user: AdminUser } | { kind: 'create' } | null

/** Users (S-41, US-073): change a role, deactivate or reactivate, add an account; every change is audited. */
export function AdminUsersPage() {
  const users = useAdminUsers()
  const patch = usePatchUser()
  const create = useCreateUser()
  const toast = useToast()
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')
  const [pending, setPending] = useState<Pending>(null)
  const [role, setRole] = useState<Role>('operator')
  const [draft, setDraft] = useState<UserCreate>({ email: '', full_name: '', role: 'officer', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof UserCreate, string>>>({})

  const rows = useMemo(() => users.data?.users ?? [], [users.data])
  const selfId = users.data?.self_id ?? ''
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: 0, operator: 0, officer: 0, admin: 0 }
    for (const u of rows) {
      c.all += 1
      c[u.role] += 1
    }
    return c
  }, [rows])
  const shown = rows.filter((u) => (filter === 'all' || u.role === filter) && matchesQuery(query, [u.full_name, u.email]))
  const summary = users.data
    ? `${counts.all} ${counts.all === 1 ? 'account' : 'accounts'} · ${counts.operator} ${counts.operator === 1 ? 'operator' : 'operators'} · ${counts.officer} licensing ${counts.officer === 1 ? 'officer' : 'officers'} · ${counts.admin} ${counts.admin === 1 ? 'administrator' : 'administrators'}`
    : 'Change a role or deactivate an account; every change is audited.'

  const close = () => {
    setPending(null)
    setError(null)
    setFieldErrors({})
  }

  const confirmRole = () => {
    if (pending?.kind !== 'role') return
    if (role === pending.user.role) {
      close()
      return
    }
    patch.mutate(
      { id: pending.user.id, body: { role } },
      {
        onSuccess: (u) => {
          toast.push({ title: 'Role changed', body: `${u.full_name} is now ${ROLE_LABEL[u.role].toLowerCase()}.`, tone: 'success' })
          close()
        },
        onError: (e) => setError(conflictMessage(e)),
      },
    )
  }

  const confirmActive = () => {
    if (pending?.kind !== 'active') return
    const next = !pending.user.is_active
    patch.mutate(
      { id: pending.user.id, body: { is_active: next } },
      {
        onSuccess: (u) => {
          toast.push({
            title: next ? 'Account reactivated' : 'Account deactivated',
            body: next ? `${u.full_name} can sign in again.` : `${u.full_name} is signed out on their next request.`,
            tone: 'success',
          })
          close()
        },
        onError: (e) => setError(conflictMessage(e)),
      },
    )
  }

  const confirmCreate = () => {
    const errors: Partial<Record<keyof UserCreate, string>> = {}
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email.trim())) errors.email = 'Enter a valid email address.'
    if (!draft.full_name.trim()) errors.full_name = "Enter the person's name."
    if (draft.password.length < 12) errors.password = 'At least 12 characters.'
    setFieldErrors(errors)
    if (Object.keys(errors).length) return
    create.mutate(
      { ...draft, email: draft.email.trim().toLowerCase(), full_name: draft.full_name.trim() },
      {
        onSuccess: (u) => {
          toast.push({
            title: 'Account created',
            body: `${u.full_name} can sign in as ${ROLE_LABEL[u.role].toLowerCase()}.`,
            tone: 'success',
          })
          setDraft({ email: '', full_name: '', role: 'officer', password: '' })
          close()
        },
        onError: (e) =>
          setError(e instanceof AppError && e.code === 'conflict' ? 'An account with this email already exists.' : conflictMessage(e)),
      },
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Administrator"
        title="Users"
        subtitle={summary}
        meta={<span>Change a role or deactivate an account; every change is audited.</span>}
        actions={
          <Button
            size="sm"
            onClick={() => {
              setError(null)
              setPending({ kind: 'create' })
            }}
          >
            Add an account
          </Button>
        }
      />
      {users.isPending ? (
        <div className="pf-surface overflow-hidden" aria-busy="true" aria-label="Loading users">
          {[0, 1, 2].map((i) => (
            <div key={i} className="grid grid-cols-[minmax(0,1fr)_150px_200px] gap-4 border-b border-line px-5 py-4 last:border-b-0">
              <Skeleton className="h-4 w-2/5" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
          ))}
        </div>
      ) : users.isError ? (
        <ErrorPanel error={users.error} onRetry={() => void users.refetch()} />
      ) : (
        <section className="pf-surface overflow-hidden" aria-label="Directory">
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2.5 sm:px-4">
            <div className="flex flex-wrap items-center gap-1" role="tablist" aria-label="Filter by role">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  role="tab"
                  aria-selected={filter === f.key}
                  onClick={() => setFilter(f.key)}
                  className={cn(
                    'inline-flex h-10 items-center gap-1.5 rounded-md px-3 text-[13px] font-medium transition-colors duration-[var(--dur-fast)] sm:h-8',
                    filter === f.key ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                  )}
                >
                  {f.label}
                  <span className="font-mono text-[11px] text-text-3">{counts[f.key]}</span>
                </button>
              ))}
            </div>
            <SearchBox
              value={query}
              onChange={setQuery}
              label="Search by name or email"
              placeholder="Search by name or email"
              className="ml-auto w-full sm:w-[300px]"
            />
          </div>
          {shown.length === 0 ? (
            <EmptyPanel title="No accounts match" description="Try another name, email or role." />
          ) : (
            <ul className="divide-y divide-line">
              {shown.map((u) => {
                const locked = lockedReason(u, selfId)
                return (
                  <li
                    key={u.id}
                    className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-2 px-5 py-3.5 sm:grid-cols-[minmax(0,1fr)_150px_210px_110px_230px] sm:items-center"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">
                        {u.full_name}
                        {u.id === selfId ? <span className="font-normal text-text-3"> (you)</span> : null}
                      </div>
                      <div className="truncate text-xs text-text-3">{u.email}</div>
                    </div>
                    <span className="text-sm text-text-2">{ROLE_LABEL[u.role]}</span>
                    <span className="flex flex-wrap items-center gap-1.5">
                      <StatusBadge label={u.is_active ? 'Active' : 'Deactivated'} tone={u.is_active ? 'success' : 'neutral'} />
                      {u.is_protected ? (
                        <span className="inline-flex h-6 items-center gap-1 rounded-full border border-line px-2 text-[11px] font-medium text-text-2">
                          <svg
                            width="11"
                            height="11"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.2"
                            aria-hidden="true"
                          >
                            <rect x="3" y="11" width="18" height="11" rx="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                          Protected
                        </span>
                      ) : null}
                    </span>
                    <span className="text-[13px] text-text-3">{formatDate(u.created_at)}</span>
                    <span className="col-span-2 flex flex-wrap justify-end gap-1 sm:col-span-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={locked !== null}
                        title={locked ?? undefined}
                        onClick={() => {
                          setRole(u.role)
                          setError(null)
                          setPending({ kind: 'role', user: u })
                        }}
                      >
                        Change role
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={locked !== null}
                        title={locked ?? undefined}
                        onClick={() => {
                          setError(null)
                          setPending({ kind: 'active', user: u })
                        }}
                      >
                        {u.is_active ? 'Deactivate' : 'Reactivate'}
                      </Button>
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
          <p className="border-t border-line px-5 py-3 text-xs text-text-3">
            {shown.length} of {rows.length} accounts. Protected accounts are the published demonstration sign-ins; no administrator can
            change them.
          </p>
        </section>
      )}

      <Dialog
        open={pending?.kind === 'role'}
        title={pending?.kind === 'role' ? `Change ${pending.user.full_name}'s role?` : ''}
        confirmLabel="Change role"
        busy={patch.isPending}
        onConfirm={confirmRole}
        onCancel={close}
      >
        {pending?.kind === 'role' ? (
          <>
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-[13px] font-semibold text-text">New role</legend>
              {ROLE_OPTIONS.map((o) => (
                <label key={o.value} className="flex items-center gap-2.5 text-sm text-text">
                  <input
                    type="radio"
                    name="new-role"
                    value={o.value}
                    checked={role === o.value}
                    onChange={() => setRole(o.value)}
                    className="h-4 w-4"
                  />
                  {o.label}
                </label>
              ))}
            </fieldset>
            <p>They get {ROLE_LABEL[role].toLowerCase()} permissions on their next request. This does not sign them out.</p>
            {error ? (
              <Alert tone="error">
                <span>{error}</span>
              </Alert>
            ) : null}
          </>
        ) : null}
      </Dialog>

      <Dialog
        open={pending?.kind === 'active'}
        title={pending?.kind === 'active' ? `${pending.user.is_active ? 'Deactivate' : 'Reactivate'} ${pending.user.full_name}?` : ''}
        confirmLabel={pending?.kind === 'active' && pending.user.is_active ? 'Deactivate' : 'Reactivate'}
        danger={pending?.kind === 'active' && pending.user.is_active}
        busy={patch.isPending}
        onConfirm={confirmActive}
        onCancel={close}
      >
        {pending?.kind === 'active' ? (
          <>
            <p>
              {pending.user.is_active
                ? 'They are signed out on their next request and cannot sign in again until reactivated. Their applications and history stay as they are.'
                : 'They can sign in again at once, with the role they had.'}
            </p>
            {error ? (
              <Alert tone="error">
                <span>{error}</span>
              </Alert>
            ) : null}
          </>
        ) : null}
      </Dialog>

      <Dialog
        open={pending?.kind === 'create'}
        title="Add an account"
        confirmLabel="Create account"
        busy={create.isPending}
        onConfirm={confirmCreate}
        onCancel={close}
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault()
            confirmCreate()
          }}
        >
          <Field
            label="Full name"
            required
            value={draft.full_name}
            error={fieldErrors.full_name}
            autoComplete="off"
            onChange={(e) => setDraft({ ...draft, full_name: e.target.value })}
          />
          <Field
            label="Email address"
            type="email"
            required
            value={draft.email}
            error={fieldErrors.email}
            autoComplete="off"
            placeholder="name@agency.gov.sg"
            onChange={(e) => setDraft({ ...draft, email: e.target.value })}
          />
          <SelectField
            label="Role"
            required
            options={ROLE_OPTIONS}
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value as Role })}
          />
          <Field
            label="Temporary password"
            type="password"
            required
            value={draft.password}
            error={fieldErrors.password}
            help="At least 12 characters. Hand it over in person; there is no email on this demonstration."
            autoComplete="new-password"
            onChange={(e) => setDraft({ ...draft, password: e.target.value })}
          />
          {error ? (
            <Alert tone="error">
              <span>{error}</span>
            </Alert>
          ) : null}
        </form>
      </Dialog>
    </>
  )
}
