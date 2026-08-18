import { Braces, CircleAlert, CircleCheck } from 'lucide-react'

type Props = {
  definitions: string
  onChange: (definitions: string) => void
}

type Preview = { line: number; name: string; value: string; kind: string; valid: boolean }

const previewDefinitions = (source: string): Preview[] => source.split(/\r?\n/).flatMap<Preview>((raw, index) => {
  const line = raw.trim()
  if (!line || line.startsWith('#')) return []
  const match = /^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)$/.exec(line)
  if (!match) return [{ line: index + 1, name: 'Invalid declaration', value: line, kind: 'error', valid: false }]
  const [, name, value] = match
  const kind = /^[-+]?\d[\d_]*$/.test(value) ? 'int'
    : /^[-+]?(?:\d[\d_]*)?\.\d[\d_]*(?:e[-+]?\d+)?$/i.test(value) ? 'float'
      : /^(True|False)$/.test(value) ? 'bool'
        : value === 'None' ? 'None'
          : /^(['"]).*\1$/.test(value) ? 'str'
            : value.startsWith('[') ? 'list'
              : value.startsWith('{') ? 'dict'
                : value.startsWith('(') ? 'tuple' : 'literal'
  return [{ line: index + 1, name, value, kind, valid: true }]
})

export function VariablesEditor({ definitions, onChange }: Props) {
  const preview = previewDefinitions(definitions)
  const hasInvalid = preview.some(item => !item.valid)
  return <section className="variables-editor">
    <div className="variables-editor-head"><div><Braces size={16} /><span><b>Global definitions</b><small>Safe Python literals</small></span></div><span className={hasInvalid ? 'invalid' : 'valid'}>{hasInvalid ? <CircleAlert size={14} /> : <CircleCheck size={14} />}{hasInvalid ? 'Check syntax' : `${preview.length} variables`}</span></div>
    <textarea aria-label="Global variable definitions" spellCheck={false} value={definitions} onChange={event => onChange(event.target.value)} />
    <p>Use one assignment per line. Supported: numbers, text, booleans, lists, tuples and dictionaries. Expressions and function calls are intentionally disabled.</p>
    {preview.length > 0 && <div className="variables-preview">{preview.map(item => <div className={item.valid ? '' : 'invalid'} key={`${item.line}-${item.name}`}><code>{item.name}</code><span>{item.value}</span><em>{item.kind}</em></div>)}</div>}
    <div className="variables-runtime"><b>In a Python Block</b><code>params["symbol_rate"]</code><code>params["variables"]</code><small>Runtime keys: snr_db · trial_index · frame_seed · device · experiment</small></div>
  </section>
}
