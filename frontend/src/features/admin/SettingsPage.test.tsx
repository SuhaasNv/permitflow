import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/admin'
import type { PlatformSetting, PlatformSettings, SettingHistoryEntry, SettingsHistory } from '@/api/admin'
import { AppError } from '@/api/client'
import { AppProviders } from '@/app/providers'
import { AdminSettingsPage } from './SettingsPage'

const MB = 1024 * 1024

function setting(over: Partial<PlatformSetting> & Pick<PlatformSetting, 'key' | 'label'>): PlatformSetting {
  return {
    description: 'A setting.',
    group: 'traffic',
    kind: 'int',
    unit: 'requests',
    value: 240,
    default: 240,
    overridden: false,
    minimum: 10,
    maximum: 240,
    max_source: 'env',
    choices: [],
    in_use: true,
    updated_by_name: null,
    updated_at: null,
    reason: null,
    ...over,
  }
}

const rate = setting({
  key: 'rate_limit_per_minute',
  label: 'Requests per minute per client',
  description: 'Every request from one client address, sliding minute.',
  value: 180,
  overridden: true,
  updated_by_name: 'Priya Nair',
  updated_at: '2026-10-09T09:31:00Z',
  reason: 'Scraper traffic from one address range',
})
const login = setting({
  key: 'login_attempts_per_minute',
  label: 'Sign-in attempts per minute per client',
  unit: 'attempts',
  value: 20,
  default: 20,
  minimum: 3,
  maximum: 20,
})
const perDay = setting({
  key: 'ai_runs_per_day',
  label: 'AI checks per platform per day',
  group: 'ai',
  unit: 'checks',
  value: 600,
  default: 1000,
  minimum: 1,
  maximum: 1000,
  overridden: true,
  updated_by_name: 'Priya Nair',
  updated_at: '2026-10-10T01:14:00Z',
  reason: 'Cost brake while the price list is checked',
})
const paused = setting({
  key: 'ai_paused',
  label: 'Pause AI checks',
  group: 'ai',
  kind: 'bool',
  unit: '',
  value: false,
  default: false,
  minimum: null,
  maximum: null,
  max_source: 'none',
})
const telegram = setting({
  key: 'telegram_per_check_messages',
  label: 'Telegram message per check',
  group: 'system',
  kind: 'bool',
  unit: '',
  value: false,
  default: false,
  minimum: null,
  maximum: null,
  max_source: 'none',
  in_use: false,
})
const upload = setting({
  key: 'upload_max_bytes',
  label: 'Upload size',
  group: 'uploads',
  unit: 'bytes',
  value: 10 * MB,
  default: 10 * MB,
  minimum: MB,
  maximum: 10 * MB,
  max_source: 'cap',
})
const drafts = setting({
  key: 'max_drafts_per_user',
  label: 'Drafts per person',
  group: 'traffic',
  unit: 'drafts',
  value: 20,
  default: 20,
  minimum: 1,
  maximum: 20,
})
const scanner = setting({
  key: 'scanner_fail_mode',
  label: 'Virus scanner failure mode',
  group: 'uploads',
  kind: 'choice',
  unit: '',
  value: 'retry',
  default: 'retry',
  minimum: null,
  maximum: null,
  max_source: 'none',
  choices: ['retry', 'hold'],
  in_use: false,
})

const all: PlatformSettings = { environment: 'development', settings: [drafts, upload, paused, perDay, scanner, telegram, rate, login] }

function entry(over: Partial<SettingHistoryEntry> & Pick<SettingHistoryEntry, 'id'>): SettingHistoryEntry {
  return {
    kind: 'changed',
    key: 'rate_limit_per_minute',
    label: 'Requests per minute per client',
    old: 240,
    new: 180,
    old_was_default: true,
    reason: 'Scraper traffic from one address range',
    actor_name: 'Priya Nair',
    created_at: '2026-10-09T09:31:00Z',
    reverted_event_id: null,
    ...over,
  }
}

const rateEntry = entry({ id: 'h-rate' })
const reverted = entry({
  id: 'h-rev',
  kind: 'reverted',
  key: 'max_drafts_per_user',
  label: 'Drafts per person',
  old: 10,
  new: 20,
  old_was_default: false,
  reason: 'Reverted: the limit was blocking a branch office',
  created_at: '2026-10-02T06:05:00Z',
})
const page1: SettingsHistory = { entries: [rateEntry, reverted], next_cursor: 'c1' }

function renderPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <AdminSettingsPage />
      </MemoryRouter>
    </AppProviders>,
  )
}

function mockLoad(settings: PlatformSettings = all, history: SettingsHistory = page1) {
  vi.spyOn(api, 'getPlatformSettings').mockResolvedValue(settings)
  return vi.spyOn(api, 'getSettingsHistory').mockResolvedValue(history)
}

/** The row a key names: the key is shown once on the page, the label also appears in the history. */
const rowOf = (key: string) => screen.getByText(key).closest('li')!
const PASSWORD = 'Admin-Own-Pass-1'

describe('admin settings page (US-101)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('lists the three groups with each row filed as designed, and says what each value is', async () => {
    mockLoad()
    renderPage()
    expect(await screen.findByText('2 of 8 overridden')).toBeInTheDocument()
    // The newest history entry (9 Oct), not the newest row that is still overridden (10 Oct).
    expect(screen.getByText(/Last change 9 Oct 2026, 17:31 by Priya Nair/)).toBeInTheDocument()
    const traffic = screen.getByRole('region', { name: 'Traffic' })
    const ai = screen.getByRole('region', { name: 'AI checks' })
    const uploads = screen.getByRole('region', { name: 'Uploads' })
    expect(within(traffic).getByText('Requests per minute per client')).toBeInTheDocument()
    expect(within(ai).getByText('Telegram message per check')).toBeInTheDocument()
    expect(within(uploads).getByText('Drafts per person')).toBeInTheDocument()
    expect(within(uploads).getByText('Virus scanner failure mode')).toBeInTheDocument()
    expect(within(traffic).queryByText('Drafts per person')).not.toBeInTheDocument()

    const row = rowOf('rate_limit_per_minute')
    expect(within(row).getByText('rate_limit_per_minute')).toBeInTheDocument()
    expect(within(row).getByText('Overridden')).toBeInTheDocument()
    expect(within(row).getByText('10 to 240')).toBeInTheDocument()
    expect(within(row).getByText('Ceiling set by the environment')).toBeInTheDocument()
    expect(within(row).getByText('Priya Nair')).toBeInTheDocument()
    expect(within(row).getByText('9 Oct 2026, 17:31')).toBeInTheDocument()
    expect(within(row).getByText('Scraper traffic from one address range')).toBeInTheDocument()
    expect(within(rowOf('login_attempts_per_minute')).getByText('Default in force')).toBeInTheDocument()
    expect(within(rowOf('login_attempts_per_minute')).getByText('No change yet')).toBeInTheDocument()

    const size = rowOf('upload_max_bytes')
    expect(within(size).getAllByText('10 MB').length).toBeGreaterThanOrEqual(2)
    expect(within(size).getByText('1 MB to 10 MB')).toBeInTheDocument()
    expect(within(size).getByText('Absolute cap of the brief')).toBeInTheDocument()
    expect(within(rowOf('telegram_per_check_messages')).getByText('Takes effect once AI usage records are live.')).toBeInTheDocument()
    expect(within(rowOf('scanner_fail_mode')).getByText('Takes effect once the virus scan is live.')).toBeInTheDocument()
    expect(within(rowOf('scanner_fail_mode')).getByText('Retry or Hold')).toBeInTheDocument()
    expect(within(rowOf('scanner_fail_mode')).getByText(/retry checks it again automatically \(up to 3 times\), hold waits/)).toBeInTheDocument()
    expect(screen.queryByText(/not allowed in production/)).not.toBeInTheDocument()
    // No pause banner while the AI runs.
    expect(screen.queryByText('AI checks are paused')).not.toBeInTheDocument()
  })

  it('has no em dash in what it says', async () => {
    mockLoad()
    renderPage()
    await screen.findByText('2 of 8 overridden')
    expect(document.body.textContent).not.toContain(String.fromCharCode(0x2014))
  })

  it('shows loading, then an error with a retry, then nothing-to-show', async () => {
    vi.spyOn(api, 'getSettingsHistory').mockResolvedValue({ entries: [], next_cursor: null })
    const get = vi.spyOn(api, 'getPlatformSettings').mockRejectedValueOnce(new AppError(403, { code: 'forbidden', message: 'Not available for your role.' }))
    const { unmount } = renderPage()
    expect(screen.getByRole('status', { name: 'Loading settings' })).toBeInTheDocument()
    const retry = await screen.findByRole('button', { name: 'Try again' })
    get.mockResolvedValueOnce({ environment: 'development', settings: [] })
    await userEvent.click(retry)
    expect(await screen.findByText('No settings to show')).toBeInTheDocument()
    unmount()
  })

  it('says so when there is no history, and when a filtered setting has none', async () => {
    mockLoad(all, { entries: [], next_cursor: null })
    renderPage()
    expect(await screen.findByText('No changes yet')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/^Setting/), 'ai_paused')
    expect(await screen.findByText('No changes to this setting yet')).toBeInTheDocument()
  })

  describe('the change dialog', () => {
    it('opens on the new value, shows now, default and allowed, and the old-to-new line', async () => {
      mockLoad()
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Requests per minute per client' }))
      const dialog = await screen.findByRole('dialog', { name: 'Change requests per minute per client?' })
      expect(within(dialog).getByLabelText(/New value/)).toHaveFocus()
      expect(within(dialog).getByText('180 requests')).toBeInTheDocument()
      expect(within(dialog).getByText('240 requests')).toBeInTheDocument()
      expect(within(dialog).getByText('10 to 240')).toBeInTheDocument()
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '200')
      const line = within(dialog).getByText('Change').parentElement!
      expect(line).toHaveTextContent('180')
      expect(line).toHaveTextContent('200')
      expect(within(dialog).getByText('0 / 280')).toBeInTheDocument()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Load test finished')
      expect(within(dialog).getByText('18 / 280')).toBeInTheDocument()
    })

    it('refuses a value outside the range with the server sentence, before asking for anything', async () => {
      mockLoad()
      const put = vi.spyOn(api, 'changePlatformSetting')
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Sign-in attempts per minute per client' }))
      const dialog = await screen.findByRole('dialog', { name: /Change sign-in attempts/ })
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '0')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(
        within(dialog).getByText('Sign-in attempts per minute per client cannot go below 3; a limit cannot be switched off from the panel.'),
      ).toBeInTheDocument()
      expect(within(dialog).getByText('Say why in at least 3 characters.')).toBeInTheDocument()
      expect(within(dialog).getByText('Enter your password to confirm.')).toBeInTheDocument()
      await userEvent.clear(field)
      await userEvent.type(field, '25')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(
        within(dialog).getByText('Sign-in attempts per minute per client cannot go above 20 (the environment ceiling).'),
      ).toBeInTheDocument()
      expect(put).not.toHaveBeenCalled()
    })

    it('sends the value, reason and password, then shows what the server returned', async () => {
      mockLoad()
      const put = vi
        .spyOn(api, 'changePlatformSetting')
        .mockResolvedValue({ ...rate, value: 200, updated_at: '2026-10-10T02:00:00Z', reason: 'Load test finished' })
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Requests per minute per client' }))
      const dialog = await screen.findByRole('dialog', { name: /Change requests per minute/ })
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '200')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), '  Load test finished  ')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      await waitFor(() =>
        expect(put).toHaveBeenCalledWith('rate_limit_per_minute', { value: 200, reason: 'Load test finished', password: PASSWORD }),
      )
      await waitFor(() => expect(screen.queryByRole('dialog', { name: /Change requests per minute/ })).not.toBeInTheDocument())
      expect(within(rowOf('rate_limit_per_minute')).getByText('Load test finished')).toBeInTheDocument()
    })

    it('puts a wrong password under the password field and keeps everything typed', async () => {
      mockLoad()
      vi.spyOn(api, 'changePlatformSetting').mockRejectedValue(
        new AppError(403, { code: 'step_up_failed', message: 'Your password is incorrect. The change was not made.' }),
      )
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Requests per minute per client' }))
      const dialog = await screen.findByRole('dialog', { name: /Change requests per minute/ })
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '200')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Load test finished')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), 'nope')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      const message = await within(dialog).findByText('Your password is incorrect. The change was not made.')
      expect(message).toBeInTheDocument()
      expect(within(dialog).getByLabelText(/Your password/)).toHaveAttribute('aria-invalid', 'true')
      expect(within(dialog).getByLabelText(/New value/)).toHaveValue('200')
      expect(within(dialog).getByLabelText(/Reason/)).toHaveValue('Load test finished')
    })

    it('puts the server bound sentence under the new value', async () => {
      mockLoad()
      vi.spyOn(api, 'changePlatformSetting').mockRejectedValue(
        new AppError(422, {
          code: 'validation_failed',
          message: 'Drafts per person cannot go above 15 (the environment ceiling).',
          details: { key: 'max_drafts_per_user', reason: 'above_maximum' },
        }),
      )
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Drafts per person' }))
      const dialog = await screen.findByRole('dialog', { name: 'Change drafts per person?' })
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '12')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Branch office')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(await within(dialog).findByText('Drafts per person cannot go above 15 (the environment ceiling).')).toBeInTheDocument()
      expect(within(dialog).getByLabelText(/New value/)).toHaveAttribute('aria-invalid', 'true')
    })

    it('describes the dialog by its short text, sends once however often Save is pressed, and takes Enter in a field', async () => {
      mockLoad()
      let finish: (s: PlatformSetting) => void = () => undefined
      const put = vi.spyOn(api, 'changePlatformSetting').mockReturnValue(new Promise((resolve) => (finish = resolve)))
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Requests per minute per client' }))
      const dialog = await screen.findByRole('dialog', { name: /Change requests per minute/ })
      const described = document.getElementById(dialog.getAttribute('aria-describedby') ?? '')
      expect(described).toHaveTextContent('Every request from one client address, sliding minute.')
      expect(described).not.toContainElement(within(dialog).getByLabelText(/New value/))
      const field = within(dialog).getByLabelText(/New value/)
      await userEvent.clear(field)
      await userEvent.type(field, '200')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Load test finished')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), `${PASSWORD}{Enter}`)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(put).toHaveBeenCalledTimes(1)
      finish({ ...rate, value: 200 })
      await waitFor(() => expect(screen.queryByRole('dialog', { name: /Change requests per minute/ })).not.toBeInTheDocument())
      // Reopened, nothing typed before is left, the password least of all.
      await userEvent.click(screen.getByRole('button', { name: 'Change Requests per minute per client' }))
      const again = await screen.findByRole('dialog', { name: /Change requests per minute/ })
      expect(within(again).getByLabelText(/Your password/)).toHaveValue('')
      expect(within(again).getByLabelText(/Reason/)).toHaveValue('')
    })

    it('sets a ceiling that is not a whole step of MB, and sees an untouched value as no change', async () => {
      const odd = { ...upload, value: 4_000_000, maximum: 5_000_000 }
      mockLoad({ environment: 'development', settings: [odd] })
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({ ...odd, value: 5_000_000 })
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Upload size' }))
      const dialog = await screen.findByRole('dialog', { name: 'Change upload size?' })
      const field = within(dialog).getByLabelText(/New value/)
      expect(field).toHaveValue('3.81')
      expect(within(dialog).getByText('1 MB to 4.77 MB')).toBeInTheDocument()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Use the whole ceiling')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      // Untouched: what the page shows for the current value is the current value.
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(within(dialog).getByText('Upload size is already 3.81 MB.')).toBeInTheDocument()
      expect(put).not.toHaveBeenCalled()
      await userEvent.clear(field)
      await userEvent.type(field, '4.77')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('upload_max_bytes', { value: 5_000_000, reason: 'Use the whole ceiling', password: PASSWORD }))
    })

    it('shows the upload size in MB and sends bytes', async () => {
      mockLoad()
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({ ...upload, value: 5 * MB, overridden: true })
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Upload size' }))
      const dialog = await screen.findByRole('dialog', { name: 'Change upload size?' })
      const field = within(dialog).getByLabelText(/New value/)
      expect(field).toHaveValue('10')
      expect(within(dialog).getByText('MB')).toBeInTheDocument()
      await userEvent.clear(field)
      await userEvent.type(field, '12')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Smaller files only')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      expect(await within(dialog).findByText('Upload size cannot go above 10 MB (the absolute cap).')).toBeInTheDocument()
      await userEvent.clear(field)
      await userEvent.type(field, '5')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('upload_max_bytes', { value: 5242880, reason: 'Smaller files only', password: PASSWORD }))
    })

    it('changes the scanner mode from a list of the allowed choices', async () => {
      mockLoad()
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({ ...scanner, value: 'hold', overridden: true })
      renderPage()
      await userEvent.click(await screen.findByRole('button', { name: 'Change Virus scanner failure mode' }))
      const dialog = await screen.findByRole('dialog', { name: /Change virus scanner failure mode/ })
      await userEvent.selectOptions(within(dialog).getByLabelText(/New value/), 'hold')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Scanner maintenance')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Save change' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('scanner_fail_mode', { value: 'hold', reason: 'Scanner maintenance', password: PASSWORD }))
    })
  })

  describe('switches', () => {
    it('asks before flipping a switch, and sends the opposite value once confirmed', async () => {
      mockLoad()
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({ ...telegram, value: true, overridden: true })
      renderPage()
      const toggle = await screen.findByRole('switch', { name: 'Telegram message per check' })
      expect(toggle).toHaveAttribute('aria-checked', 'false')
      await userEvent.click(toggle)
      expect(toggle).toHaveAttribute('aria-checked', 'false')
      const dialog = await screen.findByRole('dialog', { name: 'Switch Telegram message per check on?' })
      expect(within(dialog).getByLabelText(/Reason/)).toHaveFocus()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Trial for a week')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Switch on' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('telegram_per_check_messages', { value: true, reason: 'Trial for a week', password: PASSWORD }))
      await waitFor(() => expect(screen.getByRole('switch', { name: 'Telegram message per check' })).toHaveAttribute('aria-checked', 'true'))
    })

    it('keyboard: space opens the confirmation from the focused switch', async () => {
      mockLoad()
      renderPage()
      const toggle = await screen.findByRole('switch', { name: 'Pause AI checks' })
      toggle.focus()
      await userEvent.keyboard(' ')
      expect(await screen.findByRole('dialog', { name: 'Pause AI checks?' })).toBeInTheDocument()
    })

    it('words the pause confirmation and sends true', async () => {
      mockLoad()
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({
        ...paused,
        value: true,
        overridden: true,
        updated_by_name: 'Priya Nair',
        updated_at: '2026-10-10T00:50:00Z',
        reason: 'Provider outage',
      })
      renderPage()
      await userEvent.click(await screen.findByRole('switch', { name: 'Pause AI checks' }))
      const dialog = await screen.findByRole('dialog', { name: 'Pause AI checks?' })
      expect(within(dialog).getByText(/Stops spend and provider calls at once/)).toBeInTheDocument()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Provider outage')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Pause AI checks' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('ai_paused', { value: true, reason: 'Provider outage', password: PASSWORD }))
      expect(await screen.findByText('AI checks are paused')).toBeInTheDocument()
      expect(screen.getByText('On, paused')).toBeInTheDocument()
    })
  })

  describe('the pause banner', () => {
    const pausedOn: PlatformSetting = {
      ...paused,
      value: true,
      overridden: true,
      updated_by_name: 'Priya Nair',
      updated_at: '2026-10-10T00:50:00Z',
      reason: 'Provider outage reported',
    }

    it('shows while paused with who and when, and Switch back on turns the AI on again', async () => {
      mockLoad({ environment: 'development', settings: [rate, pausedOn] })
      const put = vi.spyOn(api, 'changePlatformSetting').mockResolvedValue({ ...pausedOn, value: false, overridden: false })
      renderPage()
      expect(await screen.findByText('AI checks are paused')).toBeInTheDocument()
      expect(screen.getByText(/New uploads are stored without a check\. Switched on 10 Oct 2026, 08:50 by Priya Nair\./)).toBeInTheDocument()
      expect(screen.getByText('On, paused')).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Switch back on' }))
      const dialog = await screen.findByRole('dialog', { name: 'Switch AI checks back on?' })
      expect(within(dialog).getByText(/The pause started 10 Oct 2026, 08:50 and ran for/)).toBeInTheDocument()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Provider recovered')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Switch on' }))
      await waitFor(() => expect(put).toHaveBeenCalledWith('ai_paused', { value: false, reason: 'Provider recovered', password: PASSWORD }))
      await waitFor(() => expect(screen.queryByText('AI checks are paused')).not.toBeInTheDocument())
      // The banner and its button are gone: focus lands on the switch, not on the page.
      await waitFor(() => expect(screen.getByRole('switch', { name: 'Pause AI checks' })).toHaveFocus())
    })
  })

  describe('history', () => {
    it('lists newest first with the revert tag, filters by setting and loads older changes', async () => {
      const history = mockLoad()
      history.mockResolvedValueOnce(page1).mockResolvedValueOnce({ entries: [entry({ id: 'h-old', label: 'Upload size', key: 'upload_max_bytes', old: 10 * MB, new: 5 * MB, created_at: '2026-09-30T02:00:00Z' })], next_cursor: null })
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      const items = within(list).getAllByRole('listitem')
      expect(items).toHaveLength(2)
      expect(items[0]).toHaveTextContent('Requests per minute per client')
      expect(items[0]).toHaveTextContent('240')
      expect(items[0]).toHaveTextContent('180')
      expect(items[0]).toHaveTextContent('Scraper traffic from one address range')
      // The arrow is for the eye; a screen reader hears "changed to".
      expect(within(items[0]!).getByText('changed to')).toHaveClass('sr-only')
      expect(within(items[0]!).getByText('\u2192')).toHaveAttribute('aria-hidden', 'true')
      expect(items[1]).toHaveTextContent('Revert')
      expect(items[1]).toHaveTextContent('Drafts per person')
      expect(screen.getByText('2 entries shown')).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Show older changes' }))
      expect(await screen.findByText('3 entries shown')).toBeInTheDocument()
      expect(history).toHaveBeenLastCalledWith(null, 'c1')
      expect(within(list).getAllByRole('listitem')[2]).toHaveTextContent('10 MB')
      expect(screen.queryByRole('button', { name: 'Show older changes' })).not.toBeInTheDocument()

      history.mockResolvedValue({ entries: [rateEntry], next_cursor: null })
      await userEvent.selectOptions(screen.getByLabelText(/^Setting/), 'rate_limit_per_minute')
      await waitFor(() => expect(history).toHaveBeenLastCalledWith('rate_limit_per_minute', null))
    })

    it('reverts an entry after a reason and the password, and says what it will set', async () => {
      mockLoad()
      const post = vi.spyOn(api, 'revertSettingChange').mockResolvedValue({ ...rate, value: 240, overridden: false })
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      await userEvent.click(within(list).getByRole('button', { name: /^Revert Requests per minute per client change/ }))
      const dialog = await screen.findByRole('dialog', { name: 'Revert this change?' })
      expect(within(dialog).getByLabelText(/Reason/)).toHaveFocus()
      expect(within(dialog).getByText('9 Oct 2026, 17:31 by Priya Nair')).toBeInTheDocument()
      expect(dialog).toHaveTextContent('This sets it back to 240 requests, replacing 180 requests now.')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Revert change' }))
      expect(within(dialog).getByText('Enter your password to confirm.')).toBeInTheDocument()
      expect(post).not.toHaveBeenCalled()
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'No longer needed')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Revert change' }))
      await waitFor(() => expect(post).toHaveBeenCalledWith('h-rate', { reason: 'No longer needed', password: PASSWORD }))
      await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Revert this change?' })).not.toBeInTheDocument())
    })

    it('does not check a revert to the default against the bounds', async () => {
      const odd = { ...rate, default: 300 }
      mockLoad({ environment: 'development', settings: [odd] })
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      await userEvent.click(within(list).getByRole('button', { name: /^Revert Requests per minute per client change/ }))
      const dialog = await screen.findByRole('dialog', { name: 'Revert this change?' })
      expect(within(dialog).queryByText('This change cannot be reverted')).not.toBeInTheDocument()
      expect(dialog).toHaveTextContent('This sets it back to 300 requests')
    })

    it('lets a revert entry be reverted too', async () => {
      mockLoad()
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      await userEvent.click(within(list).getByRole('button', { name: /^Revert Drafts per person change/ }))
      const dialog = await screen.findByRole('dialog', { name: 'Revert this change?' })
      expect(dialog).toHaveTextContent('Reverted: the limit was blocking a branch office')
      expect(dialog).toHaveTextContent('This sets it back to 10 drafts, replacing 20 drafts now.')
    })

    it('refuses a revert that today\'s ceiling forbids, and shows the server refusal if it comes later', async () => {
      const lowered = { ...drafts, maximum: 8, value: 8, default: 8 }
      mockLoad({ environment: 'development', settings: [lowered, rate] })
      const post = vi.spyOn(api, 'revertSettingChange').mockRejectedValue(
        new AppError(422, {
          code: 'validation_failed',
          message: 'Drafts per person cannot go above 8 (the environment ceiling).',
          details: { key: 'max_drafts_per_user', reason: 'above_maximum' },
        }),
      )
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      await userEvent.click(within(list).getByRole('button', { name: /^Revert Drafts per person change/ }))
      const dialog = await screen.findByRole('dialog', { name: 'Revert this change?' })
      expect(within(dialog).getByText('This change cannot be reverted')).toBeInTheDocument()
      expect(dialog).toHaveTextContent('Drafts per person cannot go above 8 (the environment ceiling).')
      expect(dialog).toHaveTextContent('Checked against today\'s bounds before anything is changed.')
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'Undo it')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), PASSWORD)
      await userEvent.click(within(dialog).getByRole('button', { name: 'Revert change' }))
      await waitFor(() => expect(post).toHaveBeenCalled())
      expect(within(dialog).getByText('This change cannot be reverted')).toBeInTheDocument()
    })

    it('puts a wrong password on a revert under the password field', async () => {
      mockLoad()
      vi.spyOn(api, 'revertSettingChange').mockRejectedValue(
        new AppError(403, { code: 'step_up_failed', message: 'Your password is incorrect. The change was not made.' }),
      )
      renderPage()
      const list = await screen.findByRole('list', { name: 'Changes and reverts' })
      await userEvent.click(within(list).getByRole('button', { name: /^Revert Requests per minute per client change/ }))
      const dialog = await screen.findByRole('dialog', { name: 'Revert this change?' })
      await userEvent.type(within(dialog).getByLabelText(/Reason/), 'No longer needed')
      await userEvent.type(within(dialog).getByLabelText(/Your password/), 'wrong')
      await userEvent.click(within(dialog).getByRole('button', { name: 'Revert change' }))
      expect(await within(dialog).findByText('Your password is incorrect. The change was not made.')).toBeInTheDocument()
      expect(within(dialog).queryByText('This change cannot be reverted')).not.toBeInTheDocument()
    })
  })
})
