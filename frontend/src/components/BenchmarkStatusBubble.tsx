import { Check, CircleAlert, LoaderCircle } from 'lucide-react'
import type { Job } from '../types'

type Props = {
  job: Job
  onOpenResults: () => void
}

export function BenchmarkStatusBubble({ job, onOpenResults }: Props) {
  const percent = Math.max(0, Math.min(100, Math.round((job.progress || 0) * 100)))
  const point = typeof job.snr_index === 'number' ? job.snr_index + 1 : 0
  const pointCount = job.snr_count || job.result?.snr_points.length || 1
  const state = job.status === 'completed' ? 'completed' : job.status === 'failed' ? 'failed' : job.status === 'cancelled' ? 'cancelled' : 'active'
  const label = state === 'completed' ? 'Completed' : state === 'failed' ? 'Failed' : state === 'cancelled' ? 'Cancelled' : job.status === 'queued' ? 'Queued' : 'Running'

  return <button type="button" className={`benchmark-status-bubble ${state}`} onClick={onOpenResults} aria-label={`Benchmark ${label.toLowerCase()}, ${percent} percent. Open results.`}>
    <span className="benchmark-bubble-head">
      {state === 'active' ? <LoaderCircle size={13} /> : state === 'completed' ? <Check size={13} /> : <CircleAlert size={13} />}
      <strong>{percent}%</strong><em>{label}</em>
    </span>
    <span className="benchmark-bubble-track"><i style={{ width: `${percent}%` }} /></span>
    <span className="benchmark-bubble-meta">
      <b>Step {point || '—'}/{pointCount}</b>
      <span>{typeof job.snr_db === 'number' ? `${job.snr_db.toFixed(2)} dB` : `${job.completed_trials || 0}/${job.trials} frames`}</span>
    </span>
  </button>
}
