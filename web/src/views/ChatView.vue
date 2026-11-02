<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import type { Row } from '../format'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import { useChat } from '../stores/chat'
import { renderAssistant } from '../markdown'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const chat = useChat()
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/conversations')) : '')
const started = computed(() => chat.chatRows.length > 0)
const agentLocked = computed(() => chat.sending || started.value)
const switchAgents = computed(() => {
  const enabled = catalog.lists.agents.filter(item => item.enabled)
  const current = catalog.lists.agents.find(item => item.id === chat.agentId)
  if (current && !enabled.some(item => item.id === current.id)) return [current, ...enabled]
  return enabled
})

async function openFromRoute(id: string | string[] | undefined) {
  const numeric = Number(id)
  if (!numeric || chat.conversationId === numeric || session.previewing) return
  await session.action(async () => {
    const row = catalog.lists.conversations.find(item => item.id === numeric)
    await chat.open(row ? { id: Number(row.id), agent_id: row.agent_id } : { id: numeric, agent_id: chat.agentId })
  })
}

function openLatest() {
  if (route.params.id || chat.drafting) return
  const rows = catalog.lists.conversations
  if (!rows.length) return
  const current = rows.find(item => item.id === chat.conversationId)
  const target = current || rows[0]
  if (session.previewing) {
    if (chat.conversationId !== Number(target.id)) selectConversation(target)
    return
  }
  router.replace(`${prefix.value}/conversations/${target.id}`)
}

watch(() => route.params.id, id => { openFromRoute(id); openLatest() }, { immediate: true })
watch(() => catalog.lists.conversations.map(item => item.id).join(','), () => openLatest())
watch(() => catalog.lists.conversations, rows => {
  const row = rows.find(item => item.id === Number(route.params.id))
  if (row) chat.agentId = row.agent_id
})
watch(() => catalog.lists.agents, rows => {
  if (chat.agentId || !rows.length) return
  const first = rows.find(item => item.enabled)
  if (first) chat.agentId = Number(first.id)
}, { immediate: true })

async function chooseAgent(value: number | string) {
  const id = Number(value)
  if (!id || id === chat.agentId || agentLocked.value) return
  if (session.previewing || !chat.conversationId) {
    chat.agentId = id
    if (chat.drafting) chat.draftAgentId = id
    return
  }
  const saved = await session.action(async () => {
    const result = await api(`/conversations/${chat.conversationId}/agent`, 'PATCH', { agent_id: id })
    await catalog.load()
    return result
  })
  if (saved) chat.agentId = Number(saved.agent_id)
}

function createConversation() {
  chat.draft()
  if (route.params.id) router.replace(`${prefix.value}/conversations`)
  if (session.previewing) ElMessage.info('静态预览不会连接服务器')
}

function resumeDraft() {
  chat.resumeDraft()
  if (route.params.id) router.replace(`${prefix.value}/conversations`)
}

async function selectConversation(row: Row) {
  if (session.previewing) {
    chat.conversationId = Number(row.id)
    chat.agentId = row.agent_id
    chat.chatRows = [
      { role: 'user', content: '分数相加要先通分吗？' },
      { role: 'assistant', content: '要先通分，再把分子相加。依据来自本班讲义《第一章 分数运算》。', citations: [{ id: 1, title: '第一章 分数运算', version: 1, start: 0, end: 24, content: '分数相加需要先通分，再把分子相加。' }] },
    ]
    return
  }
  await session.action(() => chat.open({ id: Number(row.id), agent_id: row.agent_id }))
  if (!session.error) router.push(`${prefix.value}/conversations/${row.id}`)
}

async function removeConversation(row: Row) {
  if (session.previewing) { ElMessage.info('静态预览不会连接服务器'); return }
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后这段对话不能恢复。', '删除对话', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/conversations/${row.id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (!removed) return
  if (chat.conversationId === Number(row.id)) {
    chat.stop()
    chat.conversationId = null
    chat.chatRows = []
    if (route.params.id) router.replace(`${prefix.value}/conversations`)
  }
  ElMessage.success('对话已删除')
}

async function ask() {
  if (session.previewing) { ElMessage.info('静态预览不会连接服务器'); return }
  await session.action(() => chat.ask())
  if (chat.conversationId && String(route.params.id) !== String(chat.conversationId)) router.replace(`${prefix.value}/conversations/${chat.conversationId}`)
}

onBeforeUnmount(() => {
  chat.stop()
  chat.discardDraft()
})
</script>

<template>
  <div class="chat-layout fill">
    <section class="card">
      <el-button type="primary" style="width:100%;margin-bottom:18px" @click="createConversation"><i class="fa-solid fa-plus" aria-hidden="true"></i>新建会话</el-button>
      <div class="records">
      <div v-if="chat.drafting" class="conversation-row" :class="{ active: !chat.conversationId }">
        <button class="conversation-button" :disabled="chat.sending" @click="resumeDraft">新的会话</button>
      </div>
      <div v-for="conversation in catalog.lists.conversations" :key="conversation.id" class="conversation-row" :class="{ active: chat.conversationId === conversation.id }">
        <button class="conversation-button" :disabled="chat.sending" @click="selectConversation(conversation)">{{ conversation.title }}</button>
        <el-button class="conversation-delete" text type="danger" :disabled="chat.sending" aria-label="删除" title="删除" @click="removeConversation(conversation)"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></el-button>
      </div>
      </div>
    </section>
    <section class="card">
      <div class="row spread">
        <div class="thread-agent">
          <span class="muted">学习助手</span>
          <el-select :model-value="chat.agentId" :disabled="agentLocked" placeholder="选择学习助手" :title="started ? '对话开始后不能更换学习助手' : undefined" @change="chooseAgent">
            <el-option v-for="agent in switchAgents" :key="agent.id" :label="agent.name" :value="agent.id" :disabled="!agent.enabled" />
          </el-select>
        </div>
        <span class="badge">本班材料范围</span>
      </div>
      <p v-if="started" class="muted">对话开始后不能更换学习助手。</p>
      <div class="messages">
        <div v-if="!chat.chatRows.length" class="empty">可以询问讲义内容、查看当前作业或回顾自己的错题。<template v-if="chat.drafting">提出问题后才会保存这段对话。</template></div>
        <div v-for="(message, index) in chat.chatRows" :key="index" class="message" :class="message.role">
          <strong>{{ message.role === 'user' ? '你' : '学习助手' }}{{ message.skill ? ' · ' + message.skill : '' }}</strong>
          <div v-if="message.role === 'assistant'" class="message-body" v-html="renderAssistant(message.content)"></div>
          <div v-else class="message-body">{{ message.content }}</div>
          <div v-if="message.citations?.length" class="citations"><button v-for="citation in message.citations" :key="citation.id" class="citation" @click="chat.snapshot = citation">[{{ citation.id }}] {{ citation.title }} · v{{ citation.version }}</button></div>
          <p v-if="message.gap_id" class="muted">知识缺口编号 {{ message.gap_id }}</p>
        </div>
      </div>
      <details v-if="chat.toolEvents.length"><summary class="muted">查看本轮工具执行（{{ chat.toolEvents.length }}）</summary><pre class="pre">{{ JSON.stringify(chat.toolEvents, null, 2) }}</pre></details>
      <form class="chat-form" @submit.prevent="ask">
        <el-input v-model="chat.question" type="textarea" :rows="3" maxlength="4000" placeholder="输入问题，回答将逐段显示…" :disabled="chat.sending" />
        <div class="row spread" style="margin-top:12px"><span class="muted">资料不足时会提示并登记，不编造出处</span><el-button type="primary" native-type="submit" :loading="chat.sending"><i class="fa-solid fa-paper-plane" aria-hidden="true"></i>发送</el-button></div>
      </form>
    </section>
  </div>
  <el-dialog :model-value="!!chat.snapshot" :title="(chat.snapshot?.title || '引用') + ' · 引用快照'" width="680px" @close="chat.snapshot = null">
    <p class="muted">版本 {{ chat.snapshot?.version }} · 原文位置 {{ chat.snapshot?.start }}–{{ chat.snapshot?.end }}</p>
    <pre class="pre">{{ chat.snapshot?.content }}</pre>
    <p class="muted">此处保留回答生成时的材料片段，讲义更新后仍可核对。</p>
    <template #footer>
      <el-button @click="chat.snapshot = null">关闭</el-button>
    </template>
  </el-dialog>
</template>
