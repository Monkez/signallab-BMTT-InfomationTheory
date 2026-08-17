import { useState } from 'react'
import type { SinkPoint } from './SinkChart'

const format = (value: number | null) => value === null ? '—' : value.toExponential(4)

function csvValue(value: string | number) {
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function ResultsTable({ points }: { points: SinkPoint[] }) {
  const [notice, setNotice] = useState('')
  if (!points.length) return null
  const rows = points.map(point => [point.snr_db, point.frames, point.bit_errors, point.total_bits, point.ber === null ? '' : point.ber])
  const header = ['SNR (dB)', 'Frames', 'Bit errors', 'Total bits', 'BER']
  const tsv = [header, ...rows].map(row => row.map(String).join('\t')).join('\n')
  const csv = [header, ...rows].map(row => row.map(csvValue).join(',')).join('\n')

  const download = (content: BlobPart, type: string, filename: string) => {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([content], { type }))
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  }
  const action = async (kind: 'copy' | 'csv' | 'png') => {
    try {
      if (kind === 'copy') {
        await navigator.clipboard.writeText(tsv)
        setNotice('Copied')
      } else if (kind === 'csv') {
        download(csv, 'text/csv;charset=utf-8', 'signallab-results.csv')
        setNotice('CSV saved')
      } else {
        const canvas = document.createElement('canvas')
        const width = 760
        const rowHeight = 30
        const height = rowHeight * (rows.length + 1) + 20
        canvas.width = width * 2
        canvas.height = height * 2
        const context = canvas.getContext('2d')
        if (!context) throw new Error('Canvas is unavailable')
        context.scale(2, 2)
        context.fillStyle = '#ffffff'
        context.fillRect(0, 0, width, height)
        context.font = '600 13px Segoe UI'
        context.fillStyle = '#263140'
        header.forEach((label, index) => context.fillText(label, 18 + index * 145, 25))
        context.font = '13px Consolas'
        rows.forEach((row, rowIndex) => {
          const y = 25 + (rowIndex + 1) * rowHeight
          context.fillStyle = rowIndex % 2 ? '#f7f9fc' : '#ffffff'
          context.fillRect(0, y - 21, width, rowHeight)
          context.fillStyle = '#425064'
          row.forEach((value, index) => context.fillText(index === 4 ? format(value === '' ? null : Number(value)) : String(value), 18 + index * 145, y))
        })
        const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Could not encode table image')), 'image/png'))
        download(blob, 'image/png', 'signallab-results-table.png')
        setNotice('PNG saved')
      }
    } catch (error) { setNotice((error as Error).message) }
    window.setTimeout(() => setNotice(''), 1800)
  }

  return <div className="results-table-wrap">
    <div className="results-table-toolbar"><span>Results by SNR</span><div className="chart-actions"><button onClick={() => action('copy')} aria-label="Copy results as TSV">Copy</button><button onClick={() => action('csv')} aria-label="Export results as CSV">CSV</button><button onClick={() => action('png')} aria-label="Export results as PNG">PNG</button></div></div>
    <div className="results-table-scroll"><table><thead><tr>{header.map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>{points.map(point => <tr key={`${point.snr_db}-${point.frames}`}><td>{point.snr_db.toFixed(2)}</td><td>{point.frames}</td><td>{point.bit_errors}</td><td>{point.total_bits}</td><td>{format(point.ber)}</td></tr>)}</tbody></table></div>
    {notice && <div className="chart-notice">{notice}</div>}
  </div>
}
