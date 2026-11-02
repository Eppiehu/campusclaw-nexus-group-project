<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { date, state } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import { useChat } from '../stores/chat'

const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const chat = useChat()

function openAgent(id: number) {
  if (session.teacher) {
    router.push(`/apps/${id}`)
    return
  }
  const agent = catalog.lists.agents.find(item => item.id === id)
  if (!agent?.enabled) {
    ElMessage.warning('这个学习助手已停用')
    return
  }
  chat.draft(id)
  if (session.previewing) ElMessage.info('静态预览不会连接服务器')
  router.push('/conversations')
}

function openAssignment(id: number) {
  router.push(`/assignments/${id}`)
}
</script>

<template>
  <div class="stats">
    <div class="stat"><span class="muted"><i class="fa-solid fa-comments" aria-hidden="true"></i>学习助手</span><b>{{ catalog.lists.agents.length }}</b></div>
    <div class="stat"><span class="muted"><i class="fa-solid fa-book-open" aria-hidden="true"></i>讲义材料</span><b>{{ catalog.lists.materials.length }}</b></div>
    <div class="stat"><span class="muted"><i class="fa-solid" :class="session.teacher ? 'fa-lightbulb' : 'fa-circle-question'" aria-hidden="true"></i>{{ session.teacher ? '待确认知识缺口' : '我的错题' }}</span><b>{{ session.teacher ? catalog.lists.gaps.filter(gap => gap.state === 'pending').length : catalog.lists.wrong.length }}</b></div>
  </div>
  <section class="card">
    <h2>{{ session.teacher ? '从一份讲义开始' : '今天想学些什么' }}</h2>
    <p class="muted">{{ session.teacher ? '上传讲义，绑定学习助手；学生未能获得答案的问题会汇总到知识缺口，审核后可以补充材料。' : '选择学习助手查阅本班讲义，或打开自己的作业。回答引用的讲义可以查看原始片段。' }}</p>
    <div class="row">
      <el-button type="primary" @click="router.push('/conversations')"><i class="fa-solid fa-comments" aria-hidden="true"></i>进入学习助手</el-button>
      <el-button @click="router.push(session.teacher ? '/materials' : '/assignments')"><i class="fa-solid" :class="session.teacher ? 'fa-book-open' : 'fa-clipboard-check'" aria-hidden="true"></i>{{ session.teacher ? '管理讲义' : '查看作业' }}</el-button>
    </div>
  </section>
  <div class="grid fill">
    <section class="card">
      <h2><i class="fa-solid fa-puzzle-piece" aria-hidden="true"></i>本班应用</h2>
      <div class="records"><button v-for="agent in catalog.lists.agents" :key="agent.id" type="button" class="list-item overview-open" @click="openAgent(agent.id)"><b>{{ agent.name }}</b><p class="muted">已绑定 {{ agent.material_ids.length }} 份材料 · {{ agent.skill_ids.length }} 项技能</p></button></div>
    </section>
    <section class="card">
      <h2><i class="fa-solid fa-clipboard-check" aria-hidden="true"></i>最近的作业</h2>
      <div class="records">
        <button v-for="assignment in catalog.lists.assignments.slice(0, 5)" :key="assignment.id" type="button" class="list-item overview-open" @click="openAssignment(assignment.id)"><b>{{ assignment.title }}</b><p class="muted">截止 {{ date(assignment.deadline) }} · {{ state(assignment.state) }}</p></button>
        <div v-if="!catalog.lists.assignments.length" class="empty">暂时没有作业</div>
      </div>
    </section>
  </div>
</template>
