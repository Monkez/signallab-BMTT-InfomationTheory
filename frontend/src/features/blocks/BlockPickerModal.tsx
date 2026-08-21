import { useMemo, useState } from 'react'
import { ChevronDown, Plus, Search, X } from 'lucide-react'
import type { BlockSpec } from '../../types'
import { iconFor } from './catalog'

type BlockPickerModalProps = {
  specs: BlockSpec[]
  onAdd: (spec: BlockSpec) => void
  onClose: () => void
}

export function BlockPickerModal({ specs, onAdd, onClose }: BlockPickerModalProps) {
  const [query, setQuery] = useState('')
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => new Set())
  const searching = query.trim().length > 0
  const groups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    const priority = (spec: BlockSpec) => spec.type === 'variables' ? 0 : spec.type === 'python' ? 1 : 2
    return specs
      .filter(spec => `${spec.label} ${spec.category} ${spec.description}`.toLowerCase().includes(normalizedQuery))
      .sort((a, b) => priority(a) - priority(b))
      .reduce<Record<string, BlockSpec[]>>((result, spec) => {
        (result[spec.category] ||= []).push(spec)
        return result
      }, {})
  }, [query, specs])

  const toggleGroup = (category: string) => {
    setExpandedGroups(current => {
      const next = new Set(current)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  return <div className="block-picker-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="block-picker-modal" role="dialog" aria-modal="true" aria-labelledby="block-picker-title">
      <header className="block-picker-header">
        <div><span>BLOCK LIBRARY</span><h2 id="block-picker-title">Add block</h2><p>Search or expand a group to choose a block for the flowgraph.</p></div>
        <button type="button" onClick={onClose} title="Close block library"><X size={18} /></button>
      </header>
      <label className="block-picker-search"><Search size={16} /><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder="Search blocks…" /></label>
      <div className="block-picker-groups">
        {Object.entries(groups).length ? Object.entries(groups).map(([category, blocks]) => {
          const expanded = searching || expandedGroups.has(category)
          return <section className="block-picker-group" key={category}>
            <button type="button" className="block-picker-group-toggle" aria-expanded={expanded} onClick={() => toggleGroup(category)}>
              <ChevronDown size={16} className={expanded ? 'expanded' : ''} /><span>{category}</span><small>{blocks.length}</small>
            </button>
            {expanded && <div className="block-picker-list">{blocks.map(spec => {
              const Icon = iconFor(spec.type)
              return <button type="button" className="block-picker-item" key={spec.type} onClick={() => onAdd(spec)}>
                <span className="block-icon"><Icon size={17} /></span><span><b>{spec.label}</b><small>{spec.description}</small></span><Plus size={15} />
              </button>
            })}</div>}
          </section>
        }) : <div className="block-picker-empty"><Search size={24} /><strong>No matching blocks</strong><span>Try another name or category.</span></div>}
      </div>
    </section>
  </div>
}
