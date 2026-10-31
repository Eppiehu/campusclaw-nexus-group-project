<script setup lang="ts">
import { api } from '../api'
import { state, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'

const session = useSession()
const catalog = useCatalog()
async function retryTask(row: Row) {
  await session.action(async () => { await api(`/tasks/${row.id}/retry`, 'POST'); await catalog.load() })
}
</script>

<template>
  <TeacherGate probe="/tasks">
    <section class="card">
      <h2>任务状态</h2>
      <p class="muted">索引、发卷、批改和周报在后台执行，失败记录会保留。可以在排查原因后重试。</p>
      <el-table :data="catalog.lists.tasks">
        <el-table-column prop="kind" label="任务类型" width="100" />
        <el-table-column prop="target_id" label="对象" width="80" />
        <el-table-column label="状态" width="130"><template #default="{ row }">{{ state(row.state) }}</template></el-table-column>
        <el-table-column prop="attempts" label="执行次数" width="100" />
        <el-table-column prop="error" label="错误说明" />
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button v-if="['failed', 'dispatch_failed'].includes(row.state)" text type="primary" @click="retryTask(row)">重试</el-button></template></el-table-column>
      </el-table>
    </section>
  </TeacherGate>
</template>
