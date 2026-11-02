<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import Subhead from '../components/Subhead.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const missing = ref(false)
const ready = ref(false)
const isNew = computed(() => route.path.endsWith('/templates/new'))
const templateId = computed(() => isNew.value ? 0 : Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/apps')) : '')
const form = reactive({ name: '', content: '' })

function back() {
  router.push({ path: `${prefix.value}/apps` })
}

async function load() {
  ready.value = false
  missing.value = false
  if (isNew.value) {
    Object.assign(form, { name: '', content: '' })
    ready.value = true
    return
  }
  if (!templateId.value) { missing.value = true; ready.value = true; return }
  if (session.previewing) {
    const row = catalog.lists.templates.find(item => item.id === templateId.value)
    missing.value = !row
    if (row) Object.assign(form, { name: row.name || '', content: row.content || '' })
    ready.value = true
    return
  }
  const row = await session.action(async () => {
    await catalog.load()
    return catalog.lists.templates.find(item => item.id === templateId.value)
  })
  ready.value = true
  if (!row) { missing.value = true; return }
  Object.assign(form, { name: row.name || '', content: row.content || '' })
}

watch(() => route.fullPath, () => { load() }, { immediate: true })

async function save() {
  const saved = await session.action(async () => {
    const result = await api(isNew.value ? '/templates' : `/templates/${templateId.value}`, isNew.value ? 'POST' : 'PATCH', { name: form.name, content: form.content })
    await catalog.load()
    return result
  })
  if (!saved) return
  ElMessage.success('模板已保存')
  back()
}

async function remove() {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后模板不能恢复，已选用它的应用会改为不使用模板。', '删除模板', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/templates/${templateId.value}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) { ElMessage.success('模板已删除'); back() }
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="back">返回模板列表</Subhead>
    <div class="records">
    <p v-if="missing">这个模板当前不可编辑。</p>
    <template v-else>
      <label for="template-name">名称</label>
      <el-input id="template-name" v-model="form.name" maxlength="100" />
      <label for="template-content">模板正文</label>
      <el-input id="template-content" v-model="form.content" type="textarea" :rows="8" maxlength="4000" />
      <div class="row" style="margin-top:20px">
        <el-button type="primary" :loading="session.busy" :disabled="!ready" @click="save">保存模板</el-button>
        <el-button v-if="!isNew" type="danger" plain :disabled="!ready" @click="remove">删除</el-button>
        <el-button @click="back">取消</el-button>
      </div>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
