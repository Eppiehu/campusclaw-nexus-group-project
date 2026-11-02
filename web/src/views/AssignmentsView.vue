<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/assignments')) : '')

function openCreate() {
  router.push(`${prefix.value}/assignments/new`)
}

function openAssignment(id: number) {
  router.push(`${prefix.value}/assignments/${id}`)
}

function statsFor(assignment: Row) {
  const papers = catalog.lists.papers.filter(item => item.assignment_id === assignment.id)
  const paperIds = new Set(papers.map(item => Number(item.id)))
  const submissions = catalog.lists.submissions.filter(item => paperIds.has(Number(item.paper_id)))
  const submitted = papers.filter(item => item.state === 'submitted').length
  const expected = catalog.lists.students.length || papers.length
  const open = new Date(String(assignment.deadline)).getTime() > Date.now()
  const scored = submissions.filter(item => item.final_score != null).map(item => Number(item.final_score))
  const average = !open && scored.length ? Math.round((scored.reduce((sum, score) => sum + score, 0) / scored.length) * 10) / 10 : null
  return { submitted, expected, pending: Math.max(expected - submitted, 0), average, open }
}

function averageText(assignment: Row) {
  const stats = statsFor(assignment)
  if (stats.open) return '截止后统计'
  return stats.average == null ? '暂无' : String(stats.average)
}

async function withdrawAssignment(row: Row) {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const done = await session.action(async () => {
    try {
      await ElMessageBox.confirm('撤回后学生不能查看或提交。未提交的试卷会在重新发布时重新生成，已提交的作答会保留。', '撤回作业', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/assignments/${row.id}/withdraw`, 'POST')
    await catalog.load()
    return true
  })
  if (done) ElMessage.success('作业已撤回')
}

async function removeAssignment(row: Row) {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后作业不能恢复，学生试卷和作答也会一并删除。', '删除作业', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/assignments/${row.id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) ElMessage.success('作业已删除')
}

function wrongPaper(wrong: Row) {
  const submission = catalog.lists.submissions.find(item => item.id === wrong.submission_id)
  return submission ? catalog.lists.papers.find(item => item.id === submission.paper_id) : undefined
}

function wrongLabel(wrong: Row) {
  const paper = wrongPaper(wrong)
  return paper ? catalog.assignmentName(paper.assignment_id) : `提交 #${wrong.submission_id}`
}

function openWrong(wrong: Row) {
  const paper = wrongPaper(wrong)
  if (!paper) return
  openAssignment(Number(paper.assignment_id))
}

function mine(assignment: Row) {
  const paper = catalog.lists.papers.find(item => item.assignment_id === assignment.id)
  if (!paper) return '等待发卷'
  const open = new Date(String(assignment.deadline)).getTime() > Date.now()
  if (open || paper.state !== 'submitted') return state(String(paper.state))
  const submission = catalog.lists.submissions.find(item => item.paper_id === paper.id)
  if (!submission || submission.final_score == null) return '暂无成绩'
  return `得分 ${submission.final_score}`
}
</script>

<template>
  <template v-if="session.teacher">
    <section class="card fill">
      <div class="row spread">
        <h2><i class="fa-solid fa-clipboard-list" aria-hidden="true"></i>作业列表</h2>
        <el-button type="primary" @click="openCreate"><i class="fa-solid fa-plus" aria-hidden="true"></i>创建作业</el-button>
      </div>
      <div class="records">
        <div v-if="!catalog.lists.assignments.length" class="empty">暂无作业</div>
        <div v-for="assignment in catalog.lists.assignments" :key="assignment.id" class="list-item assignment-item">
          <button type="button" class="assignment-open" @click="openAssignment(assignment.id)">
            <b>{{ assignment.title }}</b>
            <p class="muted">{{ state(assignment.state) }} · 截止 {{ date(assignment.deadline) }}</p>
            <p class="assignment-metrics">
              <span>已提交 <b>{{ statsFor(assignment).submitted }}/{{ statsFor(assignment).expected }}</b></span>
              <span>未提交 <b>{{ statsFor(assignment).pending }}</b></span>
              <span>平均分 <b>{{ averageText(assignment) }}</b></span>
            </p>
          </button>
          <div class="assignment-actions">
            <el-button v-if="assignment.state === 'published'" @click="withdrawAssignment(assignment)">撤回</el-button>
            <el-button type="danger" plain @click="removeAssignment(assignment)">删除</el-button>
          </div>
        </div>
      </div>
    </section>
  </template>
  <section v-else class="card fill">
    <div class="assignment-split student-work">
      <div class="assignment-info">
        <h2 class="assignment-head"><i class="fa-solid fa-clipboard-list" aria-hidden="true"></i>作业列表</h2>
        <div class="records">
          <div v-if="!catalog.lists.assignments.length" class="empty">暂无作业</div>
          <button v-for="assignment in catalog.lists.assignments" :key="assignment.id" type="button" class="list-item overview-open" @click="openAssignment(assignment.id)">
            <b>{{ assignment.title }}</b>
            <p class="muted">{{ state(assignment.state) }} · 截止 {{ date(assignment.deadline) }} · {{ mine(assignment) }}</p>
          </button>
        </div>
      </div>
      <div class="assignment-answers">
        <h2><i class="fa-solid fa-circle-question" aria-hidden="true"></i>错题记录</h2>
        <div class="records">
          <div v-if="!catalog.lists.wrong.length" class="empty">暂时没有错题记录</div>
          <button v-for="wrong in catalog.lists.wrong" :key="wrong.id" type="button" class="list-item overview-open" @click="openWrong(wrong)">
            <b>{{ wrongLabel(wrong) }}</b>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
