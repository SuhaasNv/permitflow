import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'

export const PASSWORD = process.env.SEED_PASSWORD ?? 'PermitFlow!2026'
export const OPERATOR = 'operator@permitflow.example.sg'
export const OFFICER = 'officer@permitflow.example.sg'
/** Backend the scenarios seed through. Locally the backend runs on 8001 (see docs/operations/OPERATIONS.md). */
export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000/api/v1'

export const TXT =
  'Tenancy agreement between landlord and tenant. Business profile ACRA UEN. Floor plan kitchen. Food hygiene certificate. '.repeat(3)
export const DOCUMENT_TYPES = ['business_profile', 'floor_plan', 'tenancy_agreement', 'food_hygiene_certificate'] as const

export const BUSINESS = {
  business_name: 'Scenario Kopi House Pte. Ltd.',
  uen: '202377777S',
  contact_name: 'Tan Wei Ling',
  contact_email: 'weiling@scenario.sg',
  contact_phone: '+65 9123 4567',
}
export const PREMISES = {
  address_line_1: '10 Jalan Besar #01-12',
  postal_code: '208787',
  floor_area_sqm: '48',
  tenancy_expiry: '2027-10-31',
}
export const OPERATIONS = {
  cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
  seating_capacity: '24',
  operating_hours: 'Mon-Sun 7am-9pm',
  food_handlers_count: '4',
}

// ---- UI helpers ----

export async function signIn(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel(/Email address/).fill(email)
  await page.getByLabel(/^Password/).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}

export async function signOut(page: Page) {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
}

export async function fillSection(page: Page, values: Record<string, string>, selects: Record<string, string> = {}) {
  for (const [name, value] of Object.entries(values)) await page.locator(`[name="${name}"]`).fill(value)
  for (const [name, value] of Object.entries(selects)) await page.locator(`select[name="${name}"]`).selectOption(value)
  await page.getByRole('button', { name: /Save and (continue|review|go to)/ }).click()
}

export async function uploadTxt(page: Page, slot: string, filename: string, text: string = TXT) {
  await page
    .locator(`#slot-${slot} input[type=file]`)
    .first()
    .setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(text) })
  await expect(page.locator(`#slot-${slot}`).getByText('Uploaded')).toBeVisible()
}

export function status(page: Page) {
  return page.locator('main span[data-tone]').first()
}

export async function confirmDialog(page: Page, button: string) {
  await page.locator('dialog[open]').getByRole('button', { name: button }).click()
}

export async function openCase(page: Page, reference: string) {
  await page.goto('/officer/queue')
  await page.getByRole('tab', { name: /All/ }).click()
  await page.getByRole('searchbox').fill(reference)
  await page
    .getByRole('link', { name: new RegExp(reference) })
    .first()
    .click()
  await expect(page.locator('main')).toContainText(reference)
}

/** Opens the audit trail on the case page and returns the summaries in order. */
export async function auditSummaries(page: Page): Promise<string[]> {
  const section = page.locator('section:has(#audit-title)')
  const toggle = section.getByRole('button', { name: /^(Show|Hide)$/ })
  await toggle.waitFor()
  if ((await toggle.innerText()) === 'Show') await toggle.click()
  await expect(section.locator('ol li').first()).toBeVisible()
  return section.locator('ol li > span:nth-child(3)').allInnerTexts()
}

// ---- API seeding (fast setup for officer-side scenarios; every scenario creates its own application) ----

type Headers = Record<string, string>

async function login(email: string): Promise<Headers> {
  const r = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: PASSWORD }),
  })
  if (!r.ok) throw new Error(`login ${email}: ${r.status}`)
  const body = (await r.json()) as { access_token?: string; token?: string }
  return { Authorization: `Bearer ${body.access_token ?? body.token ?? ''}` }
}

async function call<T>(headers: Headers, path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData
  const r = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...headers, ...(init.body && !isForm ? { 'Content-Type': 'application/json' } : {}) },
  })
  if (!r.ok) throw new Error(`${init.method ?? 'GET'} ${path}: ${r.status} ${await r.text()}`)
  return r.status === 204 ? (undefined as T) : ((await r.json()) as T)
}

export interface Seeded {
  id: string
  reference: string
  url: string
}

/** A complete, submitted application (Application Received). */
export async function seedSubmitted(): Promise<Seeded> {
  const op = await login(OPERATOR)
  const app = await call<{ id: string; reference_no: string }>(op, '/applications', { method: 'POST' })
  const id = app.id
  await call(op, `/applications/${id}/sections/business`, {
    method: 'PATCH',
    body: JSON.stringify({ ...BUSINESS, entity_type: 'private_limited' }),
  })
  await call(op, `/applications/${id}/sections/premises`, {
    method: 'PATCH',
    body: JSON.stringify({ ...PREMISES, floor_area_sqm: 48, premises_type: 'shophouse' }),
  })
  await call(op, `/applications/${id}/sections/operations`, {
    method: 'PATCH',
    body: JSON.stringify({ ...OPERATIONS, seating_capacity: 24, food_handlers_count: 4 }),
  })
  await call(op, `/applications/${id}/sections/declarations`, {
    method: 'PATCH',
    body: JSON.stringify({ information_accurate: true, consent_to_inspection: true }),
  })
  for (const t of DOCUMENT_TYPES) {
    const fd = new FormData()
    fd.append('document_type', t)
    fd.append('file', new Blob([TXT], { type: 'text/plain' }), `${t}.txt`)
    await call(op, `/applications/${id}/documents`, { method: 'POST', body: fd })
  }
  await call(op, `/applications/${id}/submit`, { method: 'POST' })
  return { id, reference: app.reference_no, url: `/app/applications/${id}` }
}

async function transition(off: Headers, id: string, target: string, note?: string) {
  const view = await call<{ version: number }>(off, `/officer/applications/${id}`)
  await call(off, `/officer/applications/${id}/transition`, {
    method: 'POST',
    body: JSON.stringify({ target, expected_version: view.version, ...(note ? { note } : {}) }),
  })
}

/** Submitted, then the officer started the review (Under Review). */
export async function seedUnderReview(): Promise<Seeded> {
  const seeded = await seedSubmitted()
  const off = await login(OFFICER)
  await transition(off, seeded.id, 'under_review')
  return seeded
}

/** Under review with one released feedback item on the premises section (Pending Pre-Site Resubmission). */
export async function seedPendingResubmission(message = 'Please confirm the premises unit number.'): Promise<Seeded> {
  const seeded = await seedUnderReview()
  const off = await login(OFFICER)
  await call(off, `/officer/applications/${seeded.id}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ target_type: 'section', section_key: 'premises', message }),
  })
  await transition(off, seeded.id, 'pending_pre_site_resubmission')
  return seeded
}
