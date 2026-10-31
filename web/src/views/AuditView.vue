<script setup lang="ts">
import { date } from '../format'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'

const catalog = useCatalog()
</script>

<template>
  <TeacherGate probe="/audit">
    <section class="card">
      <h2>请求与工具记录</h2>
      <p class="muted">按请求编号关联模型参数、工具调用和结果，记录中不包含登录令牌或模型密钥。</p>
      <div v-for="item in catalog.lists.audit" :key="item.id" class="list-item">
        <div class="row spread"><b>{{ item.action }}</b><span class="muted">{{ date(item.created_at) }} · {{ item.success ? '成功' : '失败' }}</span></div>
        <details><summary class="muted">{{ item.request_id }}</summary><pre class="pre">{{ JSON.stringify(item.details, null, 2) }}</pre></details>
      </div>
    </section>
  </TeacherGate>
</template>
