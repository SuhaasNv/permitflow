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
  email: z.string().trim().min(1, 'Enter your email address.').email('Enter a valid email address.'),
  password: z.string().min(1, 'Enter your password.'),
})
type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { user, ready, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
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
      navigate(from && from !== '/login' ? from : homeFor(response.user.role), {
        replace: true,
      })
    } catch (error) {
      if (error instanceof AppError && error.status === 429) {
        setServerError('Too many failed attempts. Sign-in is paused for a minute.')
      } else if (error instanceof AppError && error.status === 401) {
        setServerError('Email or password is incorrect.')
      } else {
        setServerError(error instanceof Error ? error.message : 'Could not sign in. Try again.')
      }
    }
  })

  return (
    <div className="flex min-h-screen bg-bg">
      <section className="flex w-full flex-col border-r border-line bg-surface px-6 py-10 sm:px-12 lg:w-[520px] lg:px-16 lg:py-14">
        <div>
          <Logo />
        </div>
        <div className="my-auto py-10">
          <h1 className="text-[26px] font-semibold leading-8 tracking-tight">Sign in</h1>
          <p className="mb-7 text-text-2">Use your registered email address and password.</p>
          <form onSubmit={onSubmit} noValidate className="flex flex-col gap-[18px]">
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
              type="password"
              autoComplete="current-password"
              required
              error={form.formState.errors.password?.message}
              {...form.register('password')}
            />
            <Button type="submit" size="lg" loading={form.formState.isSubmitting} className="mt-1">
              Sign in
            </Button>
          </form>
        </div>
        <div className="flex flex-col gap-1.5 text-xs leading-[18px] text-text-3">
          <span>Sign-in is paused for a minute after 10 failed attempts.</span>
          <span>
            Licensing officers and administrators use the same sign-in. <Link to="/">About PermitFlow</Link>
          </span>
        </div>
      </section>
      <section className="hidden flex-1 flex-col justify-center gap-6 px-20 py-16 lg:flex">
        <div className="text-xs font-semibold uppercase tracking-[0.08em] text-primary">Food Establishment Licence</div>
        <h2 className="max-w-[520px] text-[32px] font-semibold leading-10 tracking-tight">
          Apply, respond to officer feedback and track your licence in one place.
        </h2>
        <p className="max-w-[480px] text-base leading-[26px] text-text-2">
          Uploads are checked automatically so you can fix problems before you submit. Every decision is made by a licensing officer.
        </p>
      </section>
    </div>
  )
}
