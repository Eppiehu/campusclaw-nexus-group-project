<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { date, state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import ScoreChart from '../components/ScoreChart.vue'

const session = useSession()
const catalog = useCatalog()

async function newWeekly() {
  await session.action(async () => { await api('/weekly', 'POST'); await catalog.load(); ElMessage.success('已提交本周报告生成任务') })
}
async function publishWeekly(row: Row) {
  await session.action(async () => { await api(`/weekly/${row.id}/publish`, 'POST', { comment: row.teacher_comment }); await catalog.load(); ElMessage.success('周报已发布') })
}
</script>

<template>
  <div class="row spread" style="margin-bottom:20px">
    <p class="muted">指标由程序统计，AI提供解读，教师确认后发布。</p>
    <el-button v-if="session.teacher" type="primary" @click="newWeekly">生成本周报告</el-button>
  </div>
  <section v-for="report in catalog.lists.weekly" :key="report.id" class="card">
    <div class="row spread"><h2>{{ date(report.period_start).split(' ')[0] }} 起一周</h2><span class="badge">{{ state(report.state) }}</span></div>
    <template v-if="report.facts && Object.keys(report.facts).length">
      <div class="stats">
        <div class="stat"><span class="muted">检索次数</span><b>{{ report.facts.search_count }}</b></div>
        <div class="stat"><span class="muted">作业提交</span><b>{{ report.facts.submission_count }}</b></div>
        <div class="stat"><span class="muted">平均成绩</span><b>{{ report.facts.average_score ?? '—' }}</b></div>
      </div>
      <ScoreChart :facts="report.facts" />
      <p v-if="!report.facts.sample_sufficient" class="tagline">本周记录不够，暂不推断学习趋势。</p>
      <label>教学观察与建议</label>
      <el-input v-if="session.teacher && report.state === 'draft'" v-model="report.teacher_comment" type="textarea" :rows="5" />
      <p v-else class="gap-summary" style="white-space:pre-wrap">{{ report.teacher_comment }}</p>
      <el-button v-if="session.teacher && report.state === 'draft'" type="primary" style="margin-top:14px" @click="publishWeekly(report)">确认并发布</el-button>
      <details style="margin-top:18px"><summary class="muted">查看统计依据</summary><pre class="pre">{{ JSON.stringify(report.facts, null, 2) }}</pre></details>
    </template>
  </section>
  <div v-if="!catalog.lists.weekly.length" class="card empty">{{ session.teacher ? '尚未生成本周报告' : '暂无已发布周报' }}</div>
</template>
