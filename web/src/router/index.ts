import { createRouter, createWebHistory } from 'vue-router'
import { token } from '../api'
import ShellLayout from '../components/ShellLayout.vue'
import LoginView from '../views/LoginView.vue'
import OverviewView from '../views/OverviewView.vue'
import ChatView from '../views/ChatView.vue'
import MaterialsView from '../views/MaterialsView.vue'
import AppsView from '../views/AppsView.vue'
import GapsView from '../views/GapsView.vue'
import AssignmentsView from '../views/AssignmentsView.vue'
import ReportsView from '../views/ReportsView.vue'
import JobsView from '../views/JobsView.vue'
import AuditView from '../views/AuditView.vue'
import PreviewHome from '../views/PreviewHome.vue'
import { applyPreview } from '../preview'
import type { RouteRecordRaw } from 'vue-router'

const pages: RouteRecordRaw[] = [
  { path: '', name: 'overview', component: OverviewView, meta: { title: '工作台' } },
  { path: 'conversations', name: 'conversations', component: ChatView, meta: { title: '学习助手' } },
  { path: 'conversations/:id(\\d+)', name: 'conversation', component: ChatView, meta: { title: '学习助手' } },
  { path: 'materials/new', name: 'material-new', component: MaterialsView, meta: { title: '讲义知识库' } },
  { path: 'materials', name: 'materials', component: MaterialsView, meta: { title: '讲义知识库' } },
  { path: 'materials/:id(\\d+)', name: 'material', component: MaterialsView, meta: { title: '讲义知识库' } },
  { path: 'apps', name: 'apps', component: AppsView, meta: { title: '应用与技能' } },
  { path: 'gaps', name: 'gaps', component: GapsView, meta: { title: '知识缺口' } },
  { path: 'assignments', name: 'assignments', component: AssignmentsView, meta: { title: '作业与批改' } },
  { path: 'reports', name: 'reports', component: ReportsView, meta: { title: '学情周报' } },
  { path: 'jobs', name: 'jobs', component: JobsView, meta: { title: '后台任务' } },
  { path: 'audit', name: 'audit', component: AuditView, meta: { title: '调用记录' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { title: '登录' } },
    { path: '/preview', name: 'preview-home', component: PreviewHome, meta: { preview: true, title: '静态预览' } },
    { path: '/', component: ShellLayout, meta: { auth: true }, children: pages },
    {
      path: '/preview/:role(teacher|student)',
      component: ShellLayout,
      meta: { preview: true },
      children: pages.map(page => ({ ...page, name: `preview-${String(page.name)}` })),
    },
  ],
})

router.beforeEach(to => {
  if (to.matched.some(record => record.meta.preview)) {
    if (!import.meta.env.DEV) return '/login'
    if (to.params.role === 'teacher' || to.params.role === 'student') applyPreview(to.params.role)
    return
  }
  if (to.matched.some(record => record.meta.auth) && !token()) return { path: '/login', query: { redirect: to.fullPath } }
})
