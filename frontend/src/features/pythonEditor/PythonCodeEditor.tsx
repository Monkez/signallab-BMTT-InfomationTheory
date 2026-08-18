import CodeMirror from '@uiw/react-codemirror'
import { indentWithTab } from '@codemirror/commands'
import { HighlightStyle, indentUnit, syntaxHighlighting } from '@codemirror/language'
import { python } from '@codemirror/lang-python'
import { EditorView, keymap } from '@codemirror/view'
import { tags } from '@lezer/highlight'

const signalLabEditorTheme = EditorView.theme({
  '&': { backgroundColor: '#101823', color: '#d8e2ef', fontSize: '12px' },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { fontFamily: '"Cascadia Code", "JetBrains Mono", Consolas, monospace', lineHeight: '1.65' },
  '.cm-content': { padding: '12px 0', caretColor: '#78a9ff' },
  '.cm-line': { padding: '0 14px 0 8px' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: '#78a9ff', borderLeftWidth: '2px' },
  '.cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection': { backgroundColor: '#29466d !important' },
  '.cm-activeLine': { backgroundColor: '#172231' },
  '.cm-gutters': { minWidth: '45px', borderRight: '1px solid #263449', backgroundColor: '#0c131d', color: '#607089' },
  '.cm-lineNumbers .cm-gutterElement': { minWidth: '34px', padding: '0 9px 0 5px' },
  '.cm-activeLineGutter': { backgroundColor: '#172231', color: '#a9bdd7' },
  '.cm-foldGutter .cm-gutterElement': { padding: '0 4px' },
  '.cm-matchingBracket': { borderBottom: '1px solid #7dd3fc', backgroundColor: '#203851', color: '#fff' },
  '.cm-tooltip': { border: '1px solid #33445a', backgroundColor: '#172231', color: '#d8e2ef' },
  '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: '#24559a', color: '#fff' },
  '.cm-panels': { borderColor: '#2a3a4f', backgroundColor: '#121d2a', color: '#c8d6e8' },
}, { dark: true })

const signalLabHighlightStyle = HighlightStyle.define([
  { tag: [tags.keyword, tags.modifier], color: '#c792ea' },
  { tag: [tags.name, tags.variableName], color: '#d8e2ef' },
  { tag: [tags.function(tags.variableName), tags.definition(tags.variableName)], color: '#82aaff' },
  { tag: [tags.typeName, tags.className], color: '#ffcb6b' },
  { tag: [tags.string, tags.special(tags.string)], color: '#c3e88d' },
  { tag: [tags.number, tags.bool, tags.null], color: '#f78c6c' },
  { tag: [tags.comment, tags.docComment], color: '#637990', fontStyle: 'italic' },
  { tag: [tags.operator, tags.punctuation], color: '#89ddff' },
  { tag: tags.propertyName, color: '#f07178' },
])

type Props = {
  value: string
  onChange: (value: string) => void
  height?: string
  autoFocus?: boolean
  onSave?: () => void
  className?: string
}

export function PythonCodeEditor({ value, onChange, height = '290px', autoFocus = false, onSave, className = '' }: Props) {
  const saveKeymap = onSave ? keymap.of([
    { key: 'Mod-s', preventDefault: true, run: () => { onSave(); return true } },
    { key: 'Mod-Enter', preventDefault: true, run: () => { onSave(); return true } },
    indentWithTab,
  ]) : keymap.of([indentWithTab])

  return <div className={`python-code-editor ${className}`.trim()}>
    <CodeMirror
      value={value}
      height={height}
      autoFocus={autoFocus}
      onChange={onChange}
      theme={signalLabEditorTheme}
      extensions={[python(), indentUnit.of('    '), syntaxHighlighting(signalLabHighlightStyle), saveKeymap]}
      basicSetup={{
        lineNumbers: true,
        foldGutter: true,
        highlightActiveLine: true,
        highlightActiveLineGutter: true,
        bracketMatching: true,
        closeBrackets: true,
        autocompletion: true,
        history: true,
        indentOnInput: true,
        syntaxHighlighting: true,
      }}
    />
  </div>
}
