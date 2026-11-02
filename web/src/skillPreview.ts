export type SkillDraft = { name: string, description: string, body: string }

function clip(value: string, maximum: number) {
  return value.trim().slice(0, maximum)
}

function yamlValue(header: string, key: string) {
  const lines = header.split('\n')
  for (let index = 0; index < lines.length; index += 1) {
    const match = lines[index].match(new RegExp(`^${key}:\\s*(.*)$`))
    if (!match) continue
    const rest = match[1].trim()
    if (rest === '|' || rest === '>') {
      const block: string[] = []
      for (let next = index + 1; next < lines.length; next += 1) {
        if (/^\S/.test(lines[next])) break
        block.push(lines[next].replace(/^\s+/, ''))
      }
      return block.join('\n').trim()
    }
    if ((rest.startsWith('"') && rest.endsWith('"')) || (rest.startsWith("'") && rest.endsWith("'"))) return rest.slice(1, -1)
    return rest
  }
  return ''
}

export function detectSkill(source: string): SkillDraft {
  const text = source.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n')
  const lines = text.split('\n')
  if (lines[0]?.trim() === '---') {
    const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---')
    if (end > 0) {
      const header = lines.slice(1, end).join('\n')
      return {
        name: clip(yamlValue(header, 'name'), 64),
        description: clip(yamlValue(header, 'description'), 2000),
        body: clip(lines.slice(end + 1).join('\n'), 2000),
      }
    }
  }
  let name = ''
  let description = ''
  let bodyStart = -1
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    if (!line.trim()) {
      if (name || description) { bodyStart = index + 1; break }
      continue
    }
    const match = line.match(/^\s*(名称|适用条件|启用|资料|工具)\s*[：:]\s*(.*)$/)
    if (!match) break
    if (match[1] === '名称') name = match[2].trim()
    if (match[1] === '适用条件') description = match[2].trim()
  }
  if (bodyStart >= 0) {
    return { name: clip(name, 64), description: clip(description, 2000), body: clip(lines.slice(bodyStart).join('\n'), 2000) }
  }
  const heading = text.match(/^#{1,6}\s+(.+)$/m)
  if (heading) {
    return { name: clip(heading[1], 64), description: '', body: clip(text.replace(heading[0], ''), 2000) }
  }
  const first = lines.find(line => line.trim()) || ''
  return { name: clip(first, 64), description: '', body: clip(text, 2000) }
}
