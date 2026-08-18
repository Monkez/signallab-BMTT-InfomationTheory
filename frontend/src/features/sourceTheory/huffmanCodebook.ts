export type HuffmanCodeRow = {
  symbol: string
  probability: number
  information: number
  code: string
  length: number
}

export type HuffmanCodebook = {
  rows: HuffmanCodeRow[]
  entropy: number
  averageLength: number
  efficiency: number
}

type TreeNode = { weight: number; order: number; codes: Map<number, string> }

const decodeSymbol = (token: string) => ({ '<space>': ' ', '\\n': '\n', '\\t': '\t' })[token] ?? token

export function buildHuffmanCodebook(params: Record<string, string | number | boolean>): HuffmanCodebook {
  const alphabet = String(params.alphabet ?? 'A,B,C,D').split(',').map(token => decodeSymbol(token.trim()))
  if (!alphabet.length || alphabet.some(symbol => !symbol) || new Set(alphabet).size !== alphabet.length) {
    throw new Error('Alphabet must contain unique, non-empty symbols.')
  }
  const weights = String(params.probabilities ?? '0.5,0.25,0.125,0.125').split(',').map(value => Number(value.trim()))
  if (weights.length !== alphabet.length || weights.some(value => !Number.isFinite(value) || value <= 0)) {
    throw new Error('Enter one positive probability for every symbol.')
  }
  const total = weights.reduce((sum, value) => sum + value, 0)
  const probabilities = weights.map(value => value / total)
  let queue: TreeNode[] = probabilities.map((weight, symbol) => ({ weight, order: symbol, codes: new Map([[symbol, '']]) }))
  let nextOrder = queue.length
  while (queue.length > 1) {
    queue.sort((a, b) => a.weight - b.weight || a.order - b.order)
    const left = queue.shift()!
    const right = queue.shift()!
    const codes = new Map<number, string>()
    left.codes.forEach((code, symbol) => codes.set(symbol, `0${code}`))
    right.codes.forEach((code, symbol) => codes.set(symbol, `1${code}`))
    queue.push({ weight: left.weight + right.weight, order: nextOrder++, codes })
  }
  const codes = queue[0]?.codes ?? new Map([[0, '0']])
  const rows = alphabet.map((symbol, index) => {
    const probability = probabilities[index]
    const code = codes.get(index) || '0'
    return { symbol, probability, information: -Math.log2(probability), code, length: code.length }
  })
  const entropy = rows.reduce((sum, row) => sum + row.probability * row.information, 0)
  const averageLength = rows.reduce((sum, row) => sum + row.probability * row.length, 0)
  return { rows, entropy, averageLength, efficiency: averageLength ? 100 * entropy / averageLength : 100 }
}

export const displaySymbol = (symbol: string) => symbol === ' ' ? '␠' : symbol === '\n' ? '↵' : symbol === '\t' ? '⇥' : symbol
