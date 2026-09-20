// k6 load test for the v0.4.0 admin and checklist paths (US-086, NFR-008, NFR-011, NFR-018).
// Seed a scratch database with scripts/load/seed_load.py, start the API against it, then:
//   k6 run -e BASE=http://localhost:8001/api/v1 -e APP=<checklist case id> scripts/load/permitflow.js
// Budgets: checklist save p95 < 300 ms, admin overview p95 < 500 ms, activity feed p95 < 200 ms.
import http from 'k6/http'
import { check } from 'k6'

const BASE = __ENV.BASE || 'http://localhost:8001/api/v1'
const APP = __ENV.APP
const PASSWORD = __ENV.SEED_PASSWORD || 'PermitFlow!2026'

export const options = {
  scenarios: {
    checklist_save: { executor: 'constant-vus', vus: 5, duration: '30s', exec: 'checklistSave' },
    admin_overview: { executor: 'constant-vus', vus: 5, duration: '30s', exec: 'adminOverview', startTime: '30s' },
    audit_feed: { executor: 'constant-vus', vus: 10, duration: '30s', exec: 'auditFeed', startTime: '60s' },
  },
  thresholds: {
    'http_req_duration{name:checklist_save}': ['p(95)<300'],
    'http_req_duration{name:admin_overview}': ['p(95)<500'],
    'http_req_duration{name:audit_feed}': ['p(95)<200'],
    http_req_failed: ['rate<0.01'],
  },
}

function login(email) {
  const r = http.post(`${BASE}/auth/login`, JSON.stringify({ email, password: PASSWORD, take_over: true }), {
    headers: { 'Content-Type': 'application/json' },
  })
  check(r, { 'signed in': (x) => x.status === 200 })
  return { Authorization: `Bearer ${r.json('access_token')}`, 'Content-Type': 'application/json' }
}

export function setup() {
  const officer = login('officer@permitflow.example.sg')
  const admin = login('admin@permitflow.example.sg')
  const schema = http.get(`${BASE}/checklist-schema`, { headers: officer }).json()
  const keys = schema.sections.flatMap((s) => s.items.map((i) => i.key))
  const created = http.post(`${BASE}/officer/applications/${APP}/checklist`, null, { headers: officer })
  return { officer, admin, keys, version: created.json('version') }
}

export function checklistSave(data) {
  // One session per account: every VU shares the officer's token from setup.
  const items = data.keys.map((key, i) => ({
    key,
    result: i % 3 === 0 ? 'unsatisfactory' : 'satisfactory',
    comment: i % 3 === 0 ? 'x'.repeat(1800) : null,
    needs_clarification: i % 6 === 0,
  }))
  const current = http.get(`${BASE}/officer/applications/${APP}/checklist`, { headers: data.officer, tags: { name: 'checklist_read' } })
  const r = http.put(`${BASE}/officer/applications/${APP}/checklist`, JSON.stringify({ items, version: current.json('version'), save_id: `${__VU}-${__ITER}` }), {
    headers: data.officer,
    tags: { name: 'checklist_save' },
  })
  check(r, { 'save 200 or 409 (another VU saved first)': (x) => x.status === 200 || x.status === 409 })
}

export function adminOverview(data) {
  const r = http.get(`${BASE}/admin/overview`, { headers: data.admin, tags: { name: 'admin_overview' } })
  check(r, { 'overview 200': (x) => x.status === 200 })
}

export function auditFeed(data) {
  let cursor = null
  for (let page = 0; page < 3; page += 1) {
    const url = `${BASE}/admin/audit-feed?limit=50${cursor ? `&before=${cursor}` : ''}`
    const r = http.get(url, { headers: data.admin, tags: { name: 'audit_feed' } })
    check(r, { 'feed 200': (x) => x.status === 200 })
    cursor = r.json('next_cursor')
    if (!cursor) break
  }
}
