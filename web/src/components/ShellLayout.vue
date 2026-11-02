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
const routeName = computed(() => String(route.name || '').replace(/^preview-/, ''))
const sectionTitles: Record<string, string> = {
  material: '讲义知识库',
  'template-new': '应用与技能', template: '应用与技能', 'skill-edit': '应用与技能', skill: '应用与技能', 'app-new': '应用与技能', app: '应用与技能',
  'assignment-new': '作业与批改', 'assignment-edit': '作业与批改', assignment: '作业与批改', 'assignment-submission': '作业与批改', 'assignment-answer': '作业与批改',
}
const title = computed(() => sectionTitles[routeName.value] || String(route.meta.title || '工作台'))
const previewRole = computed(() => route.params.role === 'student' ? 'student' : route.params.role === 'teacher' ? 'teacher' : '')
const base = computed(() => previewRole.value ? `/preview/${previewRole.value}` : '')
const titleIcons: Record<string, string> = {
  overview: 'fa-house', conversations: 'fa-comments', conversation: 'fa-comments',
  materials: 'fa-book-open', 'material-new': 'fa-book-open', material: 'fa-book-open',
  apps: 'fa-puzzle-piece', 'template-new': 'fa-file-lines', template: 'fa-file-lines',
  'skill-edit': 'fa-pen', skill: 'fa-wand-magic-sparkles', 'app-new': 'fa-puzzle-piece', app: 'fa-puzzle-piece',
  gaps: 'fa-lightbulb', assignments: 'fa-clipboard-check', 'assignment-new': 'fa-clipboard-check',
  'assignment-edit': 'fa-clipboard-check', assignment: 'fa-clipboard-check', 'assignment-submission': 'fa-pen-to-square', 'assignment-answer': 'fa-pen-to-square',
  reports: 'fa-chart-column', jobs: 'fa-gears', audit: 'fa-clock-rotate-left',
}
const sectionIcons: Record<string, string> = {
  material: 'fa-book-open',
  'template-new': 'fa-puzzle-piece', template: 'fa-puzzle-piece', 'skill-edit': 'fa-puzzle-piece', skill: 'fa-puzzle-piece', 'app-new': 'fa-puzzle-piece', app: 'fa-puzzle-piece',
  'assignment-new': 'fa-clipboard-check', 'assignment-edit': 'fa-clipboard-check', assignment: 'fa-clipboard-check', 'assignment-submission': 'fa-clipboard-check', 'assignment-answer': 'fa-clipboard-check',
}
const titleIcon = computed(() => sectionIcons[routeName.value] || titleIcons[routeName.value] || 'fa-graduation-cap')
const nav = computed(() => [
  { to: base.value || '/', label: '工作台', icon: 'fa-house' },
  { to: `${base.value}/conversations`, label: '学习助手', icon: 'fa-comments' },
  { to: `${base.value}/materials`, label: '讲义知识库', icon: 'fa-book-open' },
  ...(session.teacher ? [{ to: `${base.value}/apps`, label: '应用与技能', icon: 'fa-puzzle-piece' }, { to: `${base.value}/gaps`, label: '知识缺口', icon: 'fa-lightbulb' }] : []),
  { to: `${base.value}/assignments`, label: '作业与批改', icon: 'fa-clipboard-check' },
  { to: `${base.value}/reports`, label: '学情周报', icon: 'fa-chart-column' },
  ...(session.teacher ? [{ to: `${base.value}/jobs`, label: '后台任务', icon: 'fa-gears' }, { to: `${base.value}/audit`, label: '调用记录', icon: 'fa-clock-rotate-left' }] : []),
])
const live = new Set(['materials', 'material', 'material-new', 'assignments', 'assignment', 'assignment-new', 'assignment-edit', 'assignment-submission', 'reports', 'jobs', 'gaps'])

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
      <div class="brand"><i class="fa-solid fa-graduation-cap" aria-hidden="true"></i><span>CampusClaw<small>NEXUS · 教学空间</small></span></div>
      <nav>
        <router-link v-for="item in nav" :key="item.to" :to="item.to" :class="{ active: active(item.to) }"><i class="fa-solid fa-fw" :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span></router-link>
      </nav>
      <div class="account"><b><i class="fa-solid fa-user" aria-hidden="true"></i>{{ session.user.username }}</b><br>{{ session.user.class_id }} 班 · {{ session.teacher ? '教师' : '学生' }}<br><el-button text style="color:#9bbebd;padding-left:0" @click="logout"><i class="fa-solid fa-right-from-bracket" aria-hidden="true"></i>退出登录</el-button></div>
    </aside>
    <main class="main">
      <header class="topline">
        <h1><i class="fa-solid" :class="titleIcon" aria-hidden="true"></i>{{ title }}</h1>
        <div class="eyebrow"><i class="fa-solid fa-chalkboard-user" aria-hidden="true"></i>{{ session.user.class_id }} 班教学空间</div>
      </header>
      <div v-if="session.previewing" class="preview-banner"><span>静态预览：虚构数据，不会访问服务器。</span><span><router-link to="/preview/teacher">教师</router-link> · <router-link to="/preview/student">学生</router-link></span></div>
      <div v-if="session.error" class="error" role="alert">{{ session.error }}</div>
      <div class="page"><RouterView /></div>
      <p class="footer-note"><i class="fa-solid fa-graduation-cap" aria-hidden="true"></i>CampusClaw Nexus · {{ session.user.class_id }} 班 · {{ session.teacher ? '教师工作空间' : '学生学习空间' }}</p>
    </main>
  </div>
</template>
