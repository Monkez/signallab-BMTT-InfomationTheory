import { lineStyles } from './constants'
import type { BerCurve, BerLineStyle, SinkPoint } from './types'

export function styleDash(style: BerLineStyle) {
  return lineStyles.find(option => option.value === style)?.dash || ''
}
export function plottedPoints(points: SinkPoint[]) {
  const valid = points.filter(point => Number.isFinite(point.snr_db) && point.total_bits > 0)
  const firstZero = valid.findIndex(point => point.ber === 0)
  return { valid, firstZero, plotted: firstZero >= 0 ? valid.slice(0, firstZero + 1) : valid }
}

export function curveDomain(curves: BerCurve[]) {
  const allValid = curves.flatMap(curve => curve.valid)
  const minX = Math.min(...allValid.map(point => point.snr_db))
  const maxX = Math.max(...allValid.map(point => point.snr_db))
  const xRange = Math.max(maxX - minX, 1)
  const values = curves.flatMap(curve => curve.plotted.map(point => Math.max(Number(point.ber ?? 0), 1e-8)))
  const maxLog = Math.ceil(Math.max(...values.map(value => Math.log10(value)), -1))
  const minLog = Math.min(-8, Math.floor(Math.min(...values.map(value => Math.log10(value)))))
  return { allValid, minX, maxX, xRange, maxLog, minLog, yRange: Math.max(maxLog - minLog, 1) }
}
