<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useSession } from '../stores/session'

const props = defineProps<{ probe: string }>()
const session = useSession()
const message = ref('')

onMounted(async () => {
  if (session.teacher) return
  if (session.previewing) { message.value = '权限不足'; return }
  try { await api(props.probe) }
  catch (error: any) { message.value = error.message }
})
</script>

<template>
  <slot v-if="session.teacher" />
  <section v-else class="card">
    <h2>此页面仅教师可用</h2>
    <p class="muted">学生导航不会显示这个入口。直接打开地址时，仍由服务端拒绝。</p>
    <div v-if="message" class="error" role="alert">{{ message }}</div>
  </section>
</template>
