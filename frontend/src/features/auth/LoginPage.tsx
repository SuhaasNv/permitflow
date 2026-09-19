import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { login } from '@/api/auth'
import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { Field } from '@/features/shared/Field'
import { Logo } from '@/features/shared/Logo'
import { homeFor, useAuth } from './AuthContext'

const schema = z.object({
  email: z.string().trim().min(1, 'Enter your email address.').email('Enter a valid email address, like name@company.sg.'),
  password: z.string().min(1, 'Enter your password.'),
})
type FormValues = z.infer<typeof schema>

const POINTS: [string, string][] = [
  ['Guided application', 'Four short sections with validation as you go. Drafts are saved on the server.'],
  ['Checked uploads', 'Documents are read and compared with your form before you submit.'],
  ['Feedback in context', 'Officer comments are tied to the section or document they concern. Only flagged parts reopen.'],
]

export function LoginPage() {
  const { user, ready, signIn, endedReason } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  })

  if (ready && user) return <Navigate to={homeFor(user.role)} replace />

  const onSubmit = form.handleSubmit(async (values) => {
    setServerError(null)
    try {
      const response = await login(values.email, values.password)
      signIn(response)
      const from = (location.state as { from?: string } | null)?.from
      const home = homeFor(response.user.role)
      const area = home.split('/')[1] ?? ''
      // Only return to a path inside this role's own area; a stale path from another role lands on home.
      navigate(from && from.startsWith(`/${area}/`) ? from : home, { replace: true })
    } catch (error) {
      if (error instanceof AppError && error.status === 429) {
        // Two limits share the status: failed attempts, or too many sign-ins from this network (US-058).
        setServerError(error.message || 'Too many attempts. Sign-in is paused for a minute.')
      } else if (error instanceof AppError && error.status === 401) {
        setServerError('Email or password is incorrect.')
      } else {
        setServerError(error instanceof Error ? error.message : 'Could not sign in. Try again.')
      }
    }
  })

  return (
    <div className="grid min-h-screen bg-surface lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <main id="main" className="flex flex-col px-6 py-8 sm:px-12 lg:px-20 lg:py-10">
        <div>
          <Logo />
        </div>
        <div className="pf-enter my-auto w-full max-w-[400px] py-12">
          <h1 className="font-display text-[40px] leading-[1.05] tracking-[-0.01em]">Sign in</h1>
          <p className="mb-8 mt-3 text-[15px] leading-[22px] text-text-2">Use the email address and password you registered with.</p>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
            {endedReason && !serverError ? (
              <Alert tone="info">
                <span>
                  {endedReason === 'expired'
                    ? 'Your session ended after 8 hours. Sign in again to continue where you left off.'
                    : 'Your session is no longer valid. Sign in again to continue.'}
                </span>
              </Alert>
            ) : null}
            {serverError ? (
              <Alert tone="error">
                <span>{serverError}</span>
              </Alert>
            ) : null}
            <Field
              label="Email address"
              type="email"
              autoComplete="email"
              required
              placeholder="name@company.sg"
              error={form.formState.errors.email?.message}
              {...form.register('email')}
            />
            <Field
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              className="[&_input]:pr-11"
              error={form.formState.errors.password?.message}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  className="flex h-8 w-8 items-center justify-center rounded-md text-text-3 transition-colors hover:bg-neutral-soft hover:text-text"
                >
                  {showPassword ? (
                    <svg
                      width="17"
                      height="17"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.9"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a20.3 20.3 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a20.3 20.3 0 0 1-4.06 5.06M1 1l22 22" />
                      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                    </svg>
                  ) : (
                    <svg
                      width="17"
                      height="17"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.9"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              }
              {...form.register('password')}
            />
            <Button type="submit" size="lg" loading={form.formState.isSubmitting} className="mt-1">
              Sign in
            </Button>
          </form>
        </div>
        <div className="flex flex-col gap-2 text-[13px] text-text-3">
          <p>
            Demonstration only: accounts are shared and their passwords are published. Use the fictional demonstration documents, never real
            personal data. See the <Link to="/privacy">privacy policy</Link>.
          </p>
          <Link to="/" className="text-text-2 no-underline hover:text-text">
            About PermitFlow
          </Link>
        </div>
      </main>
      <aside
        aria-label="About the licence"
        className="relative hidden flex-col justify-between overflow-hidden bg-ink px-16 py-14 text-white lg:flex xl:px-24"
      >
        <div
          className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full border border-white/[0.06]"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-52 -left-24 h-[520px] w-[520px] rounded-full border border-white/[0.06]"
          aria-hidden="true"
        />
        <div className="pf-eyebrow text-[#aeb6c2]">Food Establishment Licence</div>
        <div className="pf-stagger my-auto max-w-[520px]">
          <h2 className="font-display text-[48px] leading-[1.05] xl:text-[56px]">
            Everything about your licence, <em className="text-[#c5cbd3]">in one record.</em>
          </h2>
          <dl className="mt-12 divide-y divide-white/15 border-t border-white/15">
            {POINTS.map(([title, text]) => (
              <div key={title} className="grid grid-cols-1 gap-1 py-5 sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-6">
                <dt className="text-[15px] font-semibold">{title}</dt>
                <dd className="text-[14px] leading-[21px] text-[#c5cbd3]">{text}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="text-[13px] text-[#8d96a3]">Automatic checks are advisory. Every decision is made by a licensing officer.</p>
      </aside>
    </div>
  )
}
