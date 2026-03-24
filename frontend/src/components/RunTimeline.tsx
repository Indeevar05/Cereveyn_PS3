import { Bot, CalendarRange, CheckCircle2, Clock3, MailWarning, Sparkles, TriangleAlert } from 'lucide-react'

import type { RunEvent } from '../types'

function getIcon(type: RunEvent['type']) {
  switch (type) {
    case 'tool_requested':
      return <CalendarRange className="h-3.5 w-3.5" />
    case 'tool_succeeded':
      return <CheckCircle2 className="h-3.5 w-3.5" />
    case 'tool_failed':
    case 'failed':
      return <MailWarning className="h-3.5 w-3.5" />
    case 'waiting_for_user':
      return <TriangleAlert className="h-3.5 w-3.5" />
    case 'model_thinking':
      return <Sparkles className="h-3.5 w-3.5" />
    default:
      return <Bot className="h-3.5 w-3.5" />
  }
}

export function RunTimeline({ events }: { events: RunEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="px-4 py-12 text-center text-[13px] text-[var(--text-subtle)]">
        No events yet. Send a request to see tool calls and model steps.
      </div>
    )
  }

  return (
    <div className="space-y-2 px-3 py-3">
      {events.map((event) => (
        <article
          key={event.id}
          className="rounded-md border border-[var(--border)] bg-[var(--app-bg)] px-3 py-2.5"
        >
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 shrink-0 rounded bg-[var(--elevated-bg)] p-1.5 text-[var(--accent)]">
              {getIcon(event.type)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[13px] font-medium text-[var(--text)]">{event.title}</p>
                  <p className="mt-0.5 text-[12px] leading-snug text-[var(--text-muted)]">{event.detail}</p>
                </div>
                <span className="inline-flex shrink-0 items-center gap-1 text-[11px] tabular-nums text-[var(--text-subtle)]">
                  <Clock3 className="h-3 w-3" />
                  {new Date(event.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              {Object.keys(event.data).length > 0 ? (
                <pre className="mt-2 max-h-32 overflow-auto rounded border border-[var(--border)] bg-[var(--code-bg)] p-2 text-[11px] leading-relaxed text-[var(--text-muted)]">
                  {JSON.stringify(event.data, null, 2)}
                </pre>
              ) : null}
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}
