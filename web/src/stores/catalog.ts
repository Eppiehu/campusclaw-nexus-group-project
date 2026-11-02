import { reactive } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api'
import type { Row } from '../format'
import { useSession } from './session'

const keys = ['agents', 'templates', 'skills', 'materials', 'gaps', 'assignments', 'papers', 'submissions', 'weekly', 'tasks', 'audit', 'conversations', 'students', 'wrong']

export const useCatalog = defineStore('catalog', () => {
  const lists = reactive<Record<string, Row[]>>(Object.fromEntries(keys.map(key => [key, []])))

  function reset() {
    for (const key of keys) lists[key] = []
  }

  async function load() {
    const session = useSession()
    const common = ['agents', 'templates', 'skills', 'materials', 'assignments', 'papers', 'submissions', 'weekly', 'conversations']
    const extra = session.teacher ? ['gaps', 'tasks', 'audit', 'students'] : []
    const results = await Promise.all([...common, ...extra].map(async name => [name, await api('/' + name)] as const))
    for (const [name, value] of results) lists[name] = value
    lists.wrong = await api('/wrong-questions')
    for (const name of ['gaps', 'tasks', 'audit', 'students']) {
      if (!extra.includes(name)) lists[name] = []
    }
  }

  const studentName = (id: number) => lists.students.find(item => item.id === id)?.username || `学生 ${id}`
  const assignmentName = (id: number) => lists.assignments.find(item => item.id === id)?.title || `作业 ${id}`

  return { lists, load, reset, studentName, assignmentName }
})
