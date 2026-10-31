<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'

const session = useSession()
const catalog = useCatalog()
const supplementForm = reactive({ id: 0, title: '', content: '' })

async function reviewGap(row: Row, decision: string) {
  await session.action(async () => { await api(`/gaps/${row.id}/review`, 'POST', { decision, note: '' }); await catalog.load() })
}
async function supplement() {
  await session.action(async () => {
    await api(`/gaps/${supplementForm.id}/supplement`, 'POST', supplementForm)
    supplementForm.id = 0
    await catalog.load()
    ElMessage.success('补充材料正在索引')
  })
}
</script>

<template>
  <TeacherGate probe="/gaps">
    <div class="tagline">学生提问未获得足够材料依据时，系统会登记候选缺口。同班相近问题合并计数，补充材料完成索引并命中原问题后才标记“已补入”。</div>
    <section v-for="gap in catalog.lists.gaps" :key="gap.id" class="card">
      <div class="row spread"><span class="badge">{{ state(gap.state) }}</span><span class="muted">提问热度 {{ gap.heat }}</span></div>
      <p class="gap-summary">{{ gap.question }}</p>
      <div class="row inline-actions">
        <el-button v-if="['pending', 'index_failed'].includes(gap.state)" type="primary" @click="reviewGap(gap, 'approve')">确认缺口</el-button>
        <el-button v-if="['pending', 'approved', 'index_failed'].includes(gap.state)" @click="reviewGap(gap, 'reject')">驳回</el-button>
        <el-button v-if="['approved', 'index_failed'].includes(gap.state)" @click="Object.assign(supplementForm, { id: gap.id, title: '补充讲义', content: '' })">补充材料</el-button>
      </div>
      <p v-if="gap.note" class="muted">{{ gap.note }}</p>
      <details v-if="gap.state === 'filled'"><summary class="muted">查看回补前后检索结果</summary><pre class="pre">{{ JSON.stringify({ before: gap.before_hits, after: gap.after_hits }, null, 2) }}</pre></details>
    </section>
    <div v-if="!catalog.lists.gaps.length" class="card empty">暂时没有候选缺口</div>
    <el-dialog :model-value="!!supplementForm.id" title="补充知识材料" width="650px" @close="supplementForm.id = 0">
      <label>讲义标题</label><el-input v-model="supplementForm.title" />
      <label>补充正文</label><el-input v-model="supplementForm.content" type="textarea" :rows="10" />
      <el-button type="primary" style="margin-top:18px" @click="supplement">提交并建立索引</el-button>
    </el-dialog>
  </TeacherGate>
</template>
