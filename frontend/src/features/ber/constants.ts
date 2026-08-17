import type { BerLineStyle } from './types'

export const previewChart = { width: 340, height: 190, left: 42, right: 12, top: 14, bottom: 30 }
export const reportChart = { width: 960, height: 520, left: 82, right: 28, top: 24, bottom: 62 }
export const referenceStorageKey = 'signallab.ber-references.v1'

export const lineStyles: Array<{ value: BerLineStyle; label: string; dash: string }> = [
  { value: 'solid', label: 'Solid', dash: '' },
  { value: 'dash', label: 'Dashed', dash: '7 4' },
  { value: 'dot', label: 'Dotted', dash: '2 4' },
  { value: 'dashdot', label: 'Dash-dot', dash: '7 4 2 4' },
]
