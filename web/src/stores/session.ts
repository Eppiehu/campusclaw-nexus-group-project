import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type { Row } from '../format'

export const useSession = defineStore('session', () => {
  const user = ref<Row | null>(null)
  const busy = ref(false)
  const error = ref('')
  const previewing = ref(false)
  const teacher = computed(() => user.value?.role === 'teacher')

  async function action<T>(fn: () => Promise<T>): Promise<T | undefined> {
    if (previewing.value) { ElMessage.info('静态预览不会连接服务器'); return }
    error.value = ''
    busy.value = true
    try { return await fn() }
    catch (e: any) { error.value = e.message; ElMessage.error(e.message) }
    finally { busy.value = false }
  }

  async function restore() {
    user.value = await api('/me')
    return user.value
  }

  async function login(username: string, password: string) {
    const result = await api('/login', 'POST', { username, password })
    localStorage.setItem('nexus-token', result.token)
    user.value = result.user
    return result.user as Row
  }

  async function logout() {
    await api('/logout', 'POST')
    localStorage.removeItem('nexus-token')
    user.value = null
  }

  return { user, busy, error, previewing, teacher, action, restore, login, logout }
})
