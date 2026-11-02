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
const skillId = computed(() => Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/apps')) : '')
const form = reactive({ name: '', description: '', body: '' })

function back() {
  router.push({ path: `${prefix.value}/apps`, query: { tab: 'skills' } })
}

async function load() {
  ready.value = false
  missing.value = false
  if (!skillId.value) { missing.value = true; ready.value = true; return }
  if (session.previewing) {
    const row = catalog.lists.skills.find(item => item.id === skillId.value)
    missing.value = !row
    if (row) Object.assign(form, { name: row.name || '', description: row.description || '', body: row.body || '' })
    ready.value = true
    return
  }
  const row = await session.action(async () => {
    await catalog.load()
    return catalog.lists.skills.find(item => item.id === skillId.value)
  })
  ready.value = true
  if (!row) { missing.value = true; return }
  Object.assign(form, { name: row.name || '', description: row.description || '', body: row.body || '' })
}

watch(skillId, () => { load() }, { immediate: true })

async function save() {
  const saved = await session.action(async () => {
    const result = await api(`/skills/${skillId.value}`, 'PATCH', { name: form.name, description: form.description, body: form.body })
    await catalog.load()
    return result
  })
  if (!saved) return
  ElMessage.success('技能已更新')
  back()
}

async function remove() {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后技能不能恢复，已绑定的应用也会去掉这项技能。', '删除技能', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/skills/${skillId.value}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) { ElMessage.success('技能已删除'); back() }
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="back">返回技能列表</Subhead>
    <div class="records">
    <p v-if="missing">这个技能当前不可编辑。</p>
    <template v-else>
      <label for="skill-name">技能标题</label>
      <el-input id="skill-name" v-model="form.name" maxlength="64" />
      <label for="skill-condition">适用条件</label>
      <el-input id="skill-condition" v-model="form.description" type="textarea" :rows="3" maxlength="2000" />
      <label for="skill-body">正文</label>
      <el-input id="skill-body" v-model="form.body" type="textarea" :rows="8" maxlength="2000" />
      <div class="row" style="margin-top:20px">
        <el-button type="primary" :loading="session.busy" :disabled="!ready" @click="save">保存技能</el-button>
        <el-button @click="back">取消</el-button>
        <el-button type="danger" plain :disabled="!ready" @click="remove">删除</el-button>
      </div>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
