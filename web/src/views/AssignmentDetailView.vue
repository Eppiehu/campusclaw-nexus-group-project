<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import { useChat } from '../stores/chat'
import TeacherGate from '../components/TeacherGate.vue'
import Subhead from '../components/Subhead.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const chat = useChat()
const assignmentId = computed(() => Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/assignments')) : '')
const assignment = computed(() => catalog.lists.assignments.find(item => item.id === assignmentId.value) as Row | undefined)
const papers = computed(() => catalog.lists.papers.filter(item => item.assignment_id === assignmentId.value))
const closed = computed(() => !!assignment.value && new Date(String(assignment.value.deadline)).getTime() <= Date.now())
const myPaper = computed(() => papers.value[0] as Row | undefined)
const mySubmission = computed(() => myPaper.value ? catalog.lists.submissions.find(item => item.paper_id === myPaper.value?.id) as Row | undefined : undefined)
const myWrong = computed(() => mySubmission.value ? catalog.lists.wrong.find(item => item.submission_id === mySubmission.value?.id) as Row | undefined : undefined)
const distinctWrong = computed(() => {
  const explanation = String(myWrong.value?.explanation || '').trim()
  const feedback = String(mySubmission.value?.feedback || '').trim()
  return !!explanation && explanation !== feedback
})
const answerValue = computed(() => {
  const value = myPaper.value?.standard_answer?.value
  return value === undefined || value === null ? null : value
})
const ready = ref(false)

onMounted(async () => {
  if (!session.previewing) await session.action(() => catalog.load())
  ready.value = true
})

function back() {
  router.push(`${prefix.value}/assignments`)
}

function rubricText(value: unknown) {
  if (typeof value === 'string') return value
  if (!Array.isArray(value)) return ''
  return value.map(item => typeof item === 'string' ? item : String((item as Row)?.name || '')).filter(Boolean).join('、')
}

function submissionFor(paper: Row) {
  return catalog.lists.submissions.find(item => item.paper_id === paper.id) as Row | undefined
}

function scoreLabel(paper: Row) {
  const submission = submissionFor(paper)
  if (!submission) return { text: '尚未提交', scored: false }
  if (!closed.value) return { text: '截止后统计', scored: false }
  if (submission.final_score == null) return { text: '暂无', scored: false }
  return { text: String(submission.final_score), scored: true }
}

function openAnswer() {
  router.push(`${prefix.value}/assignments/${assignmentId.value}/answer`)
}

function reviewWrong(wrong: Row) {
  const agent = catalog.lists.agents.find(item => item.enabled)
  if (!agent) { ElMessage.warning('本班没有已启用的学习助手'); return }
  chat.prepareReview(`请根据讲义帮我回顾这道错题：${wrong.explanation}`, Number(agent.id))
  router.push(`${prefix.value}/conversations`)
  if (session.previewing) ElMessage.info('静态预览不会连接服务器')
}

function openSubmission(paper: Row) {
  const submission = submissionFor(paper)
  if (!submission) return
  router.push(`${prefix.value}/assignments/${assignmentId.value}/submissions/${submission.id}`)
}

async function publish() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const republish = assignment.value?.state === 'withdrawn'
  const done = await session.action(async () => {
    await api(`/assignments/${assignmentId.value}/publish`, 'POST')
    await catalog.load()
    return true
  })
  if (done) ElMessage.success(republish ? '已重新发布' : '发卷任务已加入队列')
}

function edit() {
  router.push(`${prefix.value}/assignments/${assignmentId.value}/edit`)
}

async function withdraw() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const done = await session.action(async () => {
    try {
      await ElMessageBox.confirm('撤回后学生不能查看或提交。未提交的试卷会在重新发布时重新生成，已提交的作答会保留。', '撤回作业', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/assignments/${assignmentId.value}/withdraw`, 'POST')
    await catalog.load()
    return true
  })
  if (done) ElMessage.success('作业已撤回')
}

async function remove() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后作业不能恢复，学生试卷和作答也会一并删除。', '删除作业', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/assignments/${assignmentId.value}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) { ElMessage.success('作业已删除'); back() }
}
</script>

<template>
  <TeacherGate v-if="session.teacher" probe="/students">
    <section class="card fill">
      <Subhead @back="back">返回作业列表</Subhead>
      <p v-if="!ready" class="muted">正在读取作业…</p>
      <p v-else-if="!assignment">这个作业当前不可查看。</p>
      <div v-else class="assignment-split">
        <div class="assignment-info">
          <div class="assignment-head">
            <div class="row spread">
              <div>
                <h2>{{ assignment.title }}</h2>
                <p class="muted"><span class="badge">{{ state(assignment.state) }}</span> · 截止 {{ date(assignment.deadline) }}</p>
              </div>
              <div class="row">
                <el-button v-if="assignment.state === 'draft' || assignment.state === 'withdrawn'" @click="edit">编辑</el-button>
                <el-button v-if="assignment.state === 'published'" @click="withdraw">撤回</el-button>
                <el-button type="danger" plain @click="remove">删除</el-button>
                <el-button type="primary" @click="publish">{{ assignment.state === 'draft' ? '发布并发卷' : assignment.state === 'withdrawn' ? '重新发布' : '检查未发卷学生' }}</el-button>
              </div>
            </div>
            <p v-if="assignment.state === 'withdrawn'" class="muted">已撤回：学生不能查看或提交。可以编辑题目后重新发布。未提交的试卷会重新生成，已提交的作答会保留。</p>
            <p v-else-if="assignment.state === 'published' && !closed" class="muted">截止前只能查看已提交的作业。到截止时间后系统会自动批改，学生在截止前可以修改并重新提交。</p>
            <p v-else-if="assignment.state === 'published' && closed" class="muted">已过截止时间。系统会自动批改，完成后可以复核。</p>
          </div>
          <div class="assignment-body">
            <h3>题目</h3>
            <pre class="pre material-body">{{ assignment.question_template }}</pre>
            <p class="muted">参数范围 {{ JSON.stringify(assignment.ranges) }}</p>
            <h3>作答提示</h3>
            <p class="gap-summary">{{ assignment.answer_hint || '未填写' }}</p>
            <p class="muted">作答提示只给学生查看，不作为评分依据。</p>
            <h3>评分规则</h3>
            <p class="gap-summary">{{ rubricText(assignment.rubric) || '未填写评分说明' }}</p>
            <p class="muted">由 AI 根据这段说明自行判断，满分 100。</p>
          </div>
        </div>
        <div class="assignment-answers">
          <h2><i class="fa-solid fa-users" aria-hidden="true"></i>学生作答</h2>
          <div class="records">
            <div v-if="!papers.length" class="empty">发布后才会为学生生成题目。</div>
            <template v-for="paper in papers" :key="paper.id">
              <button v-if="submissionFor(paper)" type="button" class="list-item submission-row" @click="openSubmission(paper)">
                <span class="submission-main">
                  <b>{{ catalog.studentName(paper.user_id) }}</b>
                  <p class="muted"><span class="badge">{{ state(paper.state) }}</span> · {{ closed ? state(submissionFor(paper)!.state) : '已提交' }}</p>
                  <p v-if="paper.error" class="muted">{{ paper.error }}</p>
                </span>
                <span class="submission-score" :class="{ 'is-empty': !scoreLabel(paper).scored }">{{ scoreLabel(paper).text }}</span>
              </button>
              <div v-else class="list-item submission-row">
                <span class="submission-main">
                  <b>{{ catalog.studentName(paper.user_id) }}</b>
                  <p class="muted"><span class="badge">{{ state(paper.state) }}</span></p>
                  <p v-if="paper.error" class="muted">{{ paper.error }}</p>
                </span>
                <span class="submission-score is-empty">尚未提交</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </section>
  </TeacherGate>
  <section v-else class="card fill">
    <Subhead @back="back">返回作业列表</Subhead>
    <p v-if="!ready" class="muted">正在读取作业…</p>
    <p v-else-if="!assignment">这个作业当前不可查看。</p>
    <div v-else class="assignment-split">
      <div class="assignment-info">
        <div class="assignment-head">
          <div class="row spread">
            <div>
              <h2>{{ assignment.title }}</h2>
              <p class="muted"><span class="badge">{{ state(assignment.state) }}</span> · 截止 {{ date(assignment.deadline) }}</p>
            </div>
            <div class="row">
              <el-button v-if="myPaper && ['ready', 'frozen'].includes(String(myPaper.state)) && !closed" @click="openAnswer">{{ myPaper.state === 'ready' ? '开始作答' : '继续作答' }}</el-button>
              <el-button v-else-if="myPaper && myPaper.state === 'submitted' && !closed" @click="openAnswer">修改并重新提交</el-button>
            </div>
          </div>
          <p v-if="!myPaper" class="muted">试卷还在生成，请稍后刷新。</p>
          <p v-else-if="!closed" class="muted">截止前可以修改并重新提交。到截止时间后才会批改。</p>
          <p v-else class="muted">已过截止时间，不能再修改或提交。</p>
          <p v-if="myPaper?.error" class="muted">{{ myPaper.error }}</p>
        </div>
        <div class="assignment-body">
          <h3>题目</h3>
          <p class="gap-summary">{{ myPaper?.question || '等待发卷完成' }}</p>
          <template v-if="assignment.answer_hint">
            <h3>作答提示</h3>
            <p class="gap-summary">{{ assignment.answer_hint }}</p>
          </template>
          <template v-if="closed">
            <h3>评分规则</h3>
            <p class="gap-summary">{{ rubricText(assignment.rubric) || '未填写评分说明' }}</p>
            <h3>参考答案</h3>
            <p v-if="answerValue != null" class="gap-summary">{{ answerValue }}</p>
            <p v-else class="muted">参考答案尚未生成。</p>
          </template>
          <p v-else class="muted">评分规则和参考答案在截止后可以查看。</p>
        </div>
      </div>
      <div class="assignment-answers">
        <h2><i class="fa-solid fa-square-check" aria-hidden="true"></i>批改详情</h2>
        <div class="records">
          <div v-if="!mySubmission" class="empty">尚未提交</div>
          <template v-else>
            <h3>我的作答</h3>
            <pre class="pre material-body">{{ mySubmission.answer }}</pre>
            <h3>批改结果</h3>
            <p v-if="!closed" class="muted">截止时间之后才会批改。</p>
            <template v-else>
              <p v-if="mySubmission.final_score != null">
                <template v-if="mySubmission.state === 'reviewed'">教师复核后成绩 <b>{{ mySubmission.final_score }}</b> <span v-if="mySubmission.ai_score != null" class="muted">（AI 初评 {{ mySubmission.ai_score }}）</span></template>
                <template v-else>AI 批改成绩 <b>{{ mySubmission.final_score }}</b></template>
              </p>
              <p v-else class="muted">批改尚未完成。</p>
              <p v-if="mySubmission.feedback" class="gap-summary">{{ mySubmission.feedback }}</p>
              <p v-if="mySubmission.review_note" class="muted">教师复核依据：{{ mySubmission.review_note }}</p>
              <template v-if="myWrong">
                <template v-if="distinctWrong">
                  <h3>错题说明</h3>
                  <p class="gap-summary">{{ myWrong.explanation }}</p>
                </template>
                <el-button text @click="reviewWrong(myWrong)">去学习助手回顾错因</el-button>
              </template>
            </template>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>
