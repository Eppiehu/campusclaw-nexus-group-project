export type Row = Record<string, any>

const stateNames: Record<string, string> = {
  pending: '待确认', approved: '审核通过', rejected: '已驳回', indexing: '索引中', filled: '已补入',
  index_failed: '索引失败', active: '生效', superseded: '历史版本', withdrawn: '已撤回', draft: '草稿',
  published: '已发布', issuing: '发卷中', ready: '可作答', frozen: '作答中', submitted: '已提交',
  issue_failed: '发卷失败', queued: '排队中', running: '执行中', succeeded: '已完成', failed: '失败',
  dispatch_failed: '等待重新入队', grading: '批改中', graded: '已批改', grade_failed: '批改失败',
  reviewed: '已复核', generating: '生成中', generation_failed: '生成失败',
}

export const state = (value: string) => stateNames[value] || value
export const date = (value: string) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
export const toolOptions = [
  ['lecture_search', '讲义检索'],
  ['current_assignments', '当前作业'],
  ['my_wrong_questions', '个人错题'],
  ['assignment_rubric', '作业评分规则'],
  ['class_statistics', '班级统计（教师）'],
] as const

export function safeRedirect(value: unknown) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}
