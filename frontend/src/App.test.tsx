import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import App from './App'
import type { RunState } from './types'

const listRuns = vi.fn()
const startRun = vi.fn()
const getRun = vi.fn()
const getRunEvents = vi.fn()
const respondToRun = vi.fn()
const getGoogleAuthStatus = vi.fn()
const disconnectGoogleAuth = vi.fn()
const getGoogleAuthStartUrl = vi.fn()

vi.mock('./lib/api', () => ({
  listRuns: () => listRuns(),
  startRun: (prompt: string) => startRun(prompt),
  getRun: (runId: string) => getRun(runId),
  getRunEvents: (runId: string, since?: number) => getRunEvents(runId, since),
  respondToRun: (runId: string, responseText: string) => respondToRun(runId, responseText),
  getGoogleAuthStatus: () => getGoogleAuthStatus(),
  disconnectGoogleAuth: () => disconnectGoogleAuth(),
  getGoogleAuthStartUrl: () => getGoogleAuthStartUrl(),
}))

function buildRun(overrides: Partial<RunState> = {}): RunState {
  return {
    id: 'run-1',
    prompt: 'Book meeting with boss@example.com tomorrow at 2 PM',
    status: 'waiting_for_user',
    final_message: null,
    clarification_prompt: 'I found two possible meeting times: 2 PM or 4 PM. Which do you prefer?',
    clarification_options: ['2 PM', '4 PM'],
    artifacts: {},
    events: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  listRuns.mockResolvedValue([])
  getRun.mockResolvedValue(buildRun())
  getRunEvents.mockResolvedValue({ events: [], next_cursor: 0 })
  getGoogleAuthStatus.mockResolvedValue({
    connected: false,
    authMode: 'oauth',
    redirectUri: 'http://127.0.0.1:8000/auth/google/callback',
  })
  disconnectGoogleAuth.mockResolvedValue({
    connected: false,
    authMode: 'oauth',
    redirectUri: 'http://127.0.0.1:8000/auth/google/callback',
  })
  getGoogleAuthStartUrl.mockReturnValue('http://127.0.0.1:8000/auth/google/start')
})

test('submits a task and renders the clarification card for waiting runs', async () => {
  startRun.mockResolvedValue(buildRun())
  respondToRun.mockResolvedValue(buildRun({ status: 'completed', final_message: 'Meeting booked successfully.' }))

  render(<App />)

  await waitFor(() => expect(listRuns).toHaveBeenCalled())

  await userEvent.click(screen.getByRole('button', { name: /run agent/i }))

  await waitFor(() =>
    expect(startRun).toHaveBeenCalledWith(
      'Book meeting with boss@example.com for tomorrow at 2 PM and email them.',
    ),
  )

  expect(await screen.findByText(/Human review needed/i)).toBeInTheDocument()
  expect(screen.getByText(/2 PM or 4 PM/i)).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: '2 PM' }))

  await waitFor(() => expect(respondToRun).toHaveBeenCalledWith('run-1', '2 PM'))
})
