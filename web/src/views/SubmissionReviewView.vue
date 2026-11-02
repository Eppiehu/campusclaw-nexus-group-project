<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import Subhead from '../components/Subhead.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const assignmentId = computed(() => Number(route.params.id))
const submissionId = computed(() => Number(route.params.submissionId))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/assignments')) : '')
const assignment = computed(() => catalog.lists.assignments.find(item => item.id === assignmentId.value) as Row | undefined)
const submission = computed(() => catalog.lists.submissions.find(item => item.id === submissionId.value) as Row | undefined)
const paper = computed(() => catalog.lists.papers.find(item => item.id === submission.value?.paper_id) as Row | undefined)
const closed = computed(() => !!assignment.value && new Date(String(assignment.value.deadline)).getTime() <= Date.now())
const canReview = computed(() => closed.value && ['graded', 'reviewed', 'grade_failed'].includes(String(submission.value?.state || '')))
const items = computed(() => Array.isArray(submission.value?.ai_raw?.items) ? submission.value.ai_raw.items as Row[] : [])
const noteTemplates = [
  { label: '确认得分', text: '过程完整，结果正确，确认得分。' },
  { label: '过程有误', text: '计算过程有误，已按正确部分给分。' },
  { label: '结果有误', text: '最终结果不正确，已按过程酌情给分。' },
  { label: '缺少过程', text: '最终结果正确，但缺少计算过程。' },
  { label: '人工核定', text: '自动批改未能完成，已人工核定成绩。' },
]
const form = reactive<{ score: number | undefined, note: string }>({ score: undefined, note: '' })
const ready = ref(false)

onMounted(async () => {
  if (!session.previewing) await session.action(() => catalog.load())
  ready.value = true
})

watch(() => submission.value?.id, () => {
  const value = submission.value
  form.score = value?.final_score === null || value?.final_score === undefined ? undefined : Number(value.final_score)
  form.note = String(value?.review_note || '')
}, { immediate: true })

function back() {
  router.push(`${prefix.value}/assignments/${assignmentId.value}`)
}

async function review() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const score = Number(form.score)
  if (!Number.isFinite(score) || score < 0 || score > 100) { ElMessage.warning('分数须为 0 至 100'); return }
  if (!form.note.trim()) { ElMessage.warning('请填写复核说明'); return }
  const saved = await session.action(async () => {
    const result = await api(`/submissions/${submissionId.value}/review`, 'POST', { score, note: form.note.trim() })
    await catalog.load()
    return result
  })
  if (saved) ElMessage.success('复核已保存')
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="back">返回题目</Subhead>
    <div class="records">
    <p v-if="!ready" class="muted">正在读取作答…</p>
    <p v-else-if="!submission || !paper">这份作答当前不可查看。</p>
    <template v-else>
        <div class="row spread">
          <h2>{{ catalog.studentName(submission.user_id) }} · {{ assignment?.title || '作业' }}</h2>
          <span class="badge">{{ state(submission.state) }}</span>
        </div>
        <h3>题目</h3>
        <p class="gap-summary">{{ paper.question || '等待发卷完成' }}</p>
        <h3>学生作答</h3>
        <pre class="pre material-body">{{ submission.answer }}</pre>
        <h3>批改结果</h3>
        <p v-if="!closed" class="muted">截止时间之后才能批改。</p>
        <template v-else>
          <p v-if="submission.final_score != null">
            <template v-if="submission.state === 'reviewed'">教师复核后成绩 <b>{{ submission.final_score }}</b> / 100 <span class="muted">（AI 初评 {{ submission.ai_score }} / 100）</span></template>
            <template v-else>AI 批改成绩 <b>{{ submission.final_score }}</b> / 100</template>
          </p>
          <p v-else class="muted">批改尚未完成。</p>
          <p v-if="submission.feedback" class="gap-summary">{{ submission.feedback }}</p>
          <p v-for="item in items" :key="item.criterion" class="muted">{{ item.criterion }} · {{ item.score }} 分<span v-if="item.reason"> · {{ item.reason }}</span></p>
          <p v-if="submission.review_note" class="muted">已有复核说明：{{ submission.review_note }}</p>
        </template>
        <h2>人工复核</h2>
        <p v-if="!closed" class="muted">截止时间之后才能批改。</p>
        <template v-else-if="canReview">
          <label for="review-score">最终分数（0–100）</label>
          <el-input-number id="review-score" v-model="form.score" :min="0" :max="100" :step="1" :precision="0" controls-position="right" />
          <label for="review-note">复核说明</label>
          <div class="note-templates">
            <el-button v-for="item in noteTemplates" :key="item.label" @click="form.note = item.text">{{ item.label }}</el-button>
          </div>
          <el-input id="review-note" v-model="form.note" type="textarea" :rows="4" maxlength="2000" placeholder="填写改分或确认依据，也可点选上面的模板" />
          <p v-if="submission.state === 'grade_failed'" class="muted">自动批改失败，填写的分数会作为最终成绩。</p>
          <el-button type="primary" style="margin-top:18px" :loading="session.busy" @click="review">提交复核</el-button>
        </template>
        <p v-else class="muted">批改完成后才能复核改卷。</p>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
