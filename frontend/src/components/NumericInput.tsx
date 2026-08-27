import { useEffect, useRef, useState, type InputHTMLAttributes } from 'react'

type NumericInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> & {
  value: number | null
  onValueChange: (value: number) => void
  integer?: boolean
  allowEmpty?: boolean
}

const COMPLETE_NUMBER = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i
const PARTIAL_NUMBER = /^[+-]?(?:(?:\d+(?:\.\d*)?|\.\d*)?(?:e[+-]?\d*)?)?$/i
const GROUPED_INTEGER = /^[+-]?\d{1,3}(?:\.\d{3})+$/

const formatNumber = (value: number | null) => {
  if (value === null) return ''
  if (!Number.isFinite(value)) return String(value)
  const text = String(value)
  if (/[eE]/.test(text)) return text
  const [integer, fraction] = text.split('.')
  const sign = integer.startsWith('-') || integer.startsWith('+') ? integer.slice(0, 1) : ''
  const digits = sign ? integer.slice(1) : integer
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${sign}${grouped}${fraction === undefined ? '' : `.${fraction}`}`
}

const parseNumber = (text: string) => {
  const trimmed = text.trim()
  if (!COMPLETE_NUMBER.test(trimmed) && !GROUPED_INTEGER.test(trimmed)) return null
  const numeric = Number(GROUPED_INTEGER.test(trimmed) ? trimmed.replaceAll('.', '') : trimmed)
  return Number.isFinite(numeric) ? numeric : null
}

export function NumericInput({ value, onValueChange, integer = false, allowEmpty = false, className = '', ...inputProps }: NumericInputProps) {
  const [draft, setDraft] = useState(() => formatNumber(value))
  const [focused, setFocused] = useState(false)
  const committedDraft = useRef(formatNumber(value))

  useEffect(() => {
    if (!focused) {
      const next = formatNumber(value)
      committedDraft.current = next
      setDraft(next)
    }
  }, [focused, value])

  const commitIfValid = (text: string) => {
    if (allowEmpty && text.trim() === '') {
      onValueChange(null as unknown as number)
      committedDraft.current = ''
      setDraft('')
      return true
    }
    const numeric = parseNumber(text)
    if (numeric === null || (integer && !Number.isSafeInteger(numeric))) return false
    onValueChange(numeric)
    const normalized = formatNumber(numeric)
    committedDraft.current = normalized
    setDraft(normalized)
    return true
  }

  const parsedDraft = parseNumber(draft)
  const invalid = draft !== '' && !PARTIAL_NUMBER.test(draft.trim()) && parsedDraft === null

  return <input
    {...inputProps}
    className={`${className}${invalid ? ' numeric-input-invalid' : ''}`}
    type="text"
    inputMode="decimal"
    value={draft}
    aria-invalid={invalid || undefined}
    onFocus={event => {
      setFocused(true)
      // Edit the unformatted value; grouping is restored after commit.
      setDraft(String(value))
      event.currentTarget.select()
    }}
    onChange={event => {
      const next = event.target.value
      if (!PARTIAL_NUMBER.test(next.trim())) return
      setDraft(next)
    }}
    onBlur={() => {
      setFocused(false)
      // Editing is transactional: an unfinished edit is discarded unless the
      // user explicitly confirms it with Enter. This makes Backspace/delete
      // safe and prevents min/max coercion while the field is being rewritten.
      if (draft !== committedDraft.current) setDraft(committedDraft.current)
    }}
    onKeyDown={event => {
      if (event.key === 'Enter') {
        event.preventDefault()
        commitIfValid(draft)
        event.currentTarget.blur()
      } else if (event.key === 'Escape') {
        event.preventDefault()
        setDraft(committedDraft.current)
        event.currentTarget.blur()
      }
      inputProps.onKeyDown?.(event)
    }}
  />
}
