export type PythonPortLayout = { inputs: string[]; outputs: string[]; explicit: boolean }

const defaults: PythonPortLayout = { inputs: ['in'], outputs: ['out'], explicit: false }

/** Lightweight editor-side parser for PORTS metadata. Backend remains authoritative. */
export function parsePythonPorts(code: string): PythonPortLayout {
  const declaration = /\bPORTS\s*=\s*\{([\s\S]*?)\}/m.exec(code)
  if (!declaration) return { ...defaults, inputs: [...defaults.inputs], outputs: [...defaults.outputs] }
  const read = (name: string, fallback: string[]) => {
    const match = new RegExp(`["']?${name}["']?\\s*:\\s*\\[([^\\]]*)\\]`, 'm').exec(declaration[1])
    if (!match) return fallback
    const names = [...match[1].matchAll(/["']([A-Za-z][A-Za-z0-9_]*)["']/g)].map(item => item[1])
    return names.length === new Set(names).size ? names : fallback
  }
  return { inputs: read('inputs', defaults.inputs), outputs: read('outputs', defaults.outputs), explicit: true }
}
