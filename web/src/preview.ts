import { useSession } from './stores/session'
import { useCatalog } from './stores/catalog'

const stamp = '2026-10-28T08:30:00'
const materialText = '分数相加需要先通分，再把分子相加。分母保持不变。\n这是静态预览用的虚构讲义，没有连接服务器。'

const shared = {
  agents: [
    { id: 1, name: '数学学习助手', material_ids: [1], skill_ids: [1], tools: ['lecture_search'], enabled: true },
    { id: 2, name: '语文阅读助手', material_ids: [1], skill_ids: [], tools: ['lecture_search'], enabled: true },
  ],
  templates: [{ id: 1, name: '课堂学习模板', content: '先澄清问题，再根据本班讲义引导学习。资料不足时明确说明。' }],
  skills: [{ id: 1, name: '解题引导', description: '只给下一步提示，不直接给出最终答案。', body: '先询问学生的思路。', enabled: true }],
  materials: [{
    id: 1, title: '第一章 分数运算', active_version_id: 11, preview_text: materialText,
    versions: [{ id: 11, number: 1, state: 'active', created_at: stamp, error: '' }],
  }],
  conversations: [{ id: 7, title: '分数相加要先通分吗？', agent_id: 1 }],
}

const teacherLists = {
  ...shared,
  gaps: [{ id: 3, state: 'pending', heat: 4, question: '通分时分母可以相加吗？', note: '' }],
  assignments: [{ id: 5, title: '参数运算练习', state: 'published', deadline: '2026-11-02T23:00:00' }],
  papers: [{ id: 8, assignment_id: 5, user_id: 21, state: 'ready', question: '计算 (12+7)×2，写出计算过程与结果。', error: '' }],
  submissions: [
    { id: 15, user_id: 21, state: 'reviewed', final_score: 86, ai_score: 80, feedback: '计算过程完整，结果正确。', review_note: '教师确认 AI 初评，并补上步骤分。', answer: '12+7=19，19×2=38', ai_raw: { steps: ['过程', '结果'] } },
    { id: 16, user_id: 22, state: 'graded', final_score: 60, ai_score: 60, feedback: '结果正确，过程缺少通分说明。', review_note: '', answer: '38', ai_raw: { steps: ['结果'] } },
  ],
  weekly: [{
    id: 2, state: 'draft', period_start: '2026-10-26T00:00:00', teacher_comment: '本周提交稳定，通分步骤仍需要课堂再讲一次。',
    facts: { search_count: 18, submission_count: 6, average_score: 82, sample_sufficient: true, score_distribution: { below_60: 1, '60_to_79': 2, '80_plus': 3 } },
  }],
  tasks: [{ id: 'task-1', kind: 'index', target_id: 11, state: 'failed', attempts: 2, error: '静态预览：索引服务未连接' }],
  audit: [{ id: 9, action: 'material.uploaded', created_at: stamp, success: true, request_id: 'preview-request', details: { material_id: 1 } }],
  students: [{ id: 21, username: 'student_a1' }, { id: 22, username: 'student_a2' }],
  wrong: [],
}

const studentLists = {
  ...shared,
  gaps: [], assignments: teacherLists.assignments, papers: teacherLists.papers,
  submissions: [{ id: 15, user_id: 21, state: 'reviewed', final_score: 86, ai_score: 80, feedback: '计算过程完整，结果正确。', review_note: '教师确认 AI 初评，并补上步骤分。', answer: '12+7=19，19×2=38', ai_raw: { steps: ['过程', '结果'] } }],
  weekly: [{ ...teacherLists.weekly[0], state: 'published' }],
  tasks: [], audit: [], students: [],
  wrong: [{ id: 4, submission_id: 16, explanation: '结果写对了，但没有写出通分过程。' }],
}

export function applyPreview(role: 'teacher' | 'student') {
  const session = useSession()
  const catalog = useCatalog()
  session.previewing = true
  session.error = ''
  session.user = role === 'teacher'
    ? { id: 11, username: 'teacher_a', role: 'teacher', class_id: 'A' }
    : { id: 21, username: 'student_a1', role: 'student', class_id: 'A' }
  const source = role === 'teacher' ? teacherLists : studentLists
  for (const [key, value] of Object.entries(source)) catalog.lists[key] = value
}
