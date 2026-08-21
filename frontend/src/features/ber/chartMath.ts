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

function niceStep(span: number, targetIntervals: number) {
  const rawStep = span / Math.max(targetIntervals, 1)
  const magnitude = 10 ** Math.floor(Math.log10(rawStep))
  const normalized = rawStep / magnitude
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10
  return factor * magnitude
}

export function linearTicks(rawMin: number, rawMax: number, targetIntervals = 6, minorDivisions = 4) {
  const sameValue = rawMin === rawMax
  const paddedMin = sameValue ? rawMin - 1 : rawMin
  const paddedMax = sameValue ? rawMax + 1 : rawMax
  const step = niceStep(paddedMax - paddedMin, targetIntervals)
  const min = Math.floor(paddedMin / step) * step
  const max = Math.ceil(paddedMax / step) * step
  const precision = Math.max(0, -Math.floor(Math.log10(step)) + 2)
  const round = (value: number) => Number(value.toFixed(precision))
  const major = Array.from({ length: Math.round((max - min) / step) + 1 }, (_, index) => round(min + index * step))
  const minorStep = step / minorDivisions
  const minor = Array.from({ length: Math.round((max - min) / minorStep) + 1 }, (_, index) => round(min + index * minorStep))
    .filter(value => !major.some(majorValue => Math.abs(majorValue - value) < minorStep / 100))
  return { min, max, step, major, minor }
}

export function curveDomain(curves: BerCurve[], targetXIntervals = 6) {
  const allValid = curves.flatMap(curve => curve.valid)
  const xTicks = linearTicks(Math.min(...allValid.map(point => point.snr_db)), Math.max(...allValid.map(point => point.snr_db)), targetXIntervals)
  const minX = xTicks.min
  const maxX = xTicks.max
  const xRange = maxX - minX
  const values = curves.flatMap(curve => curve.plotted.map(point => Math.max(Number(point.ber ?? 0), 1e-8)))
  const maxLog = 0
  const minLog = Math.min(-8, Math.floor(Math.min(...values.map(value => Math.log10(value)))))
  return { allValid, minX, maxX, xRange, xTicks, maxLog, minLog, yRange: Math.max(maxLog - minLog, 1) }
}
