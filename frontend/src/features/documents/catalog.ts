import quickstart from '../../../../docs/python/QUICKSTART.md?raw'
import conventions from '../../../../docs/python/CONVENTIONS.md?raw'
import sourcesSignals from '../../../../docs/python/SOURCES_SIGNALS.md?raw'
import filters from '../../../../docs/python/FILTERS.md?raw'
import communications from '../../../../docs/python/COMMUNICATIONS.md?raw'
import codingMetrics from '../../../../docs/python/CODING_METRICS.md?raw'
import pythonBlock from '../../../../docs/python/PYTHON_BLOCK.md?raw'
import userGuide from '../../../../docs/USER_GUIDE.md?raw'

export type DocumentEntry = {
  id: string
  title: string
  category: string
  summary: string
  keywords: string
  content: string
}
export const documents: DocumentEntry[] = [
  { id: 'quickstart', title: 'Bắt đầu nhanh', category: 'Python API', summary: 'Import, ví dụ BPSK và quy tắc cơ bản.', keywords: 'quickstart import numpy scipy signallab', content: quickstart },
  { id: 'conventions', title: 'Quy ước API và dữ liệu', category: 'Python API', summary: 'Shape, dtype, seed, đơn vị và contract.', keywords: 'array shape dtype seed contract', content: conventions },
  { id: 'sources-signals', title: 'Nguồn và tín hiệu', category: 'Tham chiếu hàm', summary: 'Bit, symbol, text, công suất, dB và lấy mẫu.', keywords: 'random bits symbols text energy power rms upsample downsample', content: sourcesSignals },
  { id: 'filters', title: 'Bộ lọc và pulse shaping', category: 'Tham chiếu hàm', summary: 'FIR, matched filter, RRC và SciPy nâng cao.', keywords: 'fir lowpass bandpass matched rrc scipy signal', content: filters },
  { id: 'communications', title: 'Điều chế và kênh', category: 'Tham chiếu hàm', summary: 'BPSK, QPSK, AWGN, Rayleigh và BSC.', keywords: 'bpsk qpsk awgn rayleigh channel modulation', content: communications },
  { id: 'coding-metrics', title: 'Mã kênh và chỉ tiêu', category: 'Tham chiếu hàm', summary: 'Repetition, Hamming, BER, SER, EVM và SNR.', keywords: 'coding hamming repetition ber ser evm snr', content: codingMetrics },
  { id: 'python-block', title: 'Python Block', category: 'Làm việc trong app', summary: 'API process, alias, contract, song song hóa và debug.', keywords: 'python block process params parallel output size debug', content: pythonBlock },
  { id: 'user-guide', title: 'Hướng dẫn sử dụng SignalLab', category: 'Làm việc trong app', summary: 'Canvas, Experiment, kết quả, project và source theory.', keywords: 'user guide canvas experiment benchmark project save open', content: userGuide },
]

export const documentCategories = [...new Set(documents.map(document => document.category))]

const normalize = (value: string) => value.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g, '')

export const searchDocuments = (query: string) => {
  const terms = normalize(query).trim().split(/\s+/).filter(Boolean)
  if (!terms.length) return documents.map(document => ({ document, score: 0, snippet: document.summary }))
  return documents.map(document => {
    const title = normalize(`${document.title} ${document.keywords}`)
    const content = normalize(document.content)
    const score = terms.reduce((total, term) => total + (title.includes(term) ? 8 : 0) + (content.includes(term) ? 2 : 0), 0)
    const firstTerm = terms.find(term => content.includes(term))
    const index = firstTerm ? content.indexOf(firstTerm) : -1
    const plain = document.content.replace(/[`#*|]/g, ' ').replace(/\s+/g, ' ').trim()
    const snippet = index < 0 ? document.summary : plain.slice(Math.max(0, index - 70), index + 170)
    return { document, score, snippet: `${index > 70 ? '…' : ''}${snippet}${snippet.length >= 240 ? '…' : ''}` }
  }).filter(result => result.score > 0).sort((left, right) => right.score - left.score)
}
