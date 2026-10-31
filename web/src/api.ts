const statusText: Record<number, string> = { 401: '请先登录', 403: '权限不足', 404: '资源不存在' }

export const base = '/api/nexus'
export const token = () => localStorage.getItem('nexus-token') || ''

export async function api(path: string, method = 'GET', body?: unknown): Promise<any> {
  const form = body instanceof FormData
  const response = await fetch(base + path, {
    method,
    credentials: 'omit',
    headers: { Authorization: 'Bearer ' + token(), ...(!form && body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  })
  let value: any = {}
  try { value = await response.json() } catch { value = {} }
  if (!response.ok) throw new Error(value.error || statusText[response.status] || '请求失败')
  return value
}

async function materialResponse(id: number) {
  const response = await fetch(base + `/materials/${id}/download`, { headers: { Authorization: 'Bearer ' + token() }, credentials: 'omit' })
  if (!response.ok) {
    let message = statusText[response.status] || '材料不可用或无权访问'
    try {
      const value = await response.json()
      if (value.error) message = value.error
    } catch { /* 下载失败时响应不一定是 JSON */ }
    throw new Error(message)
  }
  return response
}

export async function materialText(id: number) {
  return (await materialResponse(id)).text()
}

export async function download(id: number) {
  const response = await materialResponse(id)
  const url = URL.createObjectURL(await response.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = `讲义-${id}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
