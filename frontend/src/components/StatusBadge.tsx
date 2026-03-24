import { useEffect, useState } from 'react'
import { Check, Clock, Users } from 'lucide-react'
import clsx from 'clsx'

import type { RunState, RunStatus } from '../types'

const badgeStyles: Record<string, string> = {
  running:
    'bg-[var(--accent)]/10 text-[var(--accent)] ring-1 ring-inset ring-[var(--accent)]/30 animate-pulse',
  waiting_for_user:
    'bg-amber-500/10 text-amber-600 ring-1 ring-inset ring-amber-500/20 dark:text-amber-400',
  completed:
    'bg-emerald-500/10 text-emerald-600 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-400',
  failed:
    'bg-red-500/10 text-red-600 ring-1 ring-inset ring-red-500/20 dark:text-red-400',
  past: 'bg-zinc-500/10 text-zinc-500 ring-1 ring-inset ring-zinc-500/20 dark:text-zinc-400',
  scheduled: 'bg-blue-500/10 text-blue-600 ring-1 ring-inset ring-blue-500/20 dark:text-blue-400',
  waiting_in_room: 'bg-amber-500/10 text-amber-600 ring-1 ring-inset ring-amber-500/20 dark:text-amber-400 animate-pulse',
}

const labels: Record<string, string> = {
  running: 'Running',
  waiting_for_user: 'Waiting',
  completed: 'Done',
  failed: 'Failed',
  past: 'Meeting Over',
  scheduled: 'Scheduled',
  waiting_in_room: 'Waiting in Room',
}

export function StatusBadge({
  run,
  status,
  label,
}: {
  run?: RunState
  status?: RunStatus | string
  label?: string
}) {
  const [participants, setParticipants] = useState<number | null>(null)
  const [now, setNow] = useState(new Date())

  const startTimeStr = run?.artifacts.startTime as string | undefined
  const endTimeStr = run?.artifacts.endTime as string | undefined
  const meetLink = run?.artifacts.meetLink as string | undefined

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 10000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!run || !startTimeStr || !endTimeStr || !meetLink) return

    const start = new Date(startTimeStr)
    const end = new Date(endTimeStr)

    if (now >= start && now <= end) {
      const fetchStatus = async () => {
        try {
          const res = await fetch(`http://127.0.0.1:8000/runs/${run.id}/meeting-status`)
          const data = await res.json()
          setParticipants(data.participants)
        } catch (err) {
          console.error('Failed to fetch meeting status', err)
        }
      }
      fetchStatus()
      const statusTimer = setInterval(fetchStatus, 30000)
      return () => clearInterval(statusTimer)
    }
  }, [run?.id, startTimeStr, endTimeStr, meetLink, now, run?.status])

  let effectiveStatus: string = status || run?.status || 'running'
  let effectiveLabel: string = label || labels[effectiveStatus] || effectiveStatus

  if (run && startTimeStr && endTimeStr) {
    const start = new Date(startTimeStr)
    const end = new Date(endTimeStr)

    if (now < start) {
      effectiveStatus = 'scheduled'
      effectiveLabel = 'Scheduled'
    } else if (now > end) {
      effectiveStatus = 'past'
      effectiveLabel = 'Meeting Over'
    } else {
      // In progress
      if (participants !== null && participants > 0) {
        effectiveStatus = 'running'
        effectiveLabel = 'Running'
      } else {
        effectiveStatus = 'waiting_in_room'
        effectiveLabel = 'Waiting in Room'
      }
    }
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider',
        badgeStyles[effectiveStatus] || badgeStyles.running,
      )}
    >
      {effectiveStatus === 'scheduled' && <Clock className="h-2.5 w-2.5" />}
      {effectiveStatus === 'running' && <Users className="h-2.5 w-2.5" />}
      {(run?.status === 'completed' &&
        effectiveStatus !== 'scheduled' &&
        effectiveStatus !== 'waiting_in_room') && <Check className="h-2.5 w-2.5" />}
      {effectiveLabel}
    </span>
  )
}
