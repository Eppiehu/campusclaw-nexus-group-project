<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { date } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'

const session = useSession()
const catalog = useCatalog()

async function clearAudit() {
  const cleared = await session.action(async () => {
    try {
      await ElMessageBox.confirm('清空后，已有调用记录不能恢复。', '清空调用记录', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    const result = await api('/audit', 'DELETE')
    await catalog.load()
    return result
  })
  if (cleared) ElMessage.success(cleared.removed ? `已清空 ${cleared.removed} 条调用记录` : '没有可清空的调用记录')
}
</script>

<template>
  <TeacherGate probe="/audit">
    <section class="card fill">
      <div class="row spread"><h2><i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>请求与工具记录</h2><el-button type="danger" plain @click="clearAudit"><i class="fa-solid fa-trash-can" aria-hidden="true"></i>清空</el-button></div>
      <p class="muted">按请求编号关联模型参数、工具调用和结果，记录中不包含登录令牌或模型密钥。</p>
      <div class="records">
      <div v-for="item in catalog.lists.audit" :key="item.id" class="list-item">
        <div class="row spread"><b>{{ item.action }}</b><span class="muted">{{ date(item.created_at) }} · {{ item.success ? '成功' : '失败' }}</span></div>
        <details><summary class="muted">{{ item.request_id }}</summary><pre class="pre">{{ JSON.stringify(item.details, null, 2) }}</pre></details>
      </div>
      </div>
    </section>
  </TeacherGate>
</template>
