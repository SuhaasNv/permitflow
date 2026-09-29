import { render, waitFor } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { FALLBACK_TITLE, RouteTitle, titled } from './RouteTitle'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        element: <RouteTitle />,
        children: [
          { path: '/', element: <p>Home</p>, handle: titled('PermitFlow | Food Establishment Licence', true) },
          { path: '/login', element: <p>Sign in</p>, handle: titled('Sign in') },
          {
            path: '/officer',
            handle: titled('Officer'),
            children: [{ path: 'queue', element: <p>Queue</p>, handle: titled('Review queue') }],
          },
          { path: '/untitled', element: <p>No title</p> },
        ],
      },
    ],
    { initialEntries: [path] },
  )
  render(<RouterProvider router={router} />)
  return router
}

describe('RouteTitle', () => {
  afterEach(() => {
    document.title = ''
  })

  it('names the tab after the screen, with the product after a bar', async () => {
    renderAt('/login')
    await waitFor(() => expect(document.title).toBe('Sign in | PermitFlow'))
  })

  it('takes the full title as given when asked (the landing page)', async () => {
    renderAt('/')
    await waitFor(() => expect(document.title).toBe('PermitFlow | Food Establishment Licence'))
  })

  it('uses the deepest route that names one and follows navigation', async () => {
    const router = renderAt('/officer/queue')
    await waitFor(() => expect(document.title).toBe('Review queue | PermitFlow'))
    await router.navigate('/login')
    await waitFor(() => expect(document.title).toBe('Sign in | PermitFlow'))
  })

  it('falls back to the static title for a route that names none', async () => {
    document.title = 'Something else'
    renderAt('/untitled')
    await waitFor(() => expect(document.title).toBe(FALLBACK_TITLE))
  })
})
