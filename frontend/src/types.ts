export type RunStatus = 'running' | 'waiting_for_user' | 'completed' | 'failed' | 'past'

export type RunEventType =
  | 'run_started'
  | 'model_thinking'
  | 'tool_requested'
  | 'tool_succeeded'
  | 'tool_failed'
  | 'waiting_for_user'
  | 'completed'
  | 'failed'

export interface RunEvent {
  id: number
  type: RunEventType
  title: string
  detail: string
  data: Record<string, unknown>
  timestamp: string
}

export interface RunState {
  id: string
  prompt: string
  status: RunStatus
  final_message: string | null
  clarification_prompt: string | null
  clarification_options: string[]
  artifacts: Record<string, unknown>
  events: RunEvent[]
  created_at: string
  updated_at: string
}

export interface RunEventsResponse {
  events: RunEvent[]
  next_cursor: number
}

export interface GoogleAuthStatus {
  connected: boolean
  authMode: string
  redirectUri: string
}
