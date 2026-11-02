<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
const skill = computed(() => catalog.lists.skills.find(item => item.id === skillId.value))

function back() {
  router.push({ path: `${prefix.value}/apps`, query: { tab: 'skills' } })
}

function edit() {
  router.push(`${prefix.value}/apps/skills/${skillId.value}/edit`)
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

async function load() {
  ready.value = false
  missing.value = false
  if (!skillId.value) { missing.value = true; ready.value = true; return }
  if (session.previewing) {
    missing.value = !skill.value
    ready.value = true
    return
  }
  await session.action(() => catalog.load())
  ready.value = true
  missing.value = !catalog.lists.skills.some(item => item.id === skillId.value)
}

watch(skillId, () => { load() }, { immediate: true })
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="back">返回技能列表</Subhead>
    <div class="records">
    <p v-if="!ready" class="muted">正在读取技能…</p>
    <p v-else-if="missing">这个技能当前不可查看。</p>
    <template v-else>
      <div class="row spread">
        <h2>{{ skill?.name || '技能正文' }}</h2>
        <div class="row">
          <el-button type="primary" plain @click="edit">编辑</el-button>
          <el-button type="danger" plain @click="remove">删除</el-button>
        </div>
      </div>
      <p class="muted">适用条件</p>
      <p>{{ skill?.description }}</p>
      <h3>正文</h3>
      <pre class="pre material-body">{{ skill?.body }}</pre>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
