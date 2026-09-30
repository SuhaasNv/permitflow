import { useEffect } from 'react'
import { Outlet, useMatches } from 'react-router-dom'

/** The static `<title>` in index.html, kept for any route that names none. */
export const FALLBACK_TITLE = 'PermitFlow'

/** A route's `handle`: the tab title for that screen. */
export interface RouteHandle {
  title: string
}

/** `{ title: 'Sign in' }` becomes "Sign in | PermitFlow"; the landing page passes its full title with `full`. */
export function titled(title: string, full = false): RouteHandle {
  return { title: full ? title : `${title} | ${FALLBACK_TITLE}` }
}

function isRouteHandle(handle: unknown): handle is RouteHandle {
  return typeof handle === 'object' && handle !== null && 'title' in handle && typeof handle.title === 'string'
}

/** Root layout: sets `document.title` from the deepest matched route that declares one. */
export function RouteTitle() {
  const matches = useMatches()
  const title = matches
    .map((m) => m.handle)
    .filter(isRouteHandle)
    .at(-1)?.title
  useEffect(() => {
    document.title = title ?? FALLBACK_TITLE
  }, [title])
  return <Outlet />
}
