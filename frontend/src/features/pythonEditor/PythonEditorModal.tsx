import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { BookOpen, Braces, Check, Clipboard, RotateCcw, X } from 'lucide-react'
import { PythonCodeEditor } from './PythonCodeEditor'

type Props = {
  open: boolean
  blockName: string
  value: string
  template: string
  onApply: (code: string) => void
  onClose: () => void
  onOpenDocs: () => void
}

export function PythonEditorModal({ open, blockName, value, template, onApply, onClose, onOpenDocs }: Props) {
  const [draft, setDraft] = useState(value)
  const [copied, setCopied] = useState(false)
  const changed = draft !== value
  const stats = useMemo(() => ({ lines: draft.split('\n').length, chars: draft.length }), [draft])

  useEffect(() => {
    if (open) { setDraft(value); setCopied(false) }
  }, [blockName, open, value])

  useEffect(() => {
    if (!open) return
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape' && !event.defaultPrevented) onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose, open])

  if (!open) return null

  const apply = () => { onApply(draft); onClose() }
  const copy = async () => {
    await navigator.clipboard.writeText(draft)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1_400)
  }

  return createPortal(
    <div className="python-editor-overlay" role="presentation">
      <section className="python-editor-modal" role="dialog" aria-modal="true" aria-labelledby="python-editor-title">
        <header className="python-editor-modal-header">
          <div className="python-editor-file-icon"><Braces size={21} /></div>
          <div className="python-editor-file-title"><span>PYTHON BLOCK EDITOR</span><h2 id="python-editor-title">{blockName}</h2><small>process.py · trusted local code</small></div>
          <div className="python-editor-modal-actions">
            <button onClick={onOpenDocs} title="Open Python API documentation"><BookOpen size={15} /> API docs</button>
            <button onClick={() => void copy()} title="Copy all code">{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? 'Copied' : 'Copy'}</button>
            <button onClick={() => setDraft(template)} disabled={draft === template} title="Restore the default Python template"><RotateCcw size={15} /> Reset</button>
            <button className="python-editor-close" onClick={onClose} aria-label="Close Python editor"><X size={18} /></button>
          </div>
        </header>

        <div className="python-editor-workbench">
          <div className="python-editor-tabbar"><div className="active"><span className="python-dot" />process.py {changed && <i>●</i>}</div></div>
          <PythonCodeEditor value={draft} onChange={setDraft} height="100%" autoFocus onSave={apply} className="python-code-editor-large" />
          <footer className="python-editor-statusbar">
            <div><span>Python 3</span><span>UTF-8</span><span>Spaces: 4</span></div>
            <div><span>Ln {stats.lines}</span><span>{stats.chars.toLocaleString()} characters</span><span>{changed ? 'Modified' : 'No changes'}</span></div>
          </footer>
        </div>

        <footer className="python-editor-modal-footer">
          <p>SignalLab chạy hàm <code>process(signal, params)</code> cho từng frame và tự quản lý song song hóa. <kbd>Ctrl+S</kbd> hoặc <kbd>Ctrl+Enter</kbd> để áp dụng.</p>
          <div><button className="secondary" onClick={onClose}>Cancel</button><button className="primary" onClick={apply}><Check size={15} /> Apply changes</button></div>
        </footer>
      </section>
    </div>,
    document.body,
  )
}
