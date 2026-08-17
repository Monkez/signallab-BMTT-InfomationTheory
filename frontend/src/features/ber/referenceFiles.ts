import { lineStyles } from './constants'
import type { BerReference } from './types'

function safeFileName(name: string) {
  return `${name.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '') || 'ber-reference'}.ber.json`
}

function payload(reference: BerReference) {
  return { format: 'signallab-ber-reference', version: 1, reference }
}

function downloadReferenceFile(reference: BerReference) {
  const blob = new Blob([JSON.stringify(payload(reference), null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = safeFileName(reference.name)
  link.click()
  URL.revokeObjectURL(link.href)
}

export async function saveReferenceFile(reference: BerReference) {
  const pickerWindow = window as Window & { showSaveFilePicker?: (options: unknown) => Promise<{ createWritable: () => Promise<{ write: (data: Blob) => Promise<void>; close: () => Promise<void> }> }> }
  if (!pickerWindow.showSaveFilePicker) { downloadReferenceFile(reference); return }
  const handle = await pickerWindow.showSaveFilePicker({ suggestedName: safeFileName(reference.name), types: [{ description: 'SignalLab BER reference', accept: { 'application/json': ['.ber.json', '.json'] } }] })
  const writable = await handle.createWritable()
  await writable.write(new Blob([JSON.stringify(payload(reference), null, 2)], { type: 'application/json' }))
  await writable.close()
}

export async function parseReferenceFile(file: File): Promise<BerReference[]> {
  const parsed = JSON.parse(await file.text())
  const candidates = Array.isArray(parsed) ? parsed : [parsed.reference || parsed]
  return candidates.filter(item => item && typeof item.name === 'string' && Array.isArray(item.points) && item.points.length > 0).map(item => ({
    id: `ber-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: item.name,
    color: typeof item.color === 'string' ? item.color : '#d26782',
    style: lineStyles.some(option => option.value === item.style) ? item.style : 'dash',
    points: item.points,
    createdAt: typeof item.createdAt === 'string' ? item.createdAt : new Date().toISOString(),
  } as BerReference))
}
