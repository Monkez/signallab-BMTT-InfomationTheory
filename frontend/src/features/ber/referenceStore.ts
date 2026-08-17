import { referenceStorageKey } from './constants'
import type { BerReference } from './types'

export const referenceChangeEvent = 'signallab-ber-reference-change'

export function readReferences(): BerReference[] {
  try {
    const raw = window.localStorage.getItem(referenceStorageKey)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(item => item && typeof item.id === 'string' && typeof item.name === 'string' && Array.isArray(item.points))
  } catch { return [] }
}
export function persistReferences(references: BerReference[]) {
  try { window.localStorage.setItem(referenceStorageKey, JSON.stringify(references)) } catch { /* storage can be disabled */ }
  window.dispatchEvent(new Event(referenceChangeEvent))
}
