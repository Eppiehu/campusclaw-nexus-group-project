<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import FileDrop from '../components/FileDrop.vue'
import ChunkStrategy from '../components/ChunkStrategy.vue'
import { appendChunkFields, defaultChunkForm, type ChunkForm } from '../chunkForm'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const materialFile = ref<File>()
const materialTitle = ref('')
const replaceId = ref<number | null>(null)
const agentIds = ref<number[]>([])
const step = ref(1)
const dialogOpen = ref(false)
const chunk = ref<ChunkForm>(defaultChunkForm())
const showUpload = computed(() => session.teacher || route.path.endsWith('/materials/new'))
const needsScope = computed(() => session.teacher && replaceId.value == null && step.value === 1)

watch(materialFile, file => {
  if (!file || dialogOpen.value) return
  chunk.value = defaultChunkForm()
  materialTitle.value = ''
  replaceId.value = null
  agentIds.value = []
  step.value = 1
  dialogOpen.value = true
})

function closeDialog() {
  dialogOpen.value = false
  materialFile.value = undefined
  agentIds.value = []
  step.value = 1
}

async function confirmUpload() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); closeDialog(); return }
  const file = materialFile.value
  if (!file) return
  const supplied = materialTitle.value.trim()
  const replacing = replaceId.value
  const chosen = replacing ? [] : [...agentIds.value]
  const created = await session.action(async () => {
    const form = new FormData()
    form.append('file', file)
    form.append('title', materialTitle.value)
    appendChunkFields(form, chunk.value)
    const result = await api(replacing ? `/materials/${replacing}/versions` : '/materials', 'POST', form)
    if (!replacing && result.id) {
      for (const agentId of chosen) {
        const agent = catalog.lists.agents.find(item => item.id === agentId)
        if (!agent) continue
        const materialIds = [...new Set([...(agent.material_ids || []), result.id])]
        await api(`/agents/${agentId}`, 'PATCH', { material_ids: materialIds })
      }
    }
    await catalog.load()
    return result
  })
  if (!created) return
  closeDialog()
  const saved = !replacing && !supplied && created.title ? `已根据讲义生成标题「${created.title}」` : '已提交索引任务，完成后生效'
  ElMessage.success(chosen.length ? `${saved}，并加入所选应用的讲义范围` : saved)
}

function openMaterial(row: Row) {
  const prefix = route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/materials')) : ''
  router.push(`${prefix}/materials/${row.id}`)
}

function needsPublish(row: Row) {
  const latest = row.versions?.[0]
  if (!latest || latest.state === 'indexing') return false
  return !row.active_version_id || latest.id !== row.active_version_id
}

async function publish(row: Row) {
  const done = await session.action(async () => {
    await api(`/materials/${row.id}/publish`, 'POST')
    await catalog.load()
    return true
  })
  if (done) ElMessage.success('已重新发布，索引完成后对学生和问答生效')
}

async function withdraw(row: Row) {
  await session.action(async () => {
    await ElMessageBox.confirm('撤回后不能再被问答引用，学生也不能查看。教师仍可查看和编辑正文。', '撤回讲义', { confirmButtonText: '确定', cancelButtonText: '取消' })
    await api(`/materials/${row.id}/withdraw`, 'POST')
    await catalog.load()
  })
}

async function remove(row: Row) {
  await session.action(async () => {
    await ElMessageBox.confirm('删除后讲义不能恢复，后续问答也不会再引用。', '删除讲义', { confirmButtonText: '确定', cancelButtonText: '取消' })
    await api(`/materials/${row.id}`, 'DELETE')
    await catalog.load()
  })
}
</script>

<template>
  <section v-if="showUpload" class="card">
    <h2><i class="fa-solid fa-file-arrow-up" aria-hidden="true"></i>上传讲义</h2>
    <FileDrop v-model="materialFile" accept=".txt,.md,.pdf" label="选择讲义文件" hint="选择后填写标题和切片方式；新增时再选择要加入的应用讲义范围" />
    <p v-if="session.teacher" class="muted" style="margin-top:12px">支持 TXT、Markdown 和文字型 PDF。未填写标题时，根据讲义内容概括一个不超过20字的标题；正文过长时先截断再概括。更新期间沿用已生效版本，索引完成后再切换。</p>
    <p v-else class="muted" style="margin-top:12px">是否允许上传由服务端按当前身份判断。学生提交会收到服务端的拒绝说明。</p>
  </section>
  <section class="card fill">
    <div class="records">
    <div v-if="!catalog.lists.materials.length" class="empty">暂无可用讲义</div>
    <div v-for="material in catalog.lists.materials" :key="material.id" class="list-item assignment-item">
      <button type="button" class="assignment-open" @click="openMaterial(material)">
        <h3>{{ material.title }}</h3>
        <div v-for="version in material.versions" :key="version.id" class="muted">v{{ version.number }} · <span class="badge">{{ state(version.state) }}</span> · {{ date(version.created_at) }}<span v-if="version.error"> · {{ version.error }}</span></div>
      </button>
      <div v-if="session.teacher" class="assignment-actions">
        <el-button v-if="needsPublish(material)" @click="publish(material)">重新发布</el-button>
        <el-button v-if="material.active_version_id" @click="withdraw(material)">撤回</el-button>
        <el-button type="danger" plain @click="remove(material)">删除</el-button>
      </div>
    </div>
    </div>
  </section>
  <el-dialog :model-value="dialogOpen" :title="step === 2 ? '加入应用讲义范围' : '上传讲义'" width="680px" :close-on-click-modal="false" @close="closeDialog">
    <template v-if="step === 1">
      <p class="muted">即将上传「{{ materialFile?.name }}」。填写标题和切片方式后，新增讲义会再选择要加入的应用。</p>
      <label class="field-title" for="material-title">材料标题</label>
      <el-input id="material-title" v-model="materialTitle" placeholder="留空则概括不超过20字的标题" />
      <div v-if="session.teacher"><label class="field-title" for="material-replace">更新对象（留空为新增）</label><el-select id="material-replace" v-model="replaceId" clearable placeholder="新增材料"><el-option v-for="material in catalog.lists.materials" :key="material.id" :value="material.id" :label="material.title" /></el-select></div>
      <div class="upload-strategy">
        <h3 class="strategy-heading">切片策略</h3>
        <div class="strategy-scroll">
          <ChunkStrategy v-model="chunk" />
        </div>
      </div>
    </template>
    <template v-else>
      <p class="muted">选择这份讲义要加入哪些应用的讲义范围。可以多选；不选则只保存讲义，不加入任何应用。</p>
      <label class="field-title" for="material-agents">应用</label>
      <el-select id="material-agents" v-model="agentIds" multiple placeholder="选择应用">
        <el-option v-for="agent in catalog.lists.agents" :key="agent.id" :value="agent.id" :label="agent.name" />
      </el-select>
      <p v-if="!catalog.lists.agents.length" class="muted">当前班级还没有应用。</p>
    </template>
    <template #footer>
      <el-button v-if="step === 2" @click="step = 1" :disabled="session.busy">上一步</el-button>
      <el-button v-else @click="closeDialog" :disabled="session.busy">取消</el-button>
      <el-button v-if="needsScope" type="primary" @click="step = 2">下一步</el-button>
      <el-button v-else type="primary" :loading="session.busy" @click="confirmUpload">确定</el-button>
    </template>
  </el-dialog>
</template>
