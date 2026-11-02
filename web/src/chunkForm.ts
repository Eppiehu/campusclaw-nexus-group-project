export type ChunkForm = {
  strategy: 'hierarchy' | 'auto' | 'custom'
  delimiter: 'blank' | 'newline' | 'period'
  maxChars: number
  overlapPct: number
  collapseWS: boolean
  stripURLs: boolean
}

export function defaultChunkForm(): ChunkForm {
  return { strategy: 'hierarchy', delimiter: 'newline', maxChars: 800, overlapPct: 10, collapseWS: false, stripURLs: false }
}

export function chunkFormFrom(options?: Record<string, unknown> | null): ChunkForm {
  const form = defaultChunkForm()
  if (!options) return form
  if (options.strategy === 'hierarchy' || options.strategy === 'auto' || options.strategy === 'custom') form.strategy = options.strategy
  if (options.delimiter === 'blank' || options.delimiter === 'newline' || options.delimiter === 'period') form.delimiter = options.delimiter
  const maxChars = Number(options.max_chars)
  const overlapPct = Number(options.overlap_pct)
  if (maxChars >= 100 && maxChars <= 2000) form.maxChars = maxChars
  if (overlapPct >= 0 && overlapPct <= 50) form.overlapPct = overlapPct
  form.collapseWS = options.collapse_ws === true || options.collapse_ws === '1' || options.collapse_ws === 1
  form.stripURLs = options.strip_urls === true || options.strip_urls === '1' || options.strip_urls === 1
  return form
}

export function chunkPayload(chunk: ChunkForm) {
  const payload: Record<string, string | number | boolean> = { strategy: chunk.strategy }
  if (chunk.strategy === 'hierarchy' || chunk.strategy === 'custom') {
    payload.max_chars = chunk.maxChars
    payload.overlap_pct = chunk.overlapPct
  }
  if (chunk.strategy === 'custom') {
    payload.delimiter = chunk.delimiter
    payload.collapse_ws = chunk.collapseWS
    payload.strip_urls = chunk.stripURLs
  }
  return payload
}

export function appendChunkFields(form: FormData, chunk: ChunkForm) {
  form.append('strategy', chunk.strategy)
  if (chunk.strategy === 'hierarchy' || chunk.strategy === 'custom') {
    form.append('max_chars', String(chunk.maxChars))
    form.append('overlap_pct', String(chunk.overlapPct))
  }
  if (chunk.strategy === 'custom') {
    form.append('delimiter', chunk.delimiter)
    if (chunk.collapseWS) form.append('collapse_ws', '1')
    if (chunk.stripURLs) form.append('strip_urls', '1')
  }
}
