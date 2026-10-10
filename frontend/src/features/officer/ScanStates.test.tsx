import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ClarificationOfficerView } from '@/api/clarification'
import type { ScanState } from '@/api/documents'
import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import type { OfficerDocument } from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { formSchema, officerView } from '@/test/fixtures'
import { OfficerCasePage } from './CasePage'

function docOf(label: string, scan_state: ScanState | undefined, over: Partial<OfficerDocument> = {}): OfficerDocument {
  const base = officerView().documents[0]!
  return { ...base, id: `doc-${label}`, document_type: label, label, original_filename: `${label}.pdf`, scan_state, ...over }
}

function renderWith(documents: OfficerDocument[]) {
  vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(officerView({ id: 'a1', documents }))
  render(
    <AppProviders>
      <MemoryRouter initialEntries={['/officer/applications/a1']}>
        <Routes>
          <Route path="/officer/applications/:id" element={<OfficerCasePage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

const rowOf = async (label: string) => (await screen.findByRole('heading', { name: label })).closest('li')!

describe('officer documents by scan state (US-099, artboard 2b)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
  })

  it('clean: Scan clean chip, Open enabled; blocked: no Open and the no-download alert; scanning: Open disabled with the wait line', async () => {
    renderWith([docOf('Clean', 'clean'), docOf('Held', 'scanning'), docOf('Bad', 'infected')])
    const clean = await rowOf('Clean')
    expect(within(clean).getByText('Scan clean')).toHaveAttribute('data-tone', 'success')
    expect(within(clean).getByRole('button', { name: 'Open' })).toBeEnabled()
    expect(within(clean).getByText('Verified')).toBeInTheDocument()

    const held = await rowOf('Held')
    expect(within(held).getByText('Scanning')).toHaveAttribute('data-tone', 'info')
    expect(within(held).getByRole('button', { name: 'Open' })).toBeDisabled()
    expect(within(held).getByText(/Not available to open yet. It opens when the security scan finishes/)).toBeInTheDocument()
    expect(within(held).queryByText('Verified')).not.toBeInTheDocument()

    const bad = await rowOf('Bad')
    expect(within(bad).getByText('Blocked')).toHaveAttribute('data-tone', 'error')
    expect(within(bad).queryByRole('button', { name: 'Open' })).not.toBeInTheDocument()
    expect(within(bad).getByText('Blocked, no download')).toBeInTheDocument()
    expect(within(bad).getByText(/cannot be opened or downloaded/)).toBeInTheDocument()
    expect(within(bad).getByText(/found a virus\.|found a virus on/)).toBeInTheDocument()
    expect(screen.getByText(/3 attached/)).toHaveTextContent('3 attached · 1 blocked · 1 scanning')
  })

  it('the blocked alert says when the virus was found, in Singapore time', async () => {
    renderWith([docOf('Bad', 'infected', { scanned_at: '2026-10-10T07:12:00Z' })])
    const row = await rowOf('Bad')
    expect(within(row).getByText(/The security scan found a virus on 10 Oct, 15:12\. The file is quarantined/)).toBeInTheDocument()
  })

  it('active content shows the note to the officer and Open stays available', async () => {
    renderWith([docOf('Tenancy', 'clean', { active_content: true })])
    const row = await rowOf('Tenancy')
    expect(within(row).getByText('This PDF contains active content')).toBeInTheDocument()
    expect(within(row).getByText(/Open it only in a viewer that blocks scripts/)).toBeInTheDocument()
    expect(within(row).getByRole('button', { name: 'Open' })).toBeEnabled()
  })

  it('a null scan state looks as before: Open enabled, no chip, no note', async () => {
    renderWith([docOf('Plain', null), docOf('Old', undefined)])
    const row = await rowOf('Plain')
    expect(within(row).getByRole('button', { name: 'Open' })).toBeEnabled()
    expect(screen.queryByText('Scan clean')).not.toBeInTheDocument()
    expect(screen.queryByText('Scanning')).not.toBeInTheDocument()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    expect(screen.queryByText(/active content/)).not.toBeInTheDocument()
    expect(screen.getByText(/2 attached/)).toHaveTextContent(/^2 attached$/)
  })
})

describe('officer clarification rail attachments (US-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
  })

  it('a blocked attachment cannot be opened and says so', async () => {
    const attachment = (id: string, name: string, scan_state: ScanState) => ({
      id,
      original_filename: name,
      content_type: 'image/jpeg',
      size_bytes: 1000,
      uploaded_at: '2026-09-25T01:05:00Z',
      scan_state,
    })
    const clarification: ClarificationOfficerView = {
      visit_no: 1,
      round: 1,
      open_count: 0,
      answered_count: 1,
      resolved_count: 0,
      withdrawn_count: 0,
      unreleased_count: 0,
      turn: 'Round 1, your turn',
      items: [
        {
          item_id: 'i1',
          key: 'floor_trap_graded',
          title: 'Floor trap',
          result: 'unsatisfactory',
          comment: 'Slopes away.',
          status: 'answered',
          round_no: 1,
          requests: [
            {
              id: 'q1',
              round_no: 1,
              message: 'Slopes away.',
              author_name: 'Rahim',
              created_at: '2026-09-22T08:40:00Z',
              released_at: '2026-09-22T08:40:00Z',
              withdrawn_at: null,
              response: {
                id: 'r1',
                round_no: 1,
                message: 'Regraded.',
                created_at: '',
                sent_at: '2026-09-25T01:12:00Z',
                attachments: [attachment('a1', 'bad.jpg', 'infected'), attachment('a2', 'ok.jpg', null)],
              },
            },
          ],
          can_resolve: true,
          can_reopen: true,
          can_withdraw: false,
          pending_release: false,
        },
      ],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(
      officerView({ id: 'a1', status: 'post_site_clarification_resubmitted', status_label: 'Post-Site Clarification Resubmitted', clarification }),
    )
    render(
      <AppProviders>
        <MemoryRouter initialEntries={['/officer/applications/a1']}>
          <Routes>
            <Route path="/officer/applications/:id" element={<OfficerCasePage />} />
          </Routes>
        </MemoryRouter>
      </AppProviders>,
    )
    expect(await screen.findByRole('button', { name: /bad\.jpg/ })).toBeDisabled()
    expect(screen.getByText('Blocked, cannot be opened')).toHaveAttribute('data-tone', 'error')
    expect(screen.getByRole('button', { name: /ok\.jpg/ })).toBeEnabled()
  })
})
