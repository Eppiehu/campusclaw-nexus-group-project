<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useSession } from '../stores/session'
import type { Row } from '../format'
const session = useSession()
const rows = ref<Row[]>([])
const servers = ref<Row[]>([])
const name = ref('')
const server = ref('')
const emit = defineEmits(['changed'])
async function load() {
  if (session.previewing) return
  rows.value = await api('/mcp/connections')
  servers.value = await api('/mcp/servers')
}
async function create() {
  await session.action(async () => {
    await api('/mcp/connections', 'POST', { name: name.value, server_key: server.value })
    name.value = ''; await load(); emit('changed')
  })
}
async function test(row: Row) {
  await session.action(async () => {
    try { await api(`/mcp/connections/${row.id}/test`, 'POST') }
    finally { await load(); emit('changed') }
  })
}
async function toggle(row: Row) {
  await session.action(async () => {
    await api(`/mcp/connections/${row.id}`, 'PATCH', { enabled: !row.enabled })
    await load(); emit('changed')
  })
}
onMounted(() => session.action(load))
</script>
<template>
  <section class="card">
    <h3>MCP 连接</h3>
    <p class="muted">选择本班获准的服务器；测试成功后，在应用编辑页勾选工具。密钥由管理员配置。</p>
    <div class="fields">
      <el-input v-model="name" aria-label="MCP连接名称" placeholder="连接名称" maxlength="100" />
      <el-select v-model="server" aria-label="MCP服务器" placeholder="选择已批准服务器"><el-option v-for="s in servers" :key="s.key" :value="s.key" :label="s.key" /></el-select>
    </div>
    <el-button :disabled="!name.trim() || !server || session.previewing" :loading="session.busy" @click="create">登记连接</el-button>
    <p v-if="!servers.length" class="muted">暂无本班获准的服务器，请联系管理员登记。</p>
    <div v-for="row in rows" :key="row.id" class="list-item">
      <b>{{ row.name }}</b> · {{ row.server_key }} · {{ !row.enabled ? '已停用' : row.state === 'ready' ? '测试通过' : row.state === 'failed' ? '测试失败，请检查配置后重试' : '需要测试' }}
      <el-button :disabled="!row.enabled" :loading="session.busy" @click="test(row)">测试连接</el-button>
      <el-button @click="toggle(row)">{{ row.enabled ? '停用' : '启用' }}</el-button>
      <details v-for="tool in row.tools" :key="tool.binding"><summary>{{ tool.name }}：{{ tool.description }}</summary><pre>{{ JSON.stringify(tool.parameters, null, 2) }}</pre></details>
    </div>
  </section>
</template>
