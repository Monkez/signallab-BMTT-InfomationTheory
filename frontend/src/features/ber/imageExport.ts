import { previewChart } from './constants'

export async function svgToPng(svg: SVGSVGElement): Promise<Blob> {
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  const source = new XMLSerializer().serializeToString(clone)
  const image = new Image()
  const url = URL.createObjectURL(new Blob([source], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error('Could not render chart image')); image.src = url })
    const scale = 3
    const canvas = document.createElement('canvas')
    canvas.width = previewChart.width * scale
    canvas.height = previewChart.height * scale
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas is unavailable')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return await new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Could not encode chart image')), 'image/png'))
  } finally { URL.revokeObjectURL(url) }
}

export async function copyPng(blob: Blob) {
  if (!navigator.clipboard || typeof ClipboardItem === 'undefined') throw new Error('Image clipboard is unavailable')
  await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
}
