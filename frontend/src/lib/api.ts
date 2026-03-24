import type { GoogleAuthStatus, RunEventsResponse, RunState } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function listRuns(): Promise<RunState[]> {
  const response = await fetch(`${API_BASE}/runs`)
  const payload = await parseJson<{ runs: RunState[] }>(response)
  return payload.runs
}

export async function startRun(prompt: string, userLocalTime?: string): Promise<RunState> {
  const response = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, user_local_time: userLocalTime }),
  })
  const payload = await parseJson<{ run: RunState }>(response)
  return payload.run
}

export async function getRun(runId: string): Promise<RunState> {
  const response = await fetch(`${API_BASE}/runs/${runId}`)
  return parseJson<RunState>(response)
}

export async function getRunEvents(runId: string, since = 0): Promise<RunEventsResponse> {
  const response = await fetch(`${API_BASE}/runs/${runId}/events?since=${since}`)
  return parseJson<RunEventsResponse>(response)
}

export async function respondToRun(
  runId: string,
  responseText: string,
  userLocalTime?: string,
): Promise<RunState> {
  const response = await fetch(`${API_BASE}/runs/${runId}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ response_text: responseText, user_local_time: userLocalTime }),
  })
  const payload = await parseJson<{ run: RunState }>(response)
  return payload.run
}

export async function getGoogleAuthStatus(): Promise<GoogleAuthStatus> {
  const response = await fetch(`${API_BASE}/auth/google/status`)
  return parseJson<GoogleAuthStatus>(response)
}

export async function disconnectGoogleAuth(): Promise<GoogleAuthStatus> {
  const response = await fetch(`${API_BASE}/auth/google/disconnect`, {
    method: 'POST',
  })
  return parseJson<GoogleAuthStatus>(response)
}

export function getGoogleAuthStartUrl(): string {
  return `${API_BASE}/auth/google/start`
}
