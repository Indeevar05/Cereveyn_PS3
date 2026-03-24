import { useState } from 'react'

interface HumanReviewCardProps {
  prompt: string
  options: string[]
  onRespond: (response: string) => Promise<void>
  isSubmitting: boolean
}

export function HumanReviewCard({
  prompt,
  options,
  onRespond,
  isSubmitting,
}: HumanReviewCardProps) {
  const [value, setValue] = useState('')

  async function submit(response: string) {
    if (!response.trim()) {
      return
    }
    setValue('')
    await onRespond(response)
  }

  return (
    <section className="shrink-0 border-b border-[var(--accent)]/30 bg-[var(--accent-muted)] px-4 py-3">
      <p className="text-[12px] font-semibold uppercase tracking-wide text-[var(--accent-hover)]">
        Input required
      </p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--text)]">{prompt}</p>

      {options.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {options.map((option) => (
            <button
              key={option}
              type="button"
              disabled={isSubmitting}
              onClick={() => submit(option)}
              className="rounded-md border border-[var(--border)] bg-[var(--elevated-bg)] px-3 py-1.5 text-[12px] text-[var(--text)] transition hover:border-[var(--accent)]/50 hover:bg-[var(--panel-bg)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {option}
            </button>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex gap-2">
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Your answer…"
          className="min-w-0 flex-1 rounded-md border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-[13px] text-[var(--text)] outline-none placeholder:text-[var(--text-subtle)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
        />
        <button
          type="button"
          disabled={isSubmitting || !value.trim()}
          onClick={() => submit(value)}
          className="shrink-0 rounded-md bg-[var(--accent)] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:bg-[var(--btn-disabled-bg)] disabled:text-[var(--btn-disabled-text)]"
        >
          {isSubmitting ? '…' : 'Send'}
        </button>
      </div>
    </section>
  )
}
