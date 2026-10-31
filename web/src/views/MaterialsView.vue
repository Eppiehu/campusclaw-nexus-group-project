<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, download, materialText } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const materialFile = ref<File>()
const materialTitle = ref('')
const replaceId = ref<number | null>(null)
const preview = ref<{ id: number, content: string } | null>(null)
const showUpload = computed(() => session.teacher || route.path.endsWith('/materials/new'))

function fileChange(event: Event) {
  materialFile.value = (event.target as HTMLInputElement).files?.[0]
}

async function uploadMaterial() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  await session.action(async () => {
    if (!materialFile.value) throw new Error('请选择讲义')
    const form = new FormData()
    form.append('file', materialFile.value)
    form.append('title', materialTitle.value)
    await api(replaceId.value ? `/materials/${replaceId.value}/versions` : '/materials', 'POST', form)
    await catalog.load()
    ElMessage.success('已提交索引任务，完成后生效')
  })
}

async function showPreview(row: Row) {
  if (session.previewing) {
    preview.value = preview.value?.id === row.id ? null : { id: row.id, content: row.preview_text || '' }
    return
  }
  if (preview.value?.id === row.id) {
    preview.value = null
    if (route.params.id) router.replace('/materials')
    return
  }
  const text = await session.action(async () => materialText(row.id))
  if (text === undefined) return
  preview.value = { id: row.id, content: text }
  if (String(route.params.id) !== String(row.id)) router.replace(`/materials/${row.id}`)
}

async function loadRoutePreview(id: string | string[] | undefined) {
  const numeric = Number(id)
  if (!numeric) { preview.value = null; return }
  if (preview.value?.id === numeric) return
  const text = await session.action(async () => materialText(numeric))
  if (text !== undefined) preview.value = { id: numeric, content: text }
}

watch(() => route.params.id, id => { loadRoutePreview(id) }, { immediate: true })

async function withdraw(row: Row) {
  await session.action(async () => {
    await ElMessageBox.confirm('撤回后不再用于新的检索，已有问答引用会保留。', '撤回讲义')
    await api(`/materials/${row.id}/withdraw`, 'POST')
    await catalog.load()
  })
}
</script>

<template>
  <section v-if="showUpload" class="card">
    <h2>{{ replaceId ? '更新讲义版本' : '上传讲义' }}</h2>
    <div class="fields">
      <div><label for="material-title">材料标题</label><el-input id="material-title" v-model="materialTitle" placeholder="如：第一章 分数运算" /></div>
      <div v-if="session.teacher"><label>更新对象（留空为新增）</label><el-select v-model="replaceId" clearable placeholder="新增材料"><el-option v-for="material in catalog.lists.materials" :key="material.id" :value="material.id" :label="material.title" /></el-select></div>
      <div class="full"><input type="file" accept=".txt,.md,.pdf" aria-label="选择讲义文件" @change="fileChange" /></div>
    </div>
    <el-button type="primary" style="margin-top:16px" :loading="session.busy" @click="uploadMaterial">上传并建立索引</el-button>
    <p v-if="session.teacher" class="muted" style="margin-top:12px">支持 TXT、Markdown 和文字型 PDF。更新期间沿用已生效版本，索引完成后再切换。</p>
    <p v-else class="muted" style="margin-top:12px">是否允许上传由服务端按当前身份判断。学生提交会收到服务端的拒绝说明。</p>
  </section>
  <section class="card">
    <div v-if="!catalog.lists.materials.length" class="empty">暂无可用讲义</div>
    <div v-for="material in catalog.lists.materials" :key="material.id" class="list-item">
      <div class="row spread">
        <h3>{{ material.title }}</h3>
        <div class="row">
          <el-button v-if="material.active_version_id" type="primary" plain @click="showPreview(material)">{{ preview?.id === material.id ? '收起正文' : '查看正文' }}</el-button>
          <el-button v-if="material.active_version_id" @click="session.action(() => download(material.id))">下载正文</el-button>
          <el-button v-if="session.teacher && material.active_version_id" text type="danger" @click="withdraw(material)">撤回</el-button>
        </div>
      </div>
      <div v-for="version in material.versions" :key="version.id" class="muted">v{{ version.number }} · <span class="badge">{{ state(version.state) }}</span> · {{ date(version.created_at) }}<span v-if="version.error"> · {{ version.error }}</span></div>
      <div v-if="preview?.id === material.id" class="material-preview"><p class="muted">当前生效版本的可检索正文；PDF 原始排版不在此处保留。</p><pre class="pre">{{ preview?.content }}</pre></div>
    </div>
  </section>
</template>
