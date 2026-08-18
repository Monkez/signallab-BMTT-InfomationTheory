type WritableFile = {
  write: (data: Blob) => Promise<void>
  close: () => Promise<void>
}

type FileHandle = {
  name: string
  getFile: () => Promise<File>
  createWritable: () => Promise<WritableFile>
}

type ProjectPickerWindow = Window & {
  showOpenFilePicker?: (options: unknown) => Promise<FileHandle[]>
  showSaveFilePicker?: (options: unknown) => Promise<FileHandle>
  pywebview?: {
    api?: {
      open_project?: () => Promise<ProjectOpenResult>
      save_project?: (content: string, saveAs: boolean, suggestedName: string) => Promise<ProjectSaveResult>
      clear_project_path?: () => Promise<void>
    }
  }
}

export type ProjectOpenResult = {
  cancelled?: boolean
  content?: string
  name?: string
  path?: string
}

export type ProjectSaveResult = {
  cancelled?: boolean
  name?: string
  path?: string
  direct?: boolean
}

let browserFileHandle: FileHandle | null = null

const pickerOptions = {
  types: [{ description: 'SignalLab simulation', accept: { 'application/json': ['.slab.json', '.json'] } }],
  excludeAcceptAllOption: false,
}

function safeProjectName(name: string) {
  const clean = name.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '-').trim() || 'untitled-simulation'
  return clean.toLowerCase().endsWith('.slab.json') ? clean : `${clean.replace(/\.json$/i, '')}.slab.json`
}

function downloadProject(content: string, filename: string) {
  const blob = new Blob([content], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.hidden = true
  document.body.appendChild(link)
  window.setTimeout(() => {
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(link.href), 1_000)
  }, 0)
}

export function projectDisplayName(filename: string) {
  return filename.replace(/\.slab\.json$/i, '').replace(/\.json$/i, '') || 'Untitled simulation'
}

export async function openProjectFile(): Promise<ProjectOpenResult | null> {
  const host = window as ProjectPickerWindow
  if (host.pywebview?.api?.open_project) {
    const result = await host.pywebview.api.open_project()
    return result.cancelled ? null : result
  }
  if (!host.showOpenFilePicker) return null
  const [handle] = await host.showOpenFilePicker(pickerOptions)
  if (!handle) return null
  browserFileHandle = handle
  const file = await handle.getFile()
  return { content: await file.text(), name: file.name }
}

export function supportsProjectOpenDialog() {
  const host = window as ProjectPickerWindow
  return Boolean(host.pywebview?.api?.open_project || host.showOpenFilePicker)
}

export async function saveProjectFile(content: string, suggestedName: string, saveAs = false): Promise<ProjectSaveResult | null> {
  const host = window as ProjectPickerWindow
  const filename = safeProjectName(suggestedName)
  if (host.pywebview?.api?.save_project) {
    const result = await host.pywebview.api.save_project(content, saveAs, filename)
    return result.cancelled ? null : result
  }

  if (host.showSaveFilePicker) {
    if (!browserFileHandle || saveAs) browserFileHandle = await host.showSaveFilePicker({ ...pickerOptions, suggestedName: filename })
    const writable = await browserFileHandle.createWritable()
    await writable.write(new Blob([content], { type: 'application/json' }))
    await writable.close()
    return { name: browserFileHandle.name, direct: true }
  }

  downloadProject(content, filename)
  return { name: filename, direct: false }
}

export async function clearProjectFileTarget() {
  browserFileHandle = null
  const host = window as ProjectPickerWindow
  await host.pywebview?.api?.clear_project_path?.()
}

export function attachBrowserProjectFile(file: File) {
  browserFileHandle = null
  return file.text().then(content => ({ content, name: file.name }))
}
