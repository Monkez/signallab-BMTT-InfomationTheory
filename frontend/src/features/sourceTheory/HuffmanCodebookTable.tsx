import { useMemo } from 'react'
import { buildHuffmanCodebook, displaySymbol } from './huffmanCodebook'

export function HuffmanCodebookTable({ params }: { params: Record<string, string | number | boolean> }) {
  const model = useMemo(() => {
    try { return { codebook: buildHuffmanCodebook(params) } }
    catch (error) { return { error: (error as Error).message } }
  }, [params.alphabet, params.probabilities])

  if (!model.codebook) return <div className="codebook-error" role="alert">{model.error}</div>
  return <div className="huffman-codebook">
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
  </div>
}
