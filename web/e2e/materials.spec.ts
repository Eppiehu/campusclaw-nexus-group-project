import { expect, test, type Page } from '@playwright/test'
import { e2ePassword } from './target'

const teacherUser = process.env.E2E_TEACHER_USER?.trim() || 'teacher_a'
const studentA = process.env.E2E_STUDENT_USER?.trim() || 'student_a1'
const studentB = process.env.E2E_STUDENT_B_USER?.trim() || 'student_b1'
const teacherPassword = e2ePassword('E2E_TEACHER_PASSWORD')
const studentPassword = e2ePassword('E2E_STUDENT_PASSWORD')

async function login(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.evaluate(() => localStorage.removeItem('nexus-token'))
  await page.goto('/login')
  await page.locator('input#username, #username input').fill(username)
  await page.locator('input#password, #password input').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page.getByRole('heading', { name: '工作台' })).toBeVisible()
}

test('学生上传讲义时展示服务端 403', async ({ page }) => {
  await login(page, studentA, studentPassword)
  await page.goto('/materials/new')
  await page.getByLabel('选择讲义文件').setInputFiles({ name: 'lecture.md', mimeType: 'text/markdown', buffer: Buffer.from('学生不应上传成功\n') })
  const dialog = page.getByRole('dialog', { name: '上传讲义' })
  await expect(dialog).toBeVisible()
  await dialog.locator('input#material-title, #material-title input').fill('学生越权上传')
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.error').filter({ hasText: '权限不足' })).toBeVisible()
})

test('A 班讲义正文可见，B 班看不到同一标题', async ({ page }) => {
  test.setTimeout(90_000)
  const title = `隔离讲义${Date.now()}`
  const sentence = `这是只属于A班的虚构讲义正文${Date.now()}`
  await login(page, teacherUser, teacherPassword)
  await page.goto('/materials')
  await page.getByLabel('选择讲义文件').setInputFiles({ name: 'lecture.md', mimeType: 'text/markdown', buffer: Buffer.from(`# 讲义\n\n${sentence}\n`) })
  const dialog = page.getByRole('dialog', { name: '上传讲义' })
  await expect(dialog).toBeVisible()
  await dialog.locator('input#material-title, #material-title input').fill(title)
  await page.getByRole('button', { name: '下一步' }).click()
  await expect(page.getByRole('dialog', { name: '加入应用讲义范围' })).toBeVisible()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.list-item', { hasText: title })).toBeVisible()

  await login(page, studentB, studentPassword)
  await page.goto('/materials')
  await expect(page.locator('.list-item', { hasText: title })).toHaveCount(0)

  await login(page, studentA, studentPassword)
  await page.goto('/materials')
  const item = page.locator('.list-item', { hasText: title })
  await expect(item.getByRole('button', { name: title })).toBeVisible({ timeout: 60_000 })
  await item.getByRole('button', { name: title }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
  await expect(page.locator('.material-body')).toContainText(sentence)
})
