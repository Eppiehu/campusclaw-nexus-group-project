export function isolatedBaseURL() {
  const raw = process.env.PLAYWRIGHT_BASE_URL?.trim()
  if (!raw) throw new Error('必须设置 PLAYWRIGHT_BASE_URL，例如 http://127.0.0.1:8080。此套件没有默认主机，不会访问公网。')
  let url: URL
  try { url = new URL(raw) } catch { throw new Error('PLAYWRIGHT_BASE_URL 必须是绝对 http(s) 地址') }
  if (url.username || url.password) throw new Error('不要把账号或口令写进 PLAYWRIGHT_BASE_URL')
  if (url.protocol !== 'http:' && url.protocol !== 'https:') throw new Error('只接受 http 或 https')
  const local = url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '::1'
  if (!local && process.env.E2E_CONFIRM_ISOLATED !== 'yes') {
    throw new Error('拒绝非本机地址。若确认为隔离实验环境，请显式设置 E2E_CONFIRM_ISOLATED=yes；默认不会连接公网或生产环境。')
  }
  return url.origin
}

export function e2ePassword(name: string) {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`必须设置 ${name}。使用隔离环境里的虚构种子口令，不要把口令写进仓库。`)
  return value
}
