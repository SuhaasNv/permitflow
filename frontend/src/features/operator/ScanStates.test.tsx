import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as appsApi from '@/api/applications'
import type { DocumentSlotView } from '@/api/applications'
import { AppError } from '@/api/client'
import * as clarApi from '@/api/clarification'
import type { ClarificationView } from '@/api/clarification'
import * as docsApi from '@/api/documents'
import type { ScanState } from '@/api/documents'
import * as formApi from '@/api/formSchema'
import { AppProviders } from '@/app/providers'
import { applicationView, formSchema, sectionView, slotView } from '@/test/fixtures'
import { ClarificationPage } from './ClarificationPage'
import { DocumentsPage } from './DocumentsPage'
import { DocumentSlot } from './documents/DocumentSlot'
import { ReviewPage } from './ReviewPage'

const BLOCKED = 'This file was blocked by the security check. Upload a different copy.'

function scanned(type: string, scan_state: ScanState | undefined, over: Partial<DocumentSlotView> = {}): DocumentSlotView {
  const base = slotView(type, { editable: true, ...over })
  const document = { ...base.document!, scan_state }
  if (scan_state === 'infected')
    document.verification = { ...document.verification!, status: 'unreadable', summary: null, error_reason: 'file_infected' }
  if (scan_state === 'scanning') document.verification = { ...document.verification!, status: 'pending', summary: null }
  return { ...base, document }
}

function renderSlot(slot: DocumentSlotView) {
  render(
    <AppProviders>
      <DocumentSlot applicationId="app-1" slot={slot} index={0} canDelete onUploaded={vi.fn()} onDeleted={vi.fn()} />
    </AppProviders>,
  )
}

describe('operator document slot by scan state (US-099, artboard 2a)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('a blocked file shows the red message, the Blocked chip, no Download and no document check', () => {
    renderSlot(scanned('floor_plan', 'infected'))
    expect(screen.getByText(BLOCKED)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(BLOCKED)
    expect(screen.getByText('Blocked')).toHaveAttribute('data-tone', 'error')
    expect(screen.queryByRole('button', { name: /^Download / })).not.toBeInTheDocument()
    expect(screen.queryByText('Could not read this document')).not.toBeInTheDocument()
    expect(screen.getByText('Upload a different copy')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove' })).toBeInTheDocument()
  })

  it('a different copy goes through the normal upload', async () => {
    const upload = vi.spyOn(docsApi, 'uploadDocument').mockRejectedValue(new Error('stop'))
    renderSlot(scanned('floor_plan', 'infected'))
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['x'], 'clean.pdf', { type: 'application/pdf' }))
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1))
  })

  it('a file being scanned shows the scanning block, a disabled Download with its reason and no Replace', () => {
    renderSlot(scanned('floor_plan', 'scanning'))
    expect(screen.getByText('Scanning')).toHaveAttribute('data-tone', 'info')
    expect(screen.getByText('Scanning for viruses')).toBeInTheDocument()
    expect(screen.getByText(/You can leave this page; the check carries on/)).toBeInTheDocument()
    expect(screen.getByText('Next: the document check, which starts when the security check passes.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Download / })).toBeDisabled()
    expect(screen.getByText('Available after the security check')).toBeInTheDocument()
    expect(screen.queryByText('Replace file')).not.toBeInTheDocument()
    expect(screen.queryByText('Queued for checking')).not.toBeInTheDocument()
  })

  it('a clean file shows the security result beside the document check', () => {
    renderSlot(scanned('floor_plan', 'clean'))
    expect(screen.getByText('No virus found')).toBeInTheDocument()
    expect(screen.getByText('Security check')).toBeInTheDocument()
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Download / })).toBeEnabled()
    expect(screen.getByText('Replace file')).toBeInTheDocument()
  })

  it('a clean file says when it was scanned, in Singapore time', () => {
    const slot = scanned('floor_plan', 'clean')
    renderSlot({ ...slot, document: { ...slot.document!, scanned_at: '2026-10-10T06:02:00Z' } })
    expect(screen.getByText('Scanned 10 Oct, 14:02. The file can be opened.')).toBeInTheDocument()
  })

  it('a clean file without a scan time still reads The file can be opened.', () => {
    renderSlot(scanned('floor_plan', 'clean'))
    expect(screen.getByText('The file can be opened.')).toBeInTheDocument()
  })

  it('a null scan state (scan off) looks as before: no security block, no scan chip', () => {
    renderSlot(scanned('floor_plan', null))
    expect(screen.queryByText('Security check')).not.toBeInTheDocument()
    expect(screen.queryByText('No virus found')).not.toBeInTheDocument()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    expect(screen.getByText('Uploaded')).toBeInTheDocument()
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Download / })).toBeEnabled()
    expect(screen.getByText('Replace file')).toBeInTheDocument()
  })

  it('an upload refused with scanner_unavailable says so in the agreed words', async () => {
    vi.spyOn(docsApi, 'uploadDocument').mockRejectedValue(new AppError(503, { code: 'scanner_unavailable', message: 'raw server text' }))
    renderSlot({ type: 'floor_plan', label: 'Floor plan', present: false, editable: true, document: null })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['x'], 'a.pdf', { type: 'application/pdf' }))
    expect(await screen.findByText('The security check is not available right now. Try again in a moment.')).toBeInTheDocument()
  })

  it('a download refused with file_scanning is explained', async () => {
    vi.spyOn(docsApi, 'downloadDocument').mockRejectedValue(
      new AppError(409, { code: 'file_scanning', message: docsApi.scanMessage(new AppError(409, { code: 'file_scanning', message: '' }))! }),
    )
    renderSlot(scanned('floor_plan', 'clean'))
    await userEvent.click(screen.getByRole('button', { name: /^Download / }))
    expect(await screen.findByText('This file is still being scanned. Try again in a moment.')).toBeInTheDocument()
  })
})

function renderRoutes(path: string) {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/applications/:id/documents" element={<DocumentsPage />} />
          <Route path="/app/applications/:id/review" element={<ReviewPage />} />
          <Route path="/app/applications/:id/clarification" element={<ClarificationPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

const HOLD = 'Review and submit opens when no document is blocked or being scanned.'

/** What the backend sends: with a reason, can_submit is false. */
const draft = (slots: DocumentSlotView[], reason: string | null = null, documentsPresent = slots.length) => {
  const base = applicationView()
  return applicationView({
    completeness: { ...base.completeness, documents_present: documentsPresent, documents_total: slots.length },
    status_label: 'Draft',
    status_tone: 'neutral',
    can_edit: true,
    can_submit: reason === null,
    submit_blocked_reason: reason,
    revision_count: 0,
    revisions: [],
    sections: [sectionView('business', { editable: true }), sectionView('premises', { editable: true })],
    document_slots: slots,
  })
}

describe('Documents page and Review page with a blocked or scanning document (US-099)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('disables Review and submit with its reason and counts only the clear documents as ready', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', 'clean'), scanned('floor_plan', 'scanning')], `${HOLD} 1 being scanned.`, 1))
    renderRoutes('/app/applications/app-1/documents')
    expect(await screen.findByText('Review and submit opens when no document is blocked or being scanned. 1 being scanned.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review and submit' })).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Review and submit' })).not.toBeInTheDocument()
    expect(screen.getByText('1/2')).toBeInTheDocument()
  })

  it('shows the backend documents_present as is, never below zero (scanning and blocked slots)', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', 'scanning'), scanned('floor_plan', 'scanning')], `${HOLD} 2 being scanned.`, 0))
    const { unmount } = renderRoutes('/app/applications/app-1/documents')
    expect(await screen.findByText('0/2')).toBeInTheDocument()
    unmount()
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', 'clean'), scanned('floor_plan', 'infected')], `${HOLD} 1 blocked.`, 1))
    renderRoutes('/app/applications/app-1/documents')
    expect(await screen.findByText('1/2')).toBeInTheDocument()
  })

  it('a blocked document adds the rail note and a Blocked chip', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', 'clean'), scanned('floor_plan', 'infected')], `${HOLD} 1 blocked.`))
    renderRoutes('/app/applications/app-1/documents')
    expect(await screen.findByText('A blocked file does not count. Upload a different copy to continue.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review and submit' })).toBeDisabled()
  })

  it('with the scan off the page is as today: an enabled link and no gate text', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', null), scanned('floor_plan', undefined)]))
    renderRoutes('/app/applications/app-1/documents')
    expect(await screen.findByRole('link', { name: 'Review and submit' })).toHaveAttribute('href', '/app/applications/app-1/review')
    expect(screen.queryByText(/opens when no document/)).not.toBeInTheDocument()
    expect(screen.getByText('2/2')).toBeInTheDocument()
  })

  it('the review page disables Submit with the reason and lists the held documents with their state', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', 'infected'), scanned('floor_plan', 'scanning')], `${HOLD} 1 blocked, 1 being scanned.`))
    renderRoutes('/app/applications/app-1/review')
    expect(await screen.findByRole('button', { name: 'Submit application' })).toBeDisabled()
    expect(screen.getByText(`${HOLD} 1 blocked, 1 being scanned.`)).toBeInTheDocument()
    expect(screen.getAllByText('Blocked')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Scanning')[0]).toBeInTheDocument()
  })

  it('a 409 documents_not_clear on submit shows the scan message, not "Already submitted"', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft([scanned('business_profile', null), scanned('floor_plan', null)]))
    vi.spyOn(appsApi, 'submitApplication').mockRejectedValue(
      new AppError(409, { code: 'documents_not_clear', message: 'server wording', details: { reason: 'documents_not_clear' } }),
    )
    renderRoutes('/app/applications/app-1/review')
    await userEvent.click(await screen.findByRole('button', { name: 'Submit application' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Submit application' }).at(-1)!)
    expect(await screen.findByText('Review and submit opens when no document is blocked or being scanned.')).toBeInTheDocument()
    expect(screen.queryByText('Already submitted')).not.toBeInTheDocument()
  })
})

const clarApp = applicationView({
  id: 'a1',
  status_label: 'Pending Post-Site Clarification',
  needs_operator_action: true,
  clarification: { can_respond: true, open_count: 1, answered_count: 0, round: 1 },
})

function clarView(attachments: ClarificationView['items'][number]['responses'][number]['attachments']): ClarificationView {
  return {
    application_id: 'a1',
    visit_no: 1,
    items: [
      {
        item_id: 'i1',
        key: 'floor_trap_graded',
        title: 'Floor trap',
        guidance: '',
        status: 'Waiting for your response',
        round_no: 1,
        requests: [{ id: 'q1', round_no: 1, message: 'Send a photo.', released_at: '2026-09-24T08:40:00Z' }],
        responses: [{ id: 'r1', round_no: 1, message: 'Done.', created_at: '', sent_at: null, attachments }],
        can_respond: true,
      },
    ],
    open_count: 1,
    answered_count: 0,
    resolved_count: 0,
    round: 1,
    can_respond: true,
    can_send: true,
    storage: null,
  }
}

const att = (scan_state: ScanState | undefined) => ({
  id: 'att1',
  original_filename: 'floor.jpg',
  content_type: 'image/jpeg',
  size_bytes: 2048,
  uploaded_at: '2026-09-25T01:01:00Z',
  scan_state,
})

describe('clarification attachments with a blocked file (US-099)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('a blocked attachment is a red row with the message, cannot be opened, can be removed, and holds the send', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(clarApp)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(clarView([att('infected')]))
    const download = vi.spyOn(clarApi, 'downloadAttachment')
    renderRoutes('/app/applications/a1/clarification')
    const row = (await screen.findByText(BLOCKED)).closest('li')!
    expect(within(row).getByText('Blocked')).toHaveAttribute('data-tone', 'error')
    expect(within(row).getByRole('button', { name: /^Open floor.jpg/ })).toBeDisabled()
    expect(within(row).getByRole('button', { name: 'Remove' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Send responses' })).toBeDisabled()
    expect(screen.getByText('Remove the file the security check blocked, then send your answers.')).toBeInTheDocument()
    expect(download).not.toHaveBeenCalled()
  })

  it('a null or clean attachment opens and the send stays open (scan off unchanged)', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(clarApp)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(clarView([att(null)]))
    renderRoutes('/app/applications/a1/clarification')
    expect(await screen.findByRole('button', { name: /^Open floor.jpg/ })).toBeEnabled()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send responses' })).toBeEnabled()
  })

  it('a 422 file_infected on upload shows the agreed message and loads the blocked row', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(clarApp)
    const list = vi.spyOn(clarApi, 'getClarifications').mockResolvedValueOnce(clarView([])).mockResolvedValue(clarView([att('infected')]))
    vi.spyOn(clarApi, 'attachToResponse').mockRejectedValue(
      new AppError(422, { code: 'file_infected', message: 'x', details: { reason: 'file_infected' } }),
    )
    renderRoutes('/app/applications/a1/clarification')
    await screen.findByRole('button', { name: 'Choose a file' })
    await userEvent.upload(document.querySelector('input[type=file][multiple]') as HTMLInputElement, new File(['x'], 'floor.jpg', { type: 'image/jpeg' }))
    expect((await screen.findAllByText(BLOCKED)).length).toBeGreaterThan(0)
    await waitFor(() => expect(list.mock.calls.length).toBeGreaterThan(1))
  })

  it('a 503 scanner_unavailable is said plainly and not retried silently', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(clarApp)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(clarView([]))
    const attach = vi
      .spyOn(clarApi, 'attachToResponse')
      .mockRejectedValue(new AppError(503, { code: 'scanner_unavailable', message: 'x' }))
    renderRoutes('/app/applications/a1/clarification')
    await screen.findByRole('button', { name: 'Choose a file' })
    await userEvent.upload(document.querySelector('input[type=file][multiple]') as HTMLInputElement, new File(['x'], 'floor.jpg', { type: 'image/jpeg' }))
    expect(await screen.findByText('The security check is not available right now. Try again in a moment.')).toBeInTheDocument()
    expect(screen.queryByText(/trying again/)).not.toBeInTheDocument()
    expect(attach).toHaveBeenCalledTimes(1)
  })
})
