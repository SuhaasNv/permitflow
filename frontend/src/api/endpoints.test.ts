/**
 * Contract test for the thin API wrappers: each one must hit the path and method the backend router
 * exposes (docs/03-architecture/ARCHITECTURE.md API table). A renamed route or a wrong verb fails here, not
 * in the browser.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as applications from './applications'
import * as auth from './auth'
import { API_URL } from './client'
import * as formSchema from './formSchema'
import * as notifications from './notifications'
import * as officer from './officer'
import * as sections from './sections'
import * as siteVisit from './siteVisit'

const fetchMock = vi.fn<typeof fetch>()

function lastCall(): { path: string; method: string; body: unknown } {
  const [url, init] = fetchMock.mock.calls.at(-1)!
  return {
    path: String(url).replace(API_URL, ''),
    method: init?.method ?? 'GET',
    body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined,
  }
}

describe('API wrappers hit the documented routes', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => vi.unstubAllGlobals())

  const cases: [string, () => Promise<unknown>, string, string, unknown?][] = [
    ['login', () => auth.login('a@b.sg', 'pw'), '/auth/login', 'POST', { email: 'a@b.sg', password: 'pw' }],
    ['me', () => auth.me(), '/auth/me', 'GET'],
    ['form schema', () => formSchema.getFormSchema(), '/form-schema', 'GET'],
    ['list applications', () => applications.listApplications(), '/applications', 'GET'],
    ['create application', () => applications.createApplication(), '/applications', 'POST'],
    ['get application', () => applications.getApplication('a1'), '/applications/a1', 'GET'],
    [
      'update section',
      () => sections.updateSection('a1', 'premises', { postal_code: '208787' }),
      '/applications/a1/sections/premises',
      'PATCH',
      { postal_code: '208787' },
    ],
    ['submit', () => applications.submitApplication('a1'), '/applications/a1/submit', 'POST'],
    ['resubmit', () => applications.resubmitApplication('a1'), '/applications/a1/resubmit', 'POST'],
    ['delete draft', () => applications.deleteDraft('a1'), '/applications/a1', 'DELETE'],
    [
      'withdraw',
      () => applications.withdrawApplication('a1', 'Closing down.'),
      '/applications/a1/withdraw',
      'POST',
      { reason: 'Closing down.' },
    ],
    ['compare (operator)', () => applications.compareMyRevisions('a1', 1, 2), '/applications/a1/compare?from=1&to=2', 'GET'],
    ['notifications', () => notifications.getNotifications(), '/notifications', 'GET'],
    ['mark read', () => notifications.markNotificationRead('n1'), '/notifications/n1/read', 'POST'],
    ['mark all read', () => notifications.markAllNotificationsRead(), '/notifications/read-all', 'POST'],
    ['queue', () => officer.getQueue(), '/officer/applications', 'GET'],
    ['officer case', () => officer.getOfficerApplication('a1'), '/officer/applications/a1', 'GET'],
    [
      'transition',
      () => officer.transitionApplication('a1', { target: 'approved', expected_version: 3 }),
      '/officer/applications/a1/transition',
      'POST',
      { target: 'approved', expected_version: 3 },
    ],
    ['officer re-run', () => officer.rerunOfficerCheck('a1', 'd1'), '/officer/applications/a1/documents/d1/verify', 'POST'],
    ['templates', () => officer.getFeedbackTemplates(), '/officer/feedback-templates', 'GET'],
    [
      'create feedback',
      () =>
        officer.createFeedback('a1', {
          target_type: 'section',
          section_key: 'premises',
          document_type: null,
          message: 'Fix.',
          template_key: null,
        } as never),
      '/officer/applications/a1/feedback',
      'POST',
    ],
    ['withdraw feedback', () => officer.withdrawFeedback('a1', 'f1'), '/officer/applications/a1/feedback/f1/withdraw', 'POST'],
    ['resolve feedback', () => officer.resolveFeedback('a1', 'f1'), '/officer/applications/a1/feedback/f1/resolve', 'POST'],
    ['reopen feedback', () => officer.reopenFeedback('a1', 'f1'), '/officer/applications/a1/feedback/f1/reopen', 'POST'],
    ['restore feedback', () => officer.restoreFeedback('a1', 'f1'), '/officer/applications/a1/feedback/f1/restore', 'POST'],
    ['compare (officer)', () => officer.compareRevisions('a1', 1, 2), '/applications/a1/compare?from=1&to=2', 'GET'],
    ['audit trail', () => officer.getAuditTrail('a1'), '/officer/applications/a1/audit', 'GET'],
    // Site visit appointment (US-084): four officer routes, three operator routes.
    [
      'propose visit',
      () => siteVisit.proposeSiteVisit('a1', { date: '2026-09-22', slot: 'morning', note: null, expected_version: 3 }),
      '/officer/applications/a1/site-visit',
      'POST',
      { date: '2026-09-22', slot: 'morning', note: null, expected_version: 3 },
    ],
    [
      'decide visit',
      () => siteVisit.decideSiteVisit('a1', { action: 'keep_original' }),
      '/officer/applications/a1/site-visit/decide',
      'POST',
      { action: 'keep_original' },
    ],
    [
      'confirm visit without reply',
      () => siteVisit.confirmSiteVisitWithoutReply('a1'),
      '/officer/applications/a1/site-visit/confirm',
      'POST',
    ],
    [
      'reschedule visit (officer)',
      () => siteVisit.rescheduleSiteVisitAsOfficer('a1', { date: '2026-09-28', slot: 'afternoon', reason: 'On leave.' }),
      '/officer/applications/a1/site-visit/reschedule',
      'POST',
      { date: '2026-09-28', slot: 'afternoon', reason: 'On leave.' },
    ],
    ['accept visit', () => siteVisit.acceptSiteVisit('a1'), '/applications/a1/site-visit/accept', 'POST'],
    [
      'counter visit',
      () => siteVisit.counterSiteVisit('a1', { date: '2026-09-24', slot: 'afternoon', reason: 'Closed.' }),
      '/applications/a1/site-visit/counter',
      'POST',
      { date: '2026-09-24', slot: 'afternoon', reason: 'Closed.' },
    ],
    [
      'reschedule visit (operator)',
      () => siteVisit.rescheduleSiteVisitAsOperator('a1', { date: '2026-09-30', slot: 'morning', reason: 'Renovation.' }),
      '/applications/a1/site-visit/reschedule',
      'POST',
      { date: '2026-09-30', slot: 'morning', reason: 'Renovation.' },
    ],
  ]

  it.each(cases)('%s', async (_name, call, path, method, body) => {
    await call()
    const got = lastCall()
    expect(got.path).toBe(path)
    expect(got.method).toBe(method)
    if (body !== undefined) expect(got.body).toEqual(body)
  })
})
