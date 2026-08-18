import { referenceStorageKey } from './constants'
import type { BerReference } from './types'

export const referenceChangeEvent = 'signallab-ber-reference-change'

/**
 * A reference id is intentionally unique per import, so it cannot be used to
 * decide whether two curves are the same. Compare the curve identity instead:
 * the user-facing name. Names are the stable identity shown in the legend, so
 * loading a newer file with the same name replaces the older curve instead of
 * creating two indistinguishable legend entries.
 */
export function dedupeReferences(references: BerReference[]): BerReference[] {
  const unique = new Map<string, BerReference>()
  for (const reference of references) {
    const key = reference.name.trim().toLocaleLowerCase()
    unique.set(key, reference)
  }
  return [...unique.values()]
}

export function readReferences(): BerReference[] {
  try {
    const raw = window.localStorage.getItem(referenceStorageKey)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return dedupeReferences(parsed.filter(item => item && typeof item.id === 'string' && typeof item.name === 'string' && Array.isArray(item.points)) as BerReference[])
  } catch { return [] }
}
export function persistReferences(references: BerReference[]) {
  try { window.localStorage.setItem(referenceStorageKey, JSON.stringify(dedupeReferences(references))) } catch { /* storage can be disabled */ }
  window.dispatchEvent(new Event(referenceChangeEvent))
}
