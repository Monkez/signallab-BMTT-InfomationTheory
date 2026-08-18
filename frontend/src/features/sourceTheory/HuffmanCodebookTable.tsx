import { useMemo } from 'react'
import type { PortPreview } from '../../types'
import { buildHuffmanCodebook, displaySymbol } from './huffmanCodebook'

export function HuffmanCodebookTable({ params, inputPreview }: { params: Record<string, string | number | boolean>; inputPreview?: PortPreview }) {
  const model = useMemo(() => {
    try { return { codebook: buildHuffmanCodebook(params) } }
    catch (error) { return { error: (error as Error).message } }
  }, [params.alphabet, params.probabilities])

  if (!model.codebook) return <div className="codebook-error" role="alert">{model.error}</div>
  const previewSymbols = inputPreview?.sample || []
  const codeLookup = new Map(model.codebook.rows.map(row => [row.symbol, row.code]))
  const previewCodes = previewSymbols.map(symbol => codeLookup.get(symbol) || '?')
  const payload = previewCodes.join('')
  const complete = Boolean(inputPreview && inputPreview.size === previewSymbols.length)
  const includeHeader = params.include_header === true
  const header = inputPreview ? inputPreview.size.toString(2).padStart(32, '0') : ''

  return <><div className="huffman-codebook">
    <table>
      <thead><tr><th>Symbol</th><th>P(x)</th><th>I(x)</th><th>Code</th><th>Length</th></tr></thead>
      <tbody>{model.codebook.rows.map(row => <tr key={row.symbol}>
        <td title={row.symbol}>{displaySymbol(row.symbol)}</td>
        <td>{row.probability.toFixed(4)}</td>
        <td>{row.information.toFixed(3)}</td>
        <td><code>{row.code}</code></td>
        <td>{row.length}</td>
      </tr>)}</tbody>
    </table>
    <footer><span>H(X) <b>{model.codebook.entropy.toFixed(4)}</b></span><span>Average length <b>{model.codebook.averageLength.toFixed(4)}</b></span><span>Efficiency <b>{model.codebook.efficiency.toFixed(2)}%</b></span></footer>
  </div>{inputPreview && <div className="huffman-sequence">
    <header><strong>Current encoded sequence</strong><span>{complete ? `${inputPreview.size} symbols` : `first ${previewSymbols.length} of ${inputPreview.size}`}</span></header>
    <div><span>Symbols</span><code>{previewSymbols.map(displaySymbol).join(' | ')}</code></div>
    <div><span>Codewords</span><code>{previewCodes.join(' | ')}</code></div>
    <div><span>Huffman payload</span><code>{payload}</code><small>{complete ? `${payload.length} bits` : 'partial preview'}</small></div>
    {includeHeader ? <><div><span>Optional header</span><code>{header}</code><small>32-bit symbol count = {inputPreview.size}</small></div><div><span>Serialized output</span><code>{header} | {payload}{complete ? '' : '…'}</code></div></> : <div><span>Output</span><code>{payload}{complete ? '' : '…'}</code><small>pure payload · no hidden header</small></div>}
  </div>}</>
}
