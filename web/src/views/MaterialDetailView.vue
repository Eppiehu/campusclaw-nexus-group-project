<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, download, materialText } from '../api'
import { state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import ChunkStrategy from '../components/ChunkStrategy.vue'
import Subhead from '../components/Subhead.vue'
import { chunkFormFrom, chunkPayload, type ChunkForm } from '../chunkForm'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const body = ref('')
const draft = ref('')
const chunk = ref<ChunkForm>(chunkFormFrom(null))
const editing = ref(false)
const missing = ref(false)
const ready = ref(false)
const materialId = computed(() => Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/materials')) : '')
const current = computed(() => catalog.lists.materials.find(item => item.id === materialId.value) as Row | undefined)
const active = computed(() => Boolean(current.value?.active_version_id))
const latest = computed(() => current.value?.versions?.[0] as Row | undefined)
const canPublish = computed(() => {
  if (!latest.value || latest.value.state === 'indexing') return false
  return !current.value?.active_version_id || latest.value.id !== current.value.active_version_id
})

function back() {
  router.push(`${prefix.value}/materials`)
}

async function load() {
  editing.value = false
  missing.value = false
  ready.value = false
  const id = materialId.value
  if (!id) { missing.value = true; return }
  if (session.previewing) {
    body.value = String(current.value?.preview_text || '')
    missing.value = !current.value
    ready.value = true
    return
  }
  const text = await session.action(async () => {
    await catalog.load()
    return materialText(id)
  })
  ready.value = true
  if (text === undefined) { missing.value = true; body.value = ''; return }
  body.value = text
}

watch(materialId, () => { load() }, { immediate: true })

function startEdit() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  draft.value = body.value
  chunk.value = chunkFormFrom(latest.value?.chunk_options as Record<string, unknown> | undefined)
  editing.value = true
}

async function save() {
  const saved = await session.action(async () => {
    const result = await api(`/materials/${materialId.value}/content`, 'PUT', { content: draft.value, ...chunkPayload(chunk.value) })
    await catalog.load()
    return result
  })
  if (!saved) return
  editing.value = false
  ElMessage.success('已保存，正在按所选分段策略重建索引，完成后生效')
  await load()
}

async function publish() {
  const done = await session.action(async () => {
    await api(`/materials/${materialId.value}/publish`, 'POST')
    await catalog.load()
    return true
  })
  if (done) {
    ElMessage.success('已重新发布，索引完成后对学生和问答生效')
    await load()
  }
}

async function withdraw() {
  await session.action(async () => {
    await ElMessageBox.confirm('撤回后不能再被问答引用，学生也不能查看。教师仍可在此查看和编辑正文。', '撤回讲义', { confirmButtonText: '确定', cancelButtonText: '取消' })
    await api(`/materials/${materialId.value}/withdraw`, 'POST')
    await catalog.load()
  })
}

async function remove() {
  const removed = await session.action(async () => {
    await ElMessageBox.confirm('删除后讲义不能恢复，后续问答也不会再引用。', '删除讲义', { confirmButtonText: '确定', cancelButtonText: '取消' })
    await api(`/materials/${materialId.value}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) back()
}
</script>

<template>
  <section class="card fill">
    <Subhead @back="back">返回讲义库</Subhead>
    <div class="records">
    <p v-if="missing">这份讲义当前不可查看。</p>
    <template v-else>
    <div class="row spread">
      <div>
        <h2>{{ current?.title || '讲义正文' }}</h2>
        <p v-if="latest" class="muted">v{{ latest.number }} · <span class="badge">{{ state(String(latest.state || '')) }}</span></p>
      </div>
      <div class="row">
        <el-button v-if="session.teacher && !editing" type="primary" plain @click="startEdit">编辑正文</el-button>
        <el-button v-if="editing" type="primary" :loading="session.busy" @click="save">保存正文</el-button>
        <el-button v-if="editing" @click="editing = false">取消</el-button>
        <el-button @click="session.action(() => download(materialId))">下载正文</el-button>
        <el-button v-if="session.teacher && canPublish" :disabled="!ready || session.previewing" @click="publish">重新发布</el-button>
        <el-button v-if="session.teacher && active" :disabled="!ready || session.previewing" @click="withdraw">撤回</el-button>
        <el-button v-if="session.teacher" type="danger" plain :disabled="session.previewing" @click="remove">删除</el-button>
      </div>
    </div>
    <p v-if="ready && session.teacher && !active && latest?.state === 'withdrawn'" class="muted">已撤回：学生不能查看，后续问答也不会引用。保存编辑会按所选策略重建索引，完成后重新生效。</p>
    <p v-else-if="ready && session.teacher && latest?.state === 'indexing'" class="muted">正在根据当前正文重新建立索引，完成后对学生和问答生效。</p>
    <template v-if="editing">
      <el-input v-model="draft" type="textarea" :rows="18" />
      <p class="muted strategy-label">分段策略。保存后按这里的选择重建索引。</p>
      <ChunkStrategy v-model="chunk" />
    </template>
    <pre v-else class="pre material-body">{{ body }}</pre>
    </template>
    </div>
  </section>
</template>
