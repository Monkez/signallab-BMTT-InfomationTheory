import { useEffect, useState, type InputHTMLAttributes } from 'react'

type NumericInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> & {
  value: number
  onValueChange: (value: number) => void
  integer?: boolean
}

const COMPLETE_NUMBER = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i
const PARTIAL_NUMBER = /^[+-]?(?:(?:\d+(?:\.\d*)?|\.\d*)?(?:e[+-]?\d*)?)?$/i

export function NumericInput({ value, onValueChange, integer = false, className = '', ...inputProps }: NumericInputProps) {
  const [draft, setDraft] = useState(() => String(value))
  const [focused, setFocused] = useState(false)

  useEffect(() => {
    if (!focused) setDraft(String(value))
  }, [focused, value])

  const commitIfValid = (text: string) => {
    if (!COMPLETE_NUMBER.test(text.trim())) return false
    const numeric = Number(text)
    if (!Number.isFinite(numeric) || (integer && !Number.isSafeInteger(numeric))) return false
    onValueChange(numeric)
    return true
  }

  const invalid = draft !== '' && (!COMPLETE_NUMBER.test(draft.trim()) || !Number.isFinite(Number(draft)) || (integer && !Number.isSafeInteger(Number(draft))))

  return <input
    {...inputProps}
    className={`${className}${invalid ? ' numeric-input-invalid' : ''}`}
    type="text"
    inputMode={integer ? 'numeric' : 'decimal'}
    value={draft}
    aria-invalid={invalid || undefined}
    onFocus={() => setFocused(true)}
    onChange={event => {
      const next = event.target.value
      if (!PARTIAL_NUMBER.test(next.trim())) return
      setDraft(next)
      commitIfValid(next)
    }}
    onBlur={() => {
      setFocused(false)
      if (!commitIfValid(draft)) setDraft(String(value))
    }}
    onKeyDown={event => {
      if (event.key === 'Enter') event.currentTarget.blur()
      inputProps.onKeyDown?.(event)
    }}
  />
}
