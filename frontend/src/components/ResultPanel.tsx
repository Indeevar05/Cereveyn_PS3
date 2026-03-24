import { CheckCircle2, ExternalLink, Mail, Sparkles } from 'lucide-react'

import type { RunState, RunStatus } from '../types'

export function ResultPanel({
  run,
}: {
  run: RunState | null
}) {
  if (!run) {
    return (
      <section className="flex h-full min-h-0 flex-1 flex-col justify-center px-4 py-6 text-center text-[13px] text-[var(--text-subtle)]">
        Select a run or send a request to see outcome and artifacts.
      </section>
    )
  }

  const meetLink = typeof run.artifacts.meetLink === 'string' ? run.artifacts.meetLink : null
  const messageId = typeof run.artifacts.messageId === 'string' ? run.artifacts.messageId : null

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-4 py-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-[var(--text)]">Response</p>
          <p className="text-[12px] text-[var(--text-muted)]">Summary and outputs</p>
        </div>
      </div>

      <div className="mb-3 rounded-md border border-[var(--border)] bg-[var(--app-bg)] p-3">
        <div className="flex items-center gap-2 text-[var(--accent)]">
          <Sparkles className="h-3.5 w-3.5" />
          <p className="text-[12px] font-semibold uppercase tracking-wide">Summary</p>
        </div>
        <p className="mt-2 text-[13px] leading-relaxed text-[var(--summary-text)]">
          {run.final_message ?? 'Agent is still processing…'}
        </p>
      </div>

      <div className="rounded-md border border-[var(--border)] bg-[var(--app-bg)] p-3">
        <div className="mb-2 flex items-center gap-2 text-emerald-500">
          <CheckCircle2 className="h-3.5 w-3.5" />
          <p className="text-[12px] font-semibold">Artifacts</p>
        </div>
        <div className="space-y-2 text-[12px]">
          <div className="rounded border border-[var(--border)] bg-[var(--code-bg)] p-2.5">
            <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--text-subtle)]">Google Meet Link</p>
            {meetLink ? (
              <a
                href={meetLink}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1.5 text-[var(--link-accent)] hover:text-[var(--link-accent-hover)]"
              >
                Open link
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : (
              <p className="mt-1 text-[var(--text-subtle)]">—</p>
            )}
          </div>
          <div className="rounded border border-[var(--border)] bg-[var(--code-bg)] p-2.5">
            <p className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-[var(--text-subtle)]">
              <Mail className="h-3 w-3" />
              SES message id
            </p>
            <p className="mt-1 break-all font-mono text-[11px] text-[var(--text-muted)]">{messageId ?? '—'}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
