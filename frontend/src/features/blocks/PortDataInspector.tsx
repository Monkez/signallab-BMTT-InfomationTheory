import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Copy } from 'lucide-react'
import { getPortValues } from '../../api'
import type { NodePortPreviews, PortDataPage } from '../../types'

const pageSize = 128
type Direction = 'inputs' | 'outputs'
type PageState = { loading?: boolean; error?: string; page?: PortDataPage; copied?: boolean }

const keyFor = (direction: Direction, port: string) => `${direction}:${port}`

export function PortDataInspector({ snapshotId, nodeId, previews }: { snapshotId: string | null; nodeId: string; previews?: NodePortPreviews }) {
  const [pages, setPages] = useState<Record<string, PageState>>({})
  const ports = useMemo(() => (['inputs', 'outputs'] as Direction[]).flatMap(direction =>
    Object.keys(previews?.[direction] || {}).map(port => ({ direction, port, preview: previews?.[direction][port] })),
  ), [previews])
  const portsKey = ports.map(item => keyFor(item.direction, item.port)).join('|')

  const loadPage = useCallback(async (direction: Direction, port: string, offset: number) => {
    if (!snapshotId) return
    const key = keyFor(direction, port)
    setPages(current => ({ ...current, [key]: { ...current[key], loading: true, error: undefined } }))
    try {
      const page = await getPortValues(snapshotId, nodeId, direction, port, offset, pageSize)
      setPages(current => ({ ...current, [key]: { page } }))
    } catch (error) {
      setPages(current => ({ ...current, [key]: { error: (error as Error).message } }))
    }
  }, [nodeId, snapshotId])

  useEffect(() => {
    setPages({})
    if (!snapshotId) return
    for (const { direction, port } of ports) void loadPage(direction, port, 0)
  }, [loadPage, portsKey, snapshotId])

  const copyAll = async (direction: Direction, port: string, total: number) => {
    if (!snapshotId) return
    const key = keyFor(direction, port)
    try {
      const chunks: string[] = []
      for (let offset = 0; offset < total; offset += 4096) {
        const page = await getPortValues(snapshotId, nodeId, direction, port, offset, 4096)
        page.values.forEach((value, index) => chunks.push(`${offset + index}: ${value}`))
      }
      await navigator.clipboard.writeText(chunks.join('\n'))
      setPages(current => ({ ...current, [key]: { ...current[key], copied: true, error: undefined } }))
      window.setTimeout(() => setPages(current => ({ ...current, [key]: { ...current[key], copied: false } })), 1200)
    } catch (error) {
      setPages(current => ({ ...current, [key]: { ...current[key], error: (error as Error).message } }))
    }
  }

  if (!snapshotId || !previews) return <div className="port-data-empty">Run once or Run Benchmark to inspect every input and output value.</div>

  return <div className="port-data-inspector">
    {(['inputs', 'outputs'] as Direction[]).map(direction => {
      const group = ports.filter(item => item.direction === direction)
      return <section key={direction} className="port-data-group">
        <h5>{direction}</h5>
        {group.length ? group.map(({ port, preview }) => {
          const state = pages[keyFor(direction, port)] || {}
          const page = state.page?.snapshot_id === snapshotId && state.page.node_id === nodeId ? state.page : undefined
          const start = page ? page.offset + 1 : 0
          const end = page ? page.offset + page.values.length : 0
          return <article className="port-data-card" key={port}>
            <header><strong>{port}</strong><span>{preview?.dtype} · [{preview?.shape.join(' × ')}] · {preview?.size.toLocaleString()} values</span></header>
            {state.loading ? <div className="port-data-status">Loading values…</div> : state.error ? <div className="port-data-status error">{state.error}</div> : page ? <>
              <textarea readOnly spellCheck={false} value={page.values.map((value, index) => `${page.offset + index}: ${value}`).join('\n')} aria-label={`${direction} ${port} values`} />
              <footer>
                <span>{start.toLocaleString()}–{end.toLocaleString()} of {page.total.toLocaleString()}</span>
                <div>
                  <button onClick={() => loadPage(direction, port, Math.max(0, page.offset - pageSize))} disabled={page.offset === 0} title="Previous values"><ChevronLeft size={13} /></button>
                  <button onClick={() => loadPage(direction, port, page.offset + pageSize)} disabled={end >= page.total} title="Next values"><ChevronRight size={13} /></button>
                  <button className="copy-all" onClick={() => copyAll(direction, port, page.total)} title="Copy every value"><Copy size={12} />{state.copied ? 'Copied' : 'Copy all'}</button>
                </div>
              </footer>
            </> : null}
          </article>
        }) : <p>No {direction} ports.</p>}
      </section>
    })}
  </div>
}
