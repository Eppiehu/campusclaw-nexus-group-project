import { reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, base, token } from '../api'
import type { Row } from '../format'
import { useCatalog } from './catalog'

export const useChat = defineStore('chat', () => {
  const conversationId = ref<number | null>(null)
  const agentId = ref<number | null>(null)
  const drafting = ref(false)
  const draftAgentId = ref<number | null>(null)
  const chatRows = ref<Row[]>([])
  const question = ref('')
  const sending = ref(false)
  const toolEvents = ref<Row[]>([])
  const snapshot = ref<Row | null>(null)
  let stream: AbortController | null = null

  function reset() {
    stream?.abort()
    stream = null
    conversationId.value = null
    agentId.value = null
    drafting.value = false
    draftAgentId.value = null
    chatRows.value = []
    question.value = ''
    sending.value = false
    toolEvents.value = []
    snapshot.value = null
  }

  function stop() {
    stream?.abort()
    stream = null
  }

  function draft(nextAgent?: number) {
    stop()
    conversationId.value = null
    chatRows.value = []
    question.value = ''
    toolEvents.value = []
    snapshot.value = null
    if (nextAgent) agentId.value = nextAgent
    draftAgentId.value = agentId.value
    drafting.value = true
  }

  function prepareReview(text: string, nextAgent?: number) {
    draft(nextAgent)
    question.value = text
  }

  function resumeDraft() {
    if (!drafting.value) return
    stop()
    conversationId.value = null
    chatRows.value = []
    question.value = ''
    toolEvents.value = []
    snapshot.value = null
    if (draftAgentId.value) agentId.value = draftAgentId.value
  }

  function discardDraft() {
    drafting.value = false
    draftAgentId.value = null
  }

  async function open(row: { id: number, agent_id?: number | null }) {
    conversationId.value = row.id
    if (row.agent_id) agentId.value = row.agent_id
    chatRows.value = await api(`/conversations/${row.id}/messages`)
    toolEvents.value = []
  }

  async function createConversation() {
    if (!agentId.value) {
      const first = useCatalog().lists.agents.find(item => item.enabled)
      if (!first) throw new Error('本班没有已启用的学习助手')
      agentId.value = Number(first.id)
    }
    const row = await api('/conversations', 'POST', { agent_id: agentId.value })
    conversationId.value = row.id
    drafting.value = false
    draftAgentId.value = null
    chatRows.value = []
    toolEvents.value = []
    await useCatalog().load()
    return row as Row
  }

  async function ask() {
    if (!question.value.trim() || sending.value) return
    if (!conversationId.value) await createConversation()
    const text = question.value
    question.value = ''
    chatRows.value.push({ role: 'user', content: text })
    const answer = reactive<Row>({ role: 'assistant', content: '', citations: [] })
    chatRows.value.push(answer)
    sending.value = true
    stream = new AbortController()
    try {
      const response = await fetch(base + `/conversations/${conversationId.value}/messages`, {
        method: 'POST',
        credentials: 'omit',
        signal: stream.signal,
        headers: { Authorization: 'Bearer ' + token(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })
      if (!response.ok) throw new Error((await response.json()).error || '请求失败')
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let doneEvent = false
      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value, { stream: !done })
        buffer = buffer.replace(/\r\n/g, '\n')
        let end = buffer.indexOf('\n\n')
        while (end >= 0) {
          const frame = buffer.slice(0, end)
          buffer = buffer.slice(end + 2)
          const line = frame.split('\n').filter(item => item.startsWith('data:')).map(item => item.slice(5)).join('\n')
          if (line) {
            const item = JSON.parse(line)
            if (item.event === 'meta') { answer.citations = item.citations; answer.skill = item.skill; answer.gap_id = item.gap_id }
            else if (item.event === 'delta') answer.content += item.text
            else if (item.event === 'tool') toolEvents.value.push(item)
            else if (item.event === 'done') doneEvent = true
            else if (item.event === 'error') throw new Error(item.error)
          }
          end = buffer.indexOf('\n\n')
        }
        if (done) break
      }
      if (!doneEvent) throw new Error('连接中断，本轮未确认保存，请重新打开会话检查')
      await useCatalog().load()
    } catch (error: any) {
      if (error?.name === 'AbortError') return
      throw error
    } finally {
      sending.value = false
      stream = null
    }
  }

  return { conversationId, agentId, drafting, draftAgentId, chatRows, question, sending, toolEvents, snapshot, reset, stop, draft, prepareReview, resumeDraft, discardDraft, open, createConversation, ask }
})
