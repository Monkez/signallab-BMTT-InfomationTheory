import type { BerCurve } from './types'

type BerLegendProps = {
  curves: BerCurve[]
  variant?: 'preview' | 'report'
  onHide?: (id: string) => void
  onDelete?: (id: string) => void
}

export function BerLegend({ curves, variant = 'preview', onHide, onDelete }: BerLegendProps) {
  const report = variant === 'report'
  return <div className={report ? 'ber-report-chart-legend' : 'ber-legend'} aria-label="BER curve legend">
    {curves.map((curve, index) => report
      ? <span key={curve.id}><i style={{ borderTopColor: curve.color, borderTopStyle: curve.style === 'dot' ? 'dotted' : curve.style === 'solid' ? 'solid' : 'dashed' }} />{curve.name}</span>
      : <div className="ber-legend-item" key={curve.id}><span className="ber-legend-swatch" style={{ borderTopColor: curve.color, borderTopStyle: curve.style === 'dot' ? 'dotted' : curve.style === 'solid' ? 'solid' : 'dashed' }} /><span className="ber-legend-name">{curve.name}</span>{index > 0 && onHide && <button className="ber-legend-action" onClick={() => onHide(curve.id)} title="Hide reference">Hide</button>}{index > 0 && onDelete && <button className="ber-legend-delete" onClick={() => onDelete(curve.id)} title="Delete saved reference">×</button>}</div>
    )}
  </div>
}
