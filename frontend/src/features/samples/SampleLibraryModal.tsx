import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { ArrowRight, Blocks, CheckCircle2, Clock3, Code2, GraduationCap, Search, X } from 'lucide-react'
import { sampleCatalog, sampleCategories } from './catalog'
import type { SampleProject } from './types'

type Props = {
  open: boolean
  onClose: () => void
  onOpenSample: (sample: SampleProject) => void
}

export function SampleLibraryModal({ open, onClose, onOpenSample }: Props) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<(typeof sampleCategories)[number]>('All')
  const [selectedId, setSelectedId] = useState(sampleCatalog[0]?.sample.id || '')

  const samples = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('vi')
    return sampleCatalog.filter(project => {
      const metadata = project.sample
      const matchesCategory = category === 'All' || metadata.category === category
      const haystack = [metadata.title, metadata.subtitle, metadata.summary, metadata.category, ...metadata.concepts, ...project.graph.nodes.map(node => node.label)].join(' ').toLocaleLowerCase('vi')
      return matchesCategory && (!needle || haystack.includes(needle))
    })
  }, [category, query])

  const selected = samples.find(project => project.sample.id === selectedId) || samples[0]

  useEffect(() => {
    if (open && samples.length && !samples.some(project => project.sample.id === selectedId)) setSelectedId(samples[0].sample.id)
  }, [open, samples, selectedId])

  useEffect(() => {
    if (!open) return
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose, open])

  if (!open) return null

  return createPortal(
    <div className="samples-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <section className="samples-modal" role="dialog" aria-modal="true" aria-labelledby="samples-title">
        <header className="samples-header">
          <div>
            <span className="samples-eyebrow">LEARNING LIBRARY</span>
            <h2 id="samples-title">Open Samples</h2>
            <p>Mở một bài thực hành hoàn chỉnh, chạy thử rồi thay đổi tham số để kiểm chứng lý thuyết.</p>
          </div>
          <button className="samples-close" onClick={onClose} aria-label="Close sample library"><X size={20} /></button>
        </header>

        <div className="samples-filters">
          <label className="samples-search"><Search size={17} /><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Tìm theo tên bài, khái niệm hoặc block…" /></label>
          <div className="samples-categories" aria-label="Sample categories">
            {sampleCategories.map(item => <button key={item} className={category === item ? 'active' : ''} onClick={() => setCategory(item)}>{item}</button>)}
          </div>
        </div>

        <div className="samples-body">
          <aside className="samples-list" aria-label="Available samples">
            <div className="samples-count">{samples.length} bài thực hành</div>
            {samples.map(project => {
              const item = project.sample
              return <button key={item.id} className={`sample-card ${selected?.sample.id === item.id ? 'selected' : ''}`} onClick={() => setSelectedId(item.id)}>
                <div className="sample-card-top"><span>{item.category}</span>{item.uses_python && <em><Code2 size={11} /> Python</em>}</div>
                <strong>{item.title}</strong>
                <small>{item.subtitle}</small>
                <footer><span><GraduationCap size={12} />{item.level}</span><span><Clock3 size={12} />{item.duration_minutes} phút</span><span><Blocks size={12} />{project.graph.nodes.length} blocks</span></footer>
              </button>
            })}
            {!samples.length && <div className="samples-empty"><Search size={22} /><strong>Không tìm thấy bài phù hợp</strong><span>Thử từ khóa hoặc nhóm nội dung khác.</span></div>}
          </aside>

          {selected && <article className="sample-detail">
            <div className="sample-detail-heading">
              <div><span>{selected.sample.category} · {selected.sample.level}</span><h3>{selected.sample.title}</h3><p>{selected.sample.summary}</p></div>
              {selected.sample.uses_python && <div className="python-badge"><Code2 size={16} /><span><b>Python Block</b><small>Có mã nguồn mẫu để chỉnh sửa</small></span></div>}
            </div>

            <section className="sample-flow-section">
              <h4>Sơ đồ được nạp</h4>
              <div className="sample-flow">
                {selected.graph.nodes.map((node, index) => <div className="sample-flow-item" key={node.id}><span>{node.label}</span>{index < selected.graph.nodes.length - 1 && <ArrowRight size={14} />}</div>)}
              </div>
            </section>

            <div className="sample-learning-grid">
              <section><h4>Mục tiêu học tập</h4><ul>{selected.sample.learning_objectives.map(item => <li key={item}><CheckCircle2 size={14} />{item}</li>)}</ul></section>
              <section><h4>Khái niệm trọng tâm</h4><div className="sample-concepts">{selected.sample.concepts.map(item => <span key={item}>{item}</span>)}</div></section>
            </div>

            <section className="sample-steps"><h4>Quy trình thực hành</h4><ol>{selected.sample.instructions.map((item, index) => <li key={item}><b>{index + 1}</b><span>{item}</span></li>)}</ol></section>
            <section className="sample-observations"><h4>Kết quả cần quan sát</h4><ul>{selected.sample.expected_observations.map(item => <li key={item}>{item}</li>)}</ul></section>

            <footer className="sample-detail-footer">
              <span>Sample sẽ mở thành một simulation chưa lưu để bạn tự do chỉnh sửa.</span>
              <button onClick={() => onOpenSample(selected)}>Open this sample <ArrowRight size={16} /></button>
            </footer>
          </article>}
        </div>
      </section>
    </div>,
    document.body,
  )
}
