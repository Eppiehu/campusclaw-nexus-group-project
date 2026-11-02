import { createRouter, createWebHistory } from 'vue-router'
import { token } from '../api'
import ShellLayout from '../components/ShellLayout.vue'
import LoginView from '../views/LoginView.vue'
import OverviewView from '../views/OverviewView.vue'
import ChatView from '../views/ChatView.vue'
import MaterialsView from '../views/MaterialsView.vue'
import MaterialDetailView from '../views/MaterialDetailView.vue'
import AppsView from '../views/AppsView.vue'
import AgentFormView from '../views/AgentFormView.vue'
import SkillDetailView from '../views/SkillDetailView.vue'
import SkillFormView from '../views/SkillFormView.vue'
import TemplateFormView from '../views/TemplateFormView.vue'
import GapsView from '../views/GapsView.vue'
import AssignmentsView from '../views/AssignmentsView.vue'
import AssignmentFormView from '../views/AssignmentFormView.vue'
import AssignmentDetailView from '../views/AssignmentDetailView.vue'
import AssignmentAnswerView from '../views/AssignmentAnswerView.vue'
import SubmissionReviewView from '../views/SubmissionReviewView.vue'
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
  { path: 'materials/:id(\\d+)', name: 'material', component: MaterialDetailView, meta: { title: '讲义正文' } },
  { path: 'apps', name: 'apps', component: AppsView, meta: { title: '应用与技能' } },
  { path: 'apps/templates/new', name: 'template-new', component: TemplateFormView, meta: { title: '新建模板' } },
  { path: 'apps/templates/:id(\\d+)', name: 'template', component: TemplateFormView, meta: { title: '编辑模板' } },
  { path: 'apps/skills/:id(\\d+)/edit', name: 'skill-edit', component: SkillFormView, meta: { title: '编辑技能' } },
  { path: 'apps/skills/:id(\\d+)', name: 'skill', component: SkillDetailView, meta: { title: '技能正文' } },
  { path: 'apps/new', name: 'app-new', component: AgentFormView, meta: { title: '创建应用' } },
  { path: 'apps/:id(\\d+)', name: 'app', component: AgentFormView, meta: { title: '编辑应用' } },
  { path: 'gaps', name: 'gaps', component: GapsView, meta: { title: '知识缺口' } },
  { path: 'assignments', name: 'assignments', component: AssignmentsView, meta: { title: '作业与批改' } },
  { path: 'assignments/new', name: 'assignment-new', component: AssignmentFormView, meta: { title: '创建作业' } },
  { path: 'assignments/:id(\\d+)/edit', name: 'assignment-edit', component: AssignmentFormView, meta: { title: '编辑作业' } },
  { path: 'assignments/:id(\\d+)/submissions/:submissionId(\\d+)', name: 'assignment-submission', component: SubmissionReviewView, meta: { title: '作答复核' } },
  { path: 'assignments/:id(\\d+)/answer', name: 'assignment-answer', component: AssignmentAnswerView, meta: { title: '作业作答' } },
  { path: 'assignments/:id(\\d+)', name: 'assignment', component: AssignmentDetailView, meta: { title: '作业详情' } },
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
