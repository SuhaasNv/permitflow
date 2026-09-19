import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { PolicyPage } from './PolicyPage'
import { OPERATOR_NAME, POLICIES } from './content'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/privacy', element: <PolicyPage /> },
      { path: '/terms', element: <PolicyPage /> },
      { path: '/cookies', element: <PolicyPage /> },
      { path: '/other', element: <PolicyPage /> },
    ],
    { initialEntries: [path] },
  )
  render(<RouterProvider router={router} />)
  return router
}

describe('PolicyPage (US-057)', () => {
  it.each(['privacy', 'terms', 'cookies'] as const)('renders the %s policy with every section', (slug) => {
    renderAt(`/${slug}`)
    const policy = POLICIES[slug]
    expect(screen.getByRole('heading', { level: 1, name: policy.title })).toBeInTheDocument()
    expect(screen.getByText(`Last reviewed ${policy.reviewed}`)).toBeInTheDocument()
    for (const section of policy.sections) {
      expect(screen.getByRole('heading', { level: 2, name: section.heading })).toBeInTheDocument()
    }
    expect(screen.getByRole('link', { name: policy.title })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('names the operator, links the repository, and says it is not a government service', () => {
    renderAt('/privacy')
    expect(screen.getByText(new RegExp(`operated by ${OPERATOR_NAME}`))).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /github.com\/SuhaasNv\/permitflow/ })).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getAllByText(/Not a government service/).length).toBeGreaterThan(0)
  })

  it('states the facts the code guarantees: no cookies, OpenAI and LangSmith transfers, 10 MB uploads', () => {
    renderAt('/privacy')
    expect(screen.getByText(/sets no cookies/)).toBeInTheDocument()
    expect(screen.getByText(/sent to OpenAI \(United States\)/)).toBeInTheDocument()
    expect(screen.getByText(/LangSmith/)).toBeInTheDocument()
    expect(screen.getByText(/at most 10 MB each/)).toBeInTheDocument()
  })

  it('redirects an unknown slug to the privacy policy', () => {
    const router = renderAt('/other')
    expect(router.state.location.pathname).toBe('/privacy')
  })
})
