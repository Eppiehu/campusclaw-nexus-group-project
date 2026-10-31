<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Row } from '../format'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import { useChat } from '../stores/chat'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const chat = useChat()

async function openFromRoute(id: string | string[] | undefined) {
  const numeric = Number(id)
  if (!numeric || chat.conversationId === numeric || session.previewing) return
  await session.action(async () => {
    const row = catalog.lists.conversations.find(item => item.id === numeric)
    await chat.open(row ? { id: Number(row.id), agent_id: row.agent_id } : { id: numeric, agent_id: chat.agentId })
  })
}

watch(() => route.params.id, id => { openFromRoute(id) }, { immediate: true })
watch(() => catalog.lists.conversations, rows => {
  const row = rows.find(item => item.id === Number(route.params.id))
  if (row) chat.agentId = row.agent_id
})

async function createConversation() {
  if (session.previewing) { ElMessage.info('静态预览不会连接服务器'); return }
  const row = await session.action(() => chat.createConversation())
  if (row) router.replace(`/conversations/${row.id}`)
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
  if (!session.error) router.push(`/conversations/${row.id}`)
}

async function ask() {
  if (session.previewing) { ElMessage.info('静态预览不会连接服务器'); return }
  await session.action(() => chat.ask())
  if (chat.conversationId && String(route.params.id) !== String(chat.conversationId)) router.replace(`/conversations/${chat.conversationId}`)
}

onBeforeUnmount(() => chat.stop())
</script>

<template>
  <div class="chat-layout">
    <section class="card">
      <label>学习助手</label>
      <el-select v-model="chat.agentId" :disabled="chat.sending">
        <el-option v-for="agent in catalog.lists.agents" :key="agent.id" :label="agent.name" :value="agent.id" />
      </el-select>
      <el-button type="primary" style="width:100%;margin:12px 0 25px" @click="createConversation">新建会话</el-button>
      <button v-for="conversation in catalog.lists.conversations" :key="conversation.id" class="conversation-button" :class="{ active: chat.conversationId === conversation.id }" :disabled="chat.sending" @click="selectConversation(conversation)">{{ conversation.title }}</button>
    </section>
    <section class="card">
      <div class="row spread"><h2>{{ catalog.lists.agents.find(agent => agent.id === chat.agentId)?.name || '选择一个学习助手' }}</h2><span class="badge">本班材料范围</span></div>
      <div class="messages">
        <div v-if="!chat.chatRows.length" class="empty">可以询问讲义内容、查看当前作业或回顾自己的错题。</div>
        <div v-for="(message, index) in chat.chatRows" :key="index" class="message" :class="message.role">
          <strong>{{ message.role === 'user' ? '你' : '学习助手' }}{{ message.skill ? ' · ' + message.skill : '' }}</strong>{{ message.content }}
          <div v-if="message.citations?.length" class="citations"><button v-for="citation in message.citations" :key="citation.id" class="citation" @click="chat.snapshot = citation">[{{ citation.id }}] {{ citation.title }} · v{{ citation.version }}</button></div>
          <p v-if="message.gap_id" class="muted">知识缺口编号 {{ message.gap_id }}</p>
        </div>
      </div>
      <details v-if="chat.toolEvents.length"><summary class="muted">查看本轮工具执行（{{ chat.toolEvents.length }}）</summary><pre class="pre">{{ JSON.stringify(chat.toolEvents, null, 2) }}</pre></details>
      <form class="chat-form" @submit.prevent="ask">
        <el-input v-model="chat.question" type="textarea" :rows="3" maxlength="4000" placeholder="输入问题，回答将逐段显示…" :disabled="chat.sending" />
        <div class="row spread" style="margin-top:12px"><span class="muted">资料不足时会提示并登记，不编造出处</span><el-button type="primary" native-type="submit" :loading="chat.sending">发送</el-button></div>
      </form>
    </section>
  </div>
  <el-dialog :model-value="!!chat.snapshot" :title="(chat.snapshot?.title || '引用') + ' · 引用快照'" width="650px" @close="chat.snapshot = null">
    <p class="muted">版本 {{ chat.snapshot?.version }} · 原文位置 {{ chat.snapshot?.start }}–{{ chat.snapshot?.end }}</p>
    <pre class="pre">{{ chat.snapshot?.content }}</pre>
    <p class="muted">此处保留回答生成时的材料片段，讲义更新后仍可核对。</p>
  </el-dialog>
</template>
