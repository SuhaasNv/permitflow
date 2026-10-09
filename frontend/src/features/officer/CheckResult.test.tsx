import { render, screen } from '@testing-library/react'

import type { OfficerVerification } from '@/api/officer'
import { CheckResult } from './CheckResult'

const unavailable: OfficerVerification = {
  status: 'unavailable',
  summary: null,
  confidence: null,
  issues: [],
  missing_information: [],
  error_reason: 'ai_paused',
  provider: 'mock',
  model: null,
  requested_at: '2026-10-10T08:00:00Z',
  finished_at: '2026-10-10T08:00:01Z',
}

describe('CheckResult', () => {
  it('explains ai_paused instead of showing the raw code', () => {
    render(<CheckResult verification={unavailable} />)
    expect(screen.getByText('Automatic checks are paused by the administrator; re-run once they resume.')).toBeInTheDocument()
    expect(screen.queryByText('ai_paused')).not.toBeInTheDocument()
  })
})
