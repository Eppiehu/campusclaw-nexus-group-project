<script setup lang="ts">
import { useRouter } from 'vue-router'
import { date, state } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'

const router = useRouter()
const session = useSession()
const catalog = useCatalog()
</script>

<template>
  <div class="stats">
    <div class="stat"><span class="muted">学习助手</span><b>{{ catalog.lists.agents.length }}</b></div>
    <div class="stat"><span class="muted">讲义材料</span><b>{{ catalog.lists.materials.length }}</b></div>
    <div class="stat"><span class="muted">{{ session.teacher ? '待确认知识缺口' : '我的错题' }}</span><b>{{ session.teacher ? catalog.lists.gaps.filter(gap => gap.state === 'pending').length : catalog.lists.wrong.length }}</b></div>
  </div>
  <section class="card">
    <h2>{{ session.teacher ? '从一份讲义开始' : '今天想学些什么' }}</h2>
    <p class="muted">{{ session.teacher ? '上传讲义，绑定学习助手；学生未能获得答案的问题会汇总到知识缺口，审核后可以补充材料。' : '选择学习助手查阅本班讲义，或打开自己的作业。回答引用的讲义可以查看原始片段。' }}</p>
    <div class="row">
      <el-button type="primary" @click="router.push('/conversations')">进入学习助手</el-button>
      <el-button @click="router.push(session.teacher ? '/materials' : '/assignments')">{{ session.teacher ? '管理讲义' : '查看作业' }}</el-button>
    </div>
  </section>
  <div class="grid">
    <section class="card">
      <h2>本班应用</h2>
      <div v-for="agent in catalog.lists.agents" :key="agent.id" class="list-item"><b>{{ agent.name }}</b><p class="muted">已绑定 {{ agent.material_ids.length }} 份材料 · {{ agent.skill_ids.length }} 项技能</p></div>
    </section>
    <section class="card">
      <h2>最近的作业</h2>
      <div v-for="assignment in catalog.lists.assignments.slice(0, 5)" :key="assignment.id" class="list-item"><b>{{ assignment.title }}</b><p class="muted">截止 {{ date(assignment.deadline) }} · {{ state(assignment.state) }}</p></div>
      <div v-if="!catalog.lists.assignments.length" class="empty">暂时没有作业</div>
    </section>
  </div>
</template>
