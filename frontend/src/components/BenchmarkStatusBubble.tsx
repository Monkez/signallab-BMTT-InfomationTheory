import { LoaderCircle } from 'lucide-react'
import type { Job } from '../types'

type Props = {
  job: Job
  onOpenResults: () => void
}

export function BenchmarkStatusBubble({ job, onOpenResults }: Props) {
  const percent = Math.max(0, Math.min(100, Math.round((job.progress || 0) * 100)))
  const point = typeof job.snr_index === 'number' ? job.snr_index + 1 : 0
  const pointCount = job.snr_count || job.result?.snr_points.length || 1
  const detail = typeof job.snr_db === 'number'
    ? `${point || '—'}/${pointCount} · ${job.snr_db.toFixed(1)} dB`
    : `${job.completed_trials || 0}/${job.trials}`

  return <button type="button" className="benchmark-status-bubble" onClick={onOpenResults} aria-label={`Benchmark running, ${percent} percent, step ${detail}. Open results.`}>
    <span className="benchmark-bubble-row"><LoaderCircle size={12} /><strong>{percent}%</strong><span>{detail}</span></span>
    <span className="benchmark-bubble-track"><i style={{ width: `${percent}%` }} /></span>
  </button>
}
