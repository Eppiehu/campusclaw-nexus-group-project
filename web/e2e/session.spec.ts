import { expect, test, type Page } from '@playwright/test'
import { e2ePassword } from './target'

const teacherUser = process.env.E2E_TEACHER_USER?.trim() || 'teacher_a'
const studentUser = process.env.E2E_STUDENT_USER?.trim() || 'student_a1'
const teacherPassword = e2ePassword('E2E_TEACHER_PASSWORD')
const studentPassword = e2ePassword('E2E_STUDENT_PASSWORD')

async function signIn(page: Page, username: string, password: string) {
  await page.locator('input#username, #username input').fill(username)
  await page.locator('input#password, #password input').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
}

async function login(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.evaluate(() => localStorage.removeItem('nexus-token'))
  await page.goto('/login')
  await signIn(page, username, password)
  await expect(page.getByRole('heading', { name: '工作台' })).toBeVisible()
}

test('未登录访问受保护页面时进入登录', async ({ page }) => {
  await page.goto('/materials')
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByRole('heading', { name: '登录教学平台' })).toBeVisible()
})

test('登录后回到原先请求的页面', async ({ page }) => {
  await page.goto('/assignments')
  await expect(page).toHaveURL(/\/login\?redirect=/)
  await signIn(page, studentUser, studentPassword)
  await expect(page).toHaveURL(/\/assignments$/)
  await expect(page.getByRole('heading', { name: '作业与批改' })).toBeVisible()
})

test('教师与学生看到不同导航，并能退出', async ({ page }) => {
  await login(page, teacherUser, teacherPassword)
  await expect(page.getByRole('link', { name: '应用与技能' })).toBeVisible()
  await expect(page.getByRole('link', { name: '后台任务' })).toBeVisible()
  await page.getByRole('button', { name: '退出登录' }).first().click()
  await expect(page.getByRole('heading', { name: '登录教学平台' })).toBeVisible()

  await login(page, studentUser, studentPassword)
  await expect(page.getByRole('link', { name: '学习助手' })).toBeVisible()
  await expect(page.getByRole('link', { name: '应用与技能' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: '知识缺口' })).toHaveCount(0)
})

test('错误口令显示服务端返回的失败说明', async ({ page }) => {
  await page.goto('/login')
  await page.evaluate(() => localStorage.removeItem('nexus-token'))
  await page.goto('/login')
  await signIn(page, teacherUser, `${teacherPassword}-wrong`)
  await expect(page.getByText('用户名或密码错误')).toBeVisible()
})

test('刷新后仍停留在讲义页', async ({ page }) => {
  await login(page, teacherUser, teacherPassword)
  await page.getByRole('link', { name: '讲义知识库' }).click()
  await expect(page).toHaveURL(/\/materials$/)
  await page.reload()
  await expect(page).toHaveURL(/\/materials$/)
  await expect(page.getByRole('heading', { name: '讲义知识库' })).toBeVisible()
  await expect(page.getByText(teacherUser).first()).toBeVisible()
})

test('学生直接打开任务页时看到服务端拒绝', async ({ page }) => {
  await login(page, studentUser, studentPassword)
  await page.goto('/jobs')
  await expect(page.getByRole('heading', { name: '后台任务' })).toBeVisible()
  await expect(page.getByText('权限不足')).toBeVisible()
})
