import { API_BASE_URL } from '../lib/config'

const STACK_ITEMS = [
  'React',
  'TypeScript',
  'Vite',
  'Tailwind',
  'Python',
  'FastAPI',
  'Uvicorn',
  'SQLite',
  'Gemini',
  'Google GenAI',
  'Calendar / Meet',
  'AWS SES',
] as const

export function WorkspaceMetaBar() {
  return (
    <div className="flex flex-col gap-2 border-t border-[var(--border)] bg-[var(--meta-bar-bg)] px-4 py-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-4 sm:gap-y-1">
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-subtle)]">
          Stack
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          {STACK_ITEMS.map((item) => (
            <span
              key={item}
              className="rounded border border-[var(--border)] bg-[var(--chip-bg)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]"
            >
              {item}
            </span>
          ))}
        </div>
      </div>
      <div className="hidden h-4 w-px shrink-0 bg-[var(--border)] sm:block" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2 gap-y-0.5 sm:justify-end">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-subtle)]">
          API
        </span>
        <code className="max-w-full truncate rounded border border-[var(--border)] bg-[var(--code-bg)] px-2 py-0.5 font-mono text-[11px] text-[var(--accent)]">
          {API_BASE_URL}
        </code>
      </div>
    </div>
  )
}
