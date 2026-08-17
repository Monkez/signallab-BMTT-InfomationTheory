export type SinkPoint = {
  snr_db: number
  bit_errors: number
  total_bits: number
  frames: number
  ber: number | null
}
export type BerLineStyle = 'solid' | 'dash' | 'dot' | 'dashdot'

export type BerReference = {
  id: string
  name: string
  color: string
  style: BerLineStyle
  points: SinkPoint[]
  createdAt: string
}

export type BerCurve = {
  id: string
  name: string
  color: string
  style: BerLineStyle
  valid: SinkPoint[]
  plotted: SinkPoint[]
  firstZero: number
}
