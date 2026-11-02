<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
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

async function clearTasks() {
  const cleared = await session.action(async () => {
    try {
      await ElMessageBox.confirm('已完成和失败的任务记录会被删除，且不能恢复。正在排队或执行的任务会保留。', '清空任务记录', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    const result = await api('/tasks', 'DELETE')
    await catalog.load()
    return result
  })
  if (cleared) ElMessage.success(cleared.removed ? `已清空 ${cleared.removed} 条任务记录` : '没有可清空的任务记录')
}
</script>

<template>
  <TeacherGate probe="/tasks">
    <section class="card fill">
      <div class="row spread"><h2><i class="fa-solid fa-gears" aria-hidden="true"></i>任务状态</h2><el-button type="danger" plain @click="clearTasks"><i class="fa-solid fa-trash-can" aria-hidden="true"></i>清空</el-button></div>
      <p class="muted">索引、发卷、批改和周报在后台执行。到截止时间后会自动批改。失败后可以重试；清空只删除已结束的记录，正在排队或执行的任务会保留。</p>
      <div class="records">
      <el-table :data="catalog.lists.tasks" height="100%">
        <el-table-column prop="kind" label="任务类型" width="100" />
        <el-table-column prop="target_id" label="对象" width="80" />
        <el-table-column label="状态" width="130"><template #default="{ row }">{{ state(row.state) }}</template></el-table-column>
        <el-table-column prop="attempts" label="执行次数" width="100" />
        <el-table-column prop="error" label="错误说明" />
        <el-table-column label="操作" width="100"><template #default="{ row }"><el-button v-if="['failed', 'dispatch_failed'].includes(row.state)" text type="primary" @click="retryTask(row)">重试</el-button></template></el-table-column>
      </el-table>
      </div>
    </section>
  </TeacherGate>
</template>
