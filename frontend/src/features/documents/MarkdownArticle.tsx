import type { ReactNode } from 'react'

const inline = (value: string): ReactNode[] => value.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
  if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>
  if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>
  return part
})

const isSpecial = (line: string) => !line.trim() || /^#{1,4}\s/.test(line) || /^```/.test(line) || /^[-*]\s/.test(line) || /^\d+\.\s/.test(line)

export function MarkdownArticle({ content }: { content: string }) {
  const lines = content.replace(/\r/g, '').split('\n')
  const blocks: ReactNode[] = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    if (!line.trim()) { index += 1; continue }
    const heading = /^(#{1,4})\s+(.+)$/.exec(line)
    if (heading) {
      const level = heading[1].length
      const text = heading[2]
      const id = text.toLocaleLowerCase('vi').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '')
      const Tag = `h${level}` as keyof JSX.IntrinsicElements
      blocks.push(<Tag id={id} key={`h-${index}`}>{inline(text)}</Tag>)
      index += 1
      continue
    }
    if (line.startsWith('```')) {
      const language = line.slice(3).trim()
      const code: string[] = []
      index += 1
      while (index < lines.length && !lines[index].startsWith('```')) { code.push(lines[index]); index += 1 }
      index += 1
      blocks.push(<div className="docs-code" key={`code-${index}`}><span>{language || 'text'}</span><pre><code>{code.join('\n')}</code></pre></div>)
      continue
    }
    if (line.includes('|') && index + 1 < lines.length && /^\s*\|?\s*:?-+/.test(lines[index + 1])) {
      const parseRow = (row: string) => row.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim())
      const headers = parseRow(line)
      const rows: string[][] = []
      index += 2
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) { rows.push(parseRow(lines[index])); index += 1 }
      blocks.push(<div className="docs-table-wrap" key={`table-${index}`}><table><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{inline(cell)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{inline(cell)}</td>)}</tr>)}</tbody></table></div>)
      continue
    }
    if (/^[-*]\s/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^[-*]\s/.test(lines[index])) { items.push(lines[index].replace(/^[-*]\s+/, '')); index += 1 }
      blocks.push(<ul key={`ul-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ul>)
      continue
    }
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = []
      while (index < lines.length && /^\d+\.\s/.test(lines[index])) { items.push(lines[index].replace(/^\d+\.\s+/, '')); index += 1 }
      blocks.push(<ol key={`ol-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ol>)
      continue
    }
    const paragraph = [line]
    index += 1
    while (index < lines.length && !isSpecial(lines[index]) && !(lines[index].includes('|') && index + 1 < lines.length && /^\s*\|?\s*:?-+/.test(lines[index + 1]))) { paragraph.push(lines[index]); index += 1 }
    blocks.push(<p key={`p-${index}`}>{inline(paragraph.join(' '))}</p>)
  }
  return <article className="docs-article">{blocks}</article>
}
