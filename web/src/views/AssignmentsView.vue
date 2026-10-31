<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'

const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const assignmentForm = reactive({ title: '参数运算练习', question_template: '计算 ({a}+{b})×2，写出计算过程与结果。', ranges: '{"a":[10,99],"b":[2,20]}', answer_expression: '(a+b)*2', rubric: '[{"name":"计算过程","points":40},{"name":"最终答案","points":60}]', deadline: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 16) })
const answerForm = reactive({ id: 0, question: '', answer: '' })

async function newAssignment() {
  await session.action(async () => {
    await api('/assignments', 'POST', { ...assignmentForm, ranges: JSON.parse(assignmentForm.ranges), rubric: JSON.parse(assignmentForm.rubric), deadline: new Date(assignmentForm.deadline).toISOString() })
    await catalog.load()
    ElMessage.success('作业草稿已保存')
  })
}
async function publishAssignment(id: number) {
  await session.action(async () => { await api(`/assignments/${id}/publish`, 'POST'); await catalog.load(); ElMessage.success('发卷任务已加入队列') })
}
async function startPaper(row: Row) {
  await session.action(async () => {
    const value = await api(`/papers/${row.id}/start`, 'POST')
    Object.assign(answerForm, { id: row.id, question: value.question, answer: '' })
    await catalog.load()
  })
}
async function submitPaper() {
  await session.action(async () => {
    await api(`/papers/${answerForm.id}/submit`, 'POST', { answer: answerForm.answer })
    answerForm.id = 0
    await catalog.load()
    ElMessage.success('已提交，正在等待批改')
  })
}
async function reviewScore(row: Row) {
  await session.action(async () => {
    const value = await ElMessageBox.prompt('填写最终分数（0–100）', '教师复核', { inputValue: String(row.final_score ?? '') })
    const note = await ElMessageBox.prompt('填写改分或确认依据', '复核说明')
    await api(`/submissions/${row.id}/review`, 'POST', { score: Number(value.value), note: note.value })
    await catalog.load()
  })
}
</script>

<template>
  <section v-if="session.teacher" class="card">
    <h2>创建同纲作业</h2>
    <div class="fields">
      <div><label>作业名称</label><el-input v-model="assignmentForm.title" /></div>
      <div><label>截止时间</label><el-input v-model="assignmentForm.deadline" type="datetime-local" /></div>
      <div class="full"><label>题干模板（用 {a}、{b} 表示变量）</label><el-input v-model="assignmentForm.question_template" type="textarea" :rows="2" /></div>
      <div><label>参数范围 JSON</label><el-input v-model="assignmentForm.ranges" /></div>
      <div><label>服务端答案表达式</label><el-input v-model="assignmentForm.answer_expression" /></div>
      <div class="full"><label>Rubric JSON（满分总计100）</label><el-input v-model="assignmentForm.rubric" type="textarea" :rows="2" /></div>
    </div>
    <el-button type="primary" style="margin-top:18px" @click="newAssignment">保存草稿</el-button>
  </section>
  <section class="card">
    <h2>作业列表</h2>
    <div v-for="assignment in catalog.lists.assignments" :key="assignment.id" class="list-item row spread">
      <div><b>{{ assignment.title }}</b><p class="muted">{{ state(assignment.state) }} · 截止 {{ date(assignment.deadline) }}</p></div>
      <el-button v-if="session.teacher" type="primary" @click="publishAssignment(assignment.id)">{{ assignment.state === 'draft' ? '发布并发卷' : '检查未发卷学生' }}</el-button>
    </div>
    <div v-if="!catalog.lists.assignments.length" class="empty">暂无作业</div>
  </section>
  <section class="card">
    <h2>{{ session.teacher ? '学生试卷' : '我的试卷' }}</h2>
    <div v-for="paper in catalog.lists.papers" :key="paper.id" class="list-item">
      <div class="row spread"><b>{{ catalog.assignmentName(paper.assignment_id) }}<span v-if="session.teacher"> · {{ catalog.studentName(paper.user_id) }}</span></b><span class="badge">{{ state(paper.state) }}</span></div>
      <p class="gap-summary">{{ paper.question || '等待发卷完成' }}</p>
      <el-button v-if="!session.teacher && ['ready', 'frozen'].includes(paper.state)" @click="startPaper(paper)">{{ paper.state === 'ready' ? '开始作答' : '继续作答' }}</el-button>
      <p v-if="paper.error" class="muted">{{ paper.error }}</p>
    </div>
  </section>
  <section class="card">
    <h2>{{ session.teacher ? '批改与教师复核' : '我的批改结果' }}</h2>
    <div v-for="submission in catalog.lists.submissions" :key="submission.id" class="list-item">
      <div class="row spread"><b>提交 #{{ submission.id }}<span v-if="session.teacher"> · {{ catalog.studentName(submission.user_id) }}</span></b><span class="badge">{{ state(submission.state) }}</span></div>
      <p v-if="submission.final_score !== null">
        <template v-if="submission.state === 'reviewed'">教师复核后成绩 <b>{{ submission.final_score }}</b> / 100 <span class="muted">（AI 初评 {{ submission.ai_score }} / 100）</span></template>
        <template v-else>AI 批改成绩 <b>{{ submission.final_score }}</b> / 100</template>
      </p>
      <p class="gap-summary">{{ submission.feedback }}</p>
      <p v-if="submission.review_note" class="muted">教师复核依据：{{ submission.review_note }}</p>
      <el-button v-if="session.teacher && ['graded', 'reviewed'].includes(submission.state)" @click="reviewScore(submission)">人工复核 / 改分</el-button>
      <details><summary class="muted">查看提交及评分明细</summary><pre class="pre">{{ JSON.stringify({ answer: submission.answer, grading: submission.ai_raw }, null, 2) }}</pre></details>
    </div>
    <div v-if="!catalog.lists.submissions.length" class="empty">暂时没有提交记录</div>
  </section>
  <section v-if="!session.teacher" class="card">
    <h2>错题记录</h2>
    <div v-for="wrong in catalog.lists.wrong" :key="wrong.id" class="list-item">
      <b>提交 #{{ wrong.submission_id }}</b>
      <p class="gap-summary">{{ wrong.explanation }}</p>
      <el-button text @click="router.push('/conversations')">去学习助手回顾错因</el-button>
    </div>
  </section>
  <el-dialog :model-value="!!answerForm.id" title="我的作业" width="650px" @close="answerForm.id = 0">
    <p class="gap-summary">{{ answerForm.question }}</p>
    <p class="muted">题目实例已冻结。请把最终数值写在回答最后，便于核对。</p>
    <el-input v-model="answerForm.answer" type="textarea" :rows="8" placeholder="填写过程和最终答案" />
    <el-button type="primary" style="margin-top:18px" @click="submitPaper">提交作业</el-button>
  </el-dialog>
</template>
