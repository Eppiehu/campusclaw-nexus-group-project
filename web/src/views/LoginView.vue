<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { token } from '../api'
import { safeRedirect } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const loginForm = reactive({ username: '', password: '' })
const selectedDemo = ref('')
const teacherPassword = import.meta.env.VITE_NEXUS_DEMO_TEACHER_PASSWORD
const studentPassword = import.meta.env.VITE_NEXUS_DEMO_STUDENT_PASSWORD
const demoAccounts = [
  { username: 'teacher_a', label: 'A 班教师', password: teacherPassword },
  { username: 'teacher_b', label: 'B 班教师', password: teacherPassword },
  { username: 'student_a1', label: 'A 班学生', password: studentPassword },
  { username: 'student_a2', label: 'A 班学生', password: studentPassword },
  { username: 'student_b1', label: 'B 班学生', password: studentPassword },
].filter(account => account.password)

function selectDemoAccount(username: string) {
  const account = demoAccounts.find(item => item.username === username)
  loginForm.username = account?.username || ''
  loginForm.password = account?.password || ''
}

async function enter() {
  const user = await session.action(async () => {
    const signedIn = await session.login(loginForm.username, loginForm.password)
    await catalog.load()
    return signedIn
  })
  if (!user) return
  loginForm.password = ''
  router.replace(safeRedirect(route.query.redirect))
}

onMounted(async () => {
  if (!token() || session.user) {
    if (session.user) router.replace(safeRedirect(route.query.redirect))
    return
  }
  const user = await session.restore().catch(() => { localStorage.removeItem('nexus-token'); return null })
  if (!user) return
  await catalog.load()
  router.replace(safeRedirect(route.query.redirect))
})
</script>

<template>
  <div class="login-page">
    <section class="login-intro"><div class="eyebrow">CAMPUSCLAW NEXUS</div><h1>让问题回到课堂，<br>让学习留下依据。</h1><p>讲义检索 · 学习助手 · 作业反馈<br>教师与学生共享一个持续完善的知识空间。</p></section>
    <section class="login-box">
      <form class="login-form" @submit.prevent="enter">
        <h2>登录教学平台</h2>
        <p class="muted">使用教师或学生账号进入自己的班级</p>
        <div v-if="session.error" class="error" role="alert">{{ session.error }}</div>
        <template v-if="demoAccounts.length">
          <p class="muted">预置账号，点击后填入用户名和密码</p>
          <div class="demo-accounts">
            <button v-for="account in demoAccounts" :key="account.username" type="button" class="demo-account" :class="{ active: selectedDemo === account.username }" @click="selectDemoAccount(account.username)">
              <b>{{ account.username }}</b><span>{{ account.label }}</span>
            </button>
          </div>
        </template>
        <label for="username">用户名</label>
        <el-input id="username" v-model="loginForm.username" autocomplete="username" placeholder="请输入用户名" />
        <label for="password">密码</label>
        <el-input id="password" v-model="loginForm.password" type="password" show-password autocomplete="current-password" />
        <el-button type="primary" native-type="submit" :loading="session.busy">登录</el-button>
      </form>
    </section>
  </div>
</template>
