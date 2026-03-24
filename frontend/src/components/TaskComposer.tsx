interface TaskComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  isBusy: boolean
}

export function TaskComposer({ value, onChange, onSubmit, isBusy }: TaskComposerProps) {
  return (
    <section className="flex shrink-0 flex-col border-b border-[var(--border)] bg-[var(--panel-bg)] px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[13px] font-semibold tracking-tight text-[var(--text)]">Request</p>
          <p className="text-[12px] text-[var(--text-muted)]">Natural language task - tools run automatically.</p>
        </div>
        <button
          type="button"
          onClick={onSubmit}
          disabled={isBusy || !value.trim()}
          className="shrink-0 rounded-md bg-[var(--accent)] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:bg-[var(--btn-disabled-bg)] disabled:text-[var(--btn-disabled-text)]"
        >
          {isBusy ? 'Running…' : 'Send'}
        </button>
      </div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Book meeting with you@example.com tomorrow at 2 PM and email them."
        rows={3}
        className="min-h-[72px] w-full resize-none rounded-md border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2.5 text-[13px] leading-relaxed text-[var(--text)] outline-none placeholder:text-[var(--text-subtle)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
      />
    </section>
  )
}
