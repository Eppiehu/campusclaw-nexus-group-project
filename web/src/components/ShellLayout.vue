<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { token } from '../api'
import { applyPreview } from '../preview'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import { useChat } from '../stores/chat'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const chat = useChat()
const title = computed(() => String(route.meta.title || '工作台'))
const previewRole = computed(() => route.params.role === 'student' ? 'student' : route.params.role === 'teacher' ? 'teacher' : '')
const base = computed(() => previewRole.value ? `/preview/${previewRole.value}` : '')
const nav = computed(() => [
  { to: base.value || '/', label: '工作台' },
  { to: `${base.value}/conversations`, label: '学习助手' },
  { to: `${base.value}/materials`, label: '讲义知识库' },
  ...(session.teacher ? [{ to: `${base.value}/apps`, label: '应用与技能' }, { to: `${base.value}/gaps`, label: '知识缺口' }] : []),
  { to: `${base.value}/assignments`, label: '作业与批改' },
  { to: `${base.value}/reports`, label: '学情周报' },
  ...(session.teacher ? [{ to: `${base.value}/jobs`, label: '后台任务' }, { to: `${base.value}/audit`, label: '调用记录' }] : []),
])
const live = new Set(['materials', 'material', 'material-new', 'assignments', 'reports', 'jobs', 'gaps'])

function active(to: string) {
  if (to === '/' || to === base.value) return route.path === to
  return route.path === to || route.path.startsWith(to + '/')
}

async function boot() {
  if (previewRole.value) { applyPreview(previewRole.value); return }
  if (!token()) { router.replace('/login'); return }
  if (session.user) return
  try { await session.restore() }
  catch (error: any) {
    localStorage.removeItem('nexus-token')
    session.user = null
    session.error = error.message || '登录状态已失效'
    router.replace('/login')
    return
  }
  try { await catalog.load() }
  catch (error: any) { session.error = error.message }
}

function refresh() {
  if (previewRole.value) { applyPreview(previewRole.value); return }
  session.action(catalog.load)
}

async function logout() {
  if (session.previewing) {
    session.previewing = false
    session.user = null
    catalog.reset()
    chat.reset()
    router.replace('/preview')
    return
  }
  const ok = await session.action(() => session.logout())
  if (!ok && session.user) return
  catalog.reset()
  chat.reset()
  router.replace('/login')
}

let refreshTimer: ReturnType<typeof setInterval>
onMounted(() => {
  boot()
  refreshTimer = setInterval(() => {
    if (!session.previewing && session.user && !session.busy && live.has(String(route.name))) catalog.load().catch(() => {})
  }, 7000)
})
onBeforeUnmount(() => clearInterval(refreshTimer))
</script>

<template>
  <div v-if="!session.user" class="main"><p class="muted">正在恢复登录状态…</p></div>
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand">CampusClaw<small>NEXUS · 教学空间</small></div>
      <nav>
        <router-link v-for="item in nav" :key="item.to" :to="item.to" :class="{ active: active(item.to) }">{{ item.label }}</router-link>
      </nav>
      <div class="account"><b>{{ session.user.username }}</b><br>{{ session.user.class_id }} 班 · {{ session.teacher ? '教师' : '学生' }}<br><el-button text style="color:#9bbebd;padding-left:0" @click="logout">退出登录</el-button></div>
    </aside>
    <main class="main">
      <header class="topline">
        <div><div class="eyebrow">{{ session.user.class_id }} 班教学空间</div><h1 style="margin-bottom:0">{{ title }}</h1></div>
        <div class="row">
          <el-button :loading="session.busy" @click="refresh">刷新</el-button>
          <el-button @click="logout">退出登录</el-button>
        </div>
      </header>
      <div v-if="session.previewing" class="preview-banner"><span>静态预览：虚构数据，不会访问服务器。</span><span><router-link to="/preview/teacher">教师</router-link> · <router-link to="/preview/student">学生</router-link></span></div>
      <div v-if="session.error" class="error" role="alert">{{ session.error }}</div>
      <RouterView />
      <p class="footer-note">CampusClaw Nexus · {{ session.user.class_id }} 班 · {{ session.teacher ? '教师工作空间' : '学生学习空间' }}</p>
    </main>
  </div>
</template>
