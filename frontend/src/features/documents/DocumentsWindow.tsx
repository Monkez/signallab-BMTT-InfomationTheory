import { useEffect, useMemo, useState } from 'react'
import { BookOpen, ChevronRight, Search, X } from 'lucide-react'
import { documentCategories, documents, searchDocuments } from './catalog'
import { MarkdownArticle } from './MarkdownArticle'
import './documents.css'

export function DocumentsWindow() {
  const [query, setQuery] = useState('')
  const [activeId, setActiveId] = useState(documents[0].id)
  const results = useMemo(() => searchDocuments(query), [query])
  const active = documents.find(document => document.id === activeId) || documents[0]

  useEffect(() => { document.title = 'Documents — SignalLab' }, [])
  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        document.querySelector<HTMLInputElement>('.docs-search input')?.focus()
      }
    }
    window.addEventListener('keydown', focusSearch)
    return () => window.removeEventListener('keydown', focusSearch)
  }, [])
  const selectDocument = (id: string) => { setActiveId(id); setQuery(''); window.scrollTo(0, 0) }

  return <div className="docs-window">
    <header className="docs-header">
      <div className="docs-brand"><span><BookOpen size={20} /></span><div><strong>SignalLab Documents</strong><small>Python, DSP & digital communications</small></div></div>
      <label className="docs-search"><Search size={17} /><input autoFocus placeholder="Tìm hàm, khái niệm, ví dụ…" value={query} onChange={event => setQuery(event.target.value)} /><kbd>Ctrl K</kbd></label>
      <button className="docs-close" onClick={() => window.close()} title="Close Documents"><X size={20} /></button>
    </header>
    <div className="docs-layout">
      <nav className="docs-nav" aria-label="Documents menu">
        {query ? <section><h2>Kết quả tìm kiếm</h2>{results.length ? results.map(({ document, snippet }) => <button key={document.id} onClick={() => selectDocument(document.id)}><strong>{document.title}</strong><small>{snippet}</small><ChevronRight size={14} /></button>) : <p className="docs-empty">Không tìm thấy tài liệu phù hợp.</p>}</section> : documentCategories.map(category => <section key={category}><h2>{category}</h2>{documents.filter(document => document.category === category).map(document => <button className={document.id === active.id ? 'active' : ''} key={document.id} onClick={() => selectDocument(document.id)}><strong>{document.title}</strong><small>{document.summary}</small><ChevronRight size={14} /></button>)}</section>)}
      </nav>
      <main className="docs-content">
        <div className="docs-breadcrumb">Documents <ChevronRight size={13} /> {active.category} <ChevronRight size={13} /> <b>{active.title}</b></div>
        <MarkdownArticle content={active.content} />
      </main>
      <aside className="docs-index">
        <h2>Trong tài liệu</h2>
        {active.content.split('\n').filter(line => /^##\s/.test(line)).map((line, index) => {
          const text = line.replace(/^##\s+/, '')
          const id = text.toLocaleLowerCase('vi').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '')
          return <a key={`${id}-${index}`} href={`#${id}`}>{text.replace(/`/g, '')}</a>
        })}
      </aside>
    </div>
  </div>
}
