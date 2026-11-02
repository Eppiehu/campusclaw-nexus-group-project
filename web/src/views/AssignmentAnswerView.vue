<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type { Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import Subhead from '../components/Subhead.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const assignmentId = computed(() => Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/assignments')) : '')
const assignment = computed(() => catalog.lists.assignments.find(item => item.id === assignmentId.value) as Row | undefined)
const paper = computed(() => catalog.lists.papers.find(item => item.assignment_id === assignmentId.value) as Row | undefined)
const closed = computed(() => !!assignment.value && new Date(String(assignment.value.deadline)).getTime() <= Date.now())
const answer = ref('')
const question = ref('')
const revising = ref(false)
const blocked = ref('')
const ready = ref(false)

function back() {
  router.push(`${prefix.value}/assignments/${assignmentId.value}`)
}

async function load() {
  if (!session.user && !session.previewing) return
  ready.value = false
  blocked.value = ''
  if (session.teacher) {
    router.replace(`${prefix.value}/assignments/${assignmentId.value}`)
    return
  }
  if (!session.previewing) await session.action(() => catalog.load())
  const row = assignment.value
  const current = paper.value
  ready.value = true
  if (!row) { blocked.value = '这个作业当前不可查看。'; return }
  if (!current) { blocked.value = '试卷还在生成，请稍后刷新。'; return }
  if (row.state !== 'published' || closed.value) { blocked.value = '已过截止时间，不能再修改或提交。'; return }
  if (current.state === 'submitted') {
    revising.value = true
    question.value = String(current.question || '')
    const submission = catalog.lists.submissions.find(item => item.paper_id === current.id)
    answer.value = String(submission?.answer || '')
    return
  }
  if (current.state === 'frozen') {
    revising.value = false
    question.value = String(current.question || '')
    return
  }
  if (current.state !== 'ready') { blocked.value = '这份作业当前不能作答。'; return }
  if (session.previewing) {
    question.value = String(current.question || '')
    return
  }
  const started = await session.action(() => api(`/papers/${current.id}/start`, 'POST'))
  if (!started) { blocked.value = '暂时不能开始作答。'; return }
  question.value = String(started.question || '')
  revising.value = false
  answer.value = ''
  await catalog.load()
}

watch(() => [route.fullPath, session.user?.id], () => { load() }, { immediate: true })

async function submit() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const current = paper.value
  if (!current || blocked.value) return
  const wasRevising = revising.value
  const saved = await session.action(async () => {
    await api(`/papers/${current.id}/submit`, 'POST', { answer: answer.value })
    await catalog.load()
    return true
  })
  if (!saved) return
  ElMessage.success(wasRevising ? '已重新提交，截止前还可以继续修改' : '已提交，截止前可以修改并重新提交')
  back()
}
</script>

<template>
  <section class="card fill">
    <Subhead @back="back">返回作业详情</Subhead>
    <div class="records">
      <p v-if="!ready" class="muted">正在读取作业…</p>
      <p v-else-if="blocked" class="muted">{{ blocked }}</p>
      <template v-else>
        <h3>题目</h3>
        <p class="gap-summary">{{ question || '等待发卷完成' }}</p>
        <template v-if="assignment?.answer_hint">
          <h3>作答提示</h3>
          <p class="gap-summary">{{ assignment.answer_hint }}</p>
        </template>
        <p class="muted">题目实例已冻结。请把最终数值写在回答最后，便于核对。</p>
        <label for="paper-answer">我的作答</label>
        <el-input id="paper-answer" v-model="answer" type="textarea" :rows="10" maxlength="12000" placeholder="填写过程和最终答案" />
        <div class="row" style="margin-top:18px">
          <el-button type="primary" :loading="session.busy" @click="submit">{{ revising ? '重新提交' : '提交作业' }}</el-button>
          <el-button @click="back">取消</el-button>
        </div>
      </template>
    </div>
  </section>
</template>
