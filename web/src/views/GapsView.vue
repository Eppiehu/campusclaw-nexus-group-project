<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, materialText } from '../api'
import { state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import FileDrop from '../components/FileDrop.vue'
import ChunkStrategy from '../components/ChunkStrategy.vue'
import { appendChunkFields, chunkFormFrom, chunkPayload, defaultChunkForm, type ChunkForm } from '../chunkForm'

const session = useSession()
const catalog = useCatalog()
const gapId = ref(0)
const supplementFile = ref<File>()
const supplementTitle = ref('')
const draft = ref('')
const editingId = ref(0)
const dialogOpen = ref(false)
const mode = ref<'choose' | 'upload' | 'edit'>('choose')
const chunk = ref<ChunkForm>(defaultChunkForm())
const dialogTitle = computed(() => mode.value === 'edit' ? '编辑已有讲义' : mode.value === 'upload' ? '上传新讲义' : '补充材料')

async function removeGap(row: Row) {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后这条知识缺口不能恢复。已经补充的讲义仍保留在知识库。', '删除知识缺口', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/gaps/${row.id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) ElMessage.success('知识缺口已删除')
}

async function reviewGap(row: Row, decision: string) {
  await session.action(async () => { await api(`/gaps/${row.id}/review`, 'POST', { decision, note: '' }); await catalog.load() })
}

function beginSupplement(id: number) {
  gapId.value = id
  supplementFile.value = undefined
  supplementTitle.value = ''
  draft.value = ''
  editingId.value = 0
  mode.value = 'choose'
  chunk.value = defaultChunkForm()
  dialogOpen.value = true
}

watch(supplementFile, file => {
  if (!file || mode.value === 'edit') return
  editingId.value = 0
  draft.value = ''
  supplementTitle.value = ''
  chunk.value = defaultChunkForm()
  mode.value = 'upload'
})

function backToChoice() {
  supplementFile.value = undefined
  supplementTitle.value = ''
  draft.value = ''
  editingId.value = 0
  chunk.value = defaultChunkForm()
  mode.value = 'choose'
}

function closeDialog() {
  dialogOpen.value = false
  backToChoice()
  gapId.value = 0
}

async function editExisting(material: Row) {
  supplementFile.value = undefined
  editingId.value = Number(material.id)
  supplementTitle.value = String(material.title || '')
  const latest = material.versions?.[0] as Row | undefined
  chunk.value = chunkFormFrom(latest?.chunk_options as Record<string, unknown> | undefined)
  if (session.previewing) { draft.value = String(material.preview_text || ''); mode.value = 'edit'; return }
  const text = await session.action(() => materialText(Number(material.id)))
  if (text === undefined) { editingId.value = 0; draft.value = ''; return }
  draft.value = text
  mode.value = 'edit'
}

async function confirmSupplement() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); closeDialog(); return }
  const file = supplementFile.value
  const identifier = gapId.value
  const materialId = editingId.value
  if (!identifier || (!file && !materialId)) { ElMessage.warning('请上传新文件，或选择已有讲义进行编辑'); return }
  const supplied = supplementTitle.value.trim()
  const created = await session.action(async () => {
    const result = file
      ? await api(`/gaps/${identifier}/supplement`, 'POST', (() => { const form = new FormData(); form.append('file', file); form.append('title', supplementTitle.value); appendChunkFields(form, chunk.value); return form })())
      : await api(`/gaps/${identifier}/supplement`, 'POST', { material_id: materialId, title: supplementTitle.value, content: draft.value, ...chunkPayload(chunk.value) })
    await catalog.load()
    return result
  })
  if (!created) return
  closeDialog()
  ElMessage.success(!file && supplied ? '已保存已有讲义，正在重建索引' : !supplied && created.title ? `已根据讲义生成标题「${created.title}」` : '补充材料正在索引')
}
</script>

<template>
  <TeacherGate probe="/gaps">
    <p class="muted">学生提问未获得足够材料依据时，系统会登记候选缺口。同班相近问题合并计数，补充材料完成索引并命中原问题后才标记“已补入”。</p>
    <div class="fill records">
    <section v-for="gap in catalog.lists.gaps" :key="gap.id" class="card gap-item">
      <div class="gap-body">
        <h3>{{ gap.question }}</h3>
        <p class="muted"><span class="badge">{{ state(gap.state) }}</span> · 提问热度 {{ gap.heat }}</p>
        <p v-if="gap.note" class="muted">{{ gap.note }}</p>
        <details v-if="gap.state === 'filled'"><summary class="muted">查看回补前后检索结果</summary><pre class="pre">{{ JSON.stringify({ before: gap.before_hits, after: gap.after_hits }, null, 2) }}</pre></details>
      </div>
      <div class="gap-actions">
        <el-button v-if="['pending', 'index_failed'].includes(gap.state)" type="primary" @click="reviewGap(gap, 'approve')">确认缺口</el-button>
        <el-button v-if="gap.state === 'rejected'" type="primary" @click="reviewGap(gap, 'approve')">改为可补充</el-button>
        <el-button v-if="['pending', 'approved', 'indexing', 'filled', 'index_failed'].includes(gap.state)" @click="reviewGap(gap, 'reject')">驳回</el-button>
        <el-button v-if="['approved', 'index_failed'].includes(gap.state)" @click="beginSupplement(gap.id)">补充材料</el-button>
        <el-button type="danger" plain @click="removeGap(gap)">删除</el-button>
      </div>
    </section>
    <div v-if="!catalog.lists.gaps.length" class="card empty">暂时没有候选缺口</div>
    </div>
    <el-dialog :model-value="dialogOpen" class="supplement-dialog" :title="dialogTitle" width="760px" :close-on-click-modal="false" @close="closeDialog">
      <template v-if="mode === 'choose'">
        <FileDrop v-model="supplementFile" accept=".txt,.md,.pdf" label="选择补充讲义" hint="选择后进入上传界面" />
        <p class="muted">上传一份新讲义，或从下面选择已有讲义进入编辑。两种方式只能选一种。</p>
        <h3 class="strategy-heading existing-heading">已有讲义</h3>
        <div class="existing-files">
          <div v-for="material in catalog.lists.materials" :key="material.id" class="list-item row spread">
            <b>{{ material.title }}</b>
            <el-button @click="editExisting(material)">编辑</el-button>
          </div>
          <p v-if="!catalog.lists.materials.length" class="muted">还没有可编辑的讲义。</p>
        </div>
      </template>
      <template v-else-if="mode === 'upload'">
        <p class="muted">即将上传「{{ supplementFile?.name }}」。填写标题和切片方式后，点击确定才会上传。</p>
        <label for="gap-material-title">材料标题</label>
        <el-input id="gap-material-title" v-model="supplementTitle" placeholder="留空则概括不超过20字的标题" />
        <div class="upload-strategy">
          <h3 class="strategy-heading">切片策略</h3>
          <div class="strategy-scroll"><ChunkStrategy v-model="chunk" /></div>
        </div>
      </template>
      <template v-else>
        <label for="gap-existing-title">材料标题</label>
        <el-input id="gap-existing-title" v-model="supplementTitle" maxlength="200" />
        <label for="gap-existing-body">正文</label>
        <el-input id="gap-existing-body" v-model="draft" type="textarea" :rows="12" />
        <div class="upload-strategy">
          <h3 class="strategy-heading">切片策略</h3>
          <div class="strategy-scroll"><ChunkStrategy v-model="chunk" /></div>
        </div>
      </template>
      <template #footer>
        <el-button v-if="mode !== 'choose'" @click="backToChoice" :disabled="session.busy">返回</el-button>
        <el-button @click="closeDialog" :disabled="session.busy">取消</el-button>
        <el-button v-if="mode !== 'choose'" type="primary" :loading="session.busy" @click="confirmSupplement">确定</el-button>
      </template>
    </el-dialog>
  </TeacherGate>
</template>
