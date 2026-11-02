<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { api } from '../api'
import type { Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import Subhead from '../components/Subhead.vue'
import VariableEditor from '../components/VariableEditor.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/assignments')) : '')
const isNew = computed(() => /\/assignments\/new$/.test(route.path))
const assignmentId = computed(() => Number(route.params.id))
const ready = ref(false)
const missing = ref(false)
const blocked = ref(false)
const parameters = ref<Parameter[]>([])
const templateEditor = ref<{ insert: (name: string) => void } | null>(null)
const expressionEditor = ref<{ insert: (name: string) => void } | null>(null)
const adding = ref(false)
const parameterError = ref('')
const draft = reactive<{ name: string, min: number | null, max: number | null }>({ name: '', min: 0, max: 10 })

type Parameter = { name: string, min: number, max: number }
const nameHint = '变量名须以小写英文字母开头，只能包含小写字母、数字和下划线，最长 16 个字符。'

function blank() {
  return {
    title: '',
    question_template: '',
    answer_expression: '',
    answer_hint: '',
    rubric: '',
    deadline: localDeadline(new Date(Date.now() + 86400000 * 3).toISOString()),
  }
}

const form = reactive(blank())

function localDeadline(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function rubricText(value: unknown) {
  if (typeof value === 'string') return value
  if (!Array.isArray(value)) return ''
  return value.map(item => typeof item === 'string' ? item : String((item as Row)?.name || '')).filter(Boolean).join('、')
}

function fill(row: Row) {
  Object.assign(form, {
    title: row.title || '',
    question_template: row.question_template || '',
    answer_expression: row.answer_expression || '',
    answer_hint: row.answer_hint || '',
    rubric: rubricText(row.rubric),
    deadline: localDeadline(String(row.deadline || '')),
  })
  const ranges = row.ranges && typeof row.ranges === 'object' ? row.ranges as Record<string, number[]> : {}
  parameters.value = Object.entries(ranges).map(([name, bounds]) => ({ name, min: Number(bounds?.[0]), max: Number(bounds?.[1]) }))
  adding.value = false
  parameterError.value = ''
}

function resetParameters() {
  parameters.value = []
  adding.value = false
  parameterError.value = ''
}

function parameterMessage(name: string, min: number | null, max: number | null, others: string[]) {
  const trimmed = name.trim()
  if (!/^[a-z][a-z0-9_]{0,15}$/.test(trimmed)) return nameHint
  if (others.includes(trimmed)) return `变量名「${trimmed}」已经用过。`
  if (min == null || max == null || !Number.isInteger(min) || !Number.isInteger(max)) return '最小和最大须为整数。'
  if (min < -10000 || max > 10000 || min > max) return '范围须满足 -10000 ≤ 最小 ≤ 最大 ≤ 10000。'
  return ''
}

function beginParameter() {
  draft.name = ''
  draft.min = 0
  draft.max = 10
  parameterError.value = ''
  adding.value = true
}

function confirmParameter() {
  const message = parameterMessage(draft.name, draft.min, draft.max, parameters.value.map(item => item.name))
  parameterError.value = message
  if (message) return
  parameters.value.push({ name: draft.name.trim(), min: Number(draft.min), max: Number(draft.max) })
  adding.value = false
  parameterError.value = ''
}

function cancelParameter() {
  adding.value = false
  parameterError.value = ''
}

function removeParameter(name: string) {
  parameters.value = parameters.value.filter(item => item.name !== name)
}

function back() {
  router.push(isNew.value ? `${prefix.value}/assignments` : `${prefix.value}/assignments/${assignmentId.value}`)
}

async function load() {
  ready.value = false
  missing.value = false
  blocked.value = false
  if (isNew.value) {
    Object.assign(form, blank())
    resetParameters()
    ready.value = true
    return
  }
  const apply = (row: Row | undefined) => {
    if (!row) { missing.value = true; return }
    if (!['draft', 'withdrawn'].includes(String(row.state))) { blocked.value = true; return }
    fill(row)
  }
  if (session.previewing) {
    apply(catalog.lists.assignments.find(item => item.id === assignmentId.value) as Row | undefined)
    ready.value = true
    return
  }
  const row = await session.action(async () => {
    await catalog.load()
    return catalog.lists.assignments.find(item => item.id === assignmentId.value) as Row | undefined
  })
  ready.value = true
  if (row === undefined && session.error) return
  apply(row)
}

watch(() => route.fullPath, () => { load() }, { immediate: true })

async function save() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); return }
  if (adding.value) { ElMessage.warning('请先确定正在填写的参数，或取消添加。'); return }
  if (!parameters.value.length || parameters.value.length > 5) { ElMessage.warning('参数数量须为 1 到 5 个。'); return }
  const names = new Set(parameters.value.map(item => item.name))
  const placeholders = [...new Set([...form.question_template.matchAll(/\{([^{}]+)\}/g)].map(item => item[1]))]
  const missing = placeholders.find(token => !names.has(token))
  if (missing) { ElMessage.warning(`题干中的变量 ${missing} 还没有确定范围。`); return }
  const unused = parameters.value.find(item => !form.question_template.includes(`{${item.name}}`))
  if (unused) { ElMessage.warning(`变量 ${unused.name} 已不在题干中。要修改它，请删除后重新添加。`); return }
  const ranges = Object.fromEntries(parameters.value.map(item => [item.name, [item.min, item.max]]))
  const rubric = form.rubric.trim()
  if (!rubric) { ElMessage.warning('请填写评分说明'); return }
  const saved = await session.action(async () => {
    const result = await api(isNew.value ? '/assignments' : `/assignments/${assignmentId.value}`, isNew.value ? 'POST' : 'PATCH', {
      ...form, ranges, rubric, deadline: new Date(form.deadline).toISOString(),
    })
    await catalog.load()
    return result
  })
  if (!saved) return
  ElMessage.success(isNew.value ? '作业草稿已保存' : '作业已保存')
  if (isNew.value) router.push(`${prefix.value}/assignments`)
  else router.push(`${prefix.value}/assignments/${saved.id || assignmentId.value}`)
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="missing ? router.push(`${prefix}/assignments`) : back()">{{ isNew || missing ? '返回作业列表' : '返回题目' }}</Subhead>
    <div class="records">
    <p v-if="!ready" class="muted">正在读取作业…</p>
    <p v-else-if="missing">这个作业当前不可编辑。</p>
    <p v-else-if="blocked">已发布的作业要先撤回，才能编辑。</p>
    <template v-else>
      <div class="fields assignment-form">
        <div class="field"><label for="assignment-title">作业名称</label><el-input id="assignment-title" v-model="form.title" maxlength="200" placeholder="例如：参数运算练习" /></div>
        <div class="field"><label for="assignment-deadline">截止时间</label><el-config-provider :locale="zhCn"><el-date-picker id="assignment-deadline" v-model="form.deadline" type="datetime" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DDTHH:mm" placeholder="选择截止时间" :show-confirm="true" :clearable="false" /></el-config-provider></div>
        <div class="field full">
          <label>确定参数</label>
          <p class="field-hint">先确定变量名和范围。题干和答案表达式上方会列出可用变量，点击即可插入到光标处。已确定的参数不能直接改，要修改就先删除再重新添加。</p>
          <p v-if="!parameters.length && !adding" class="field-hint">还没有参数。</p>
          <div v-if="parameters.length" class="parameter-list">
            <div v-for="item in parameters" :key="item.name" class="parameter-row">
              <span class="variable-option"><span class="variable-token">{{ item.name }}</span><span class="parameter-range">{{ item.min }} 到 {{ item.max }}</span></span>
              <el-button type="danger" plain @click="removeParameter(item.name)">删除</el-button>
            </div>
          </div>
          <p v-if="parameterError" class="field-error">{{ parameterError }}</p>
          <div v-if="adding" class="parameter-draft">
            <div><label for="parameter-name">变量名</label><el-input id="parameter-name" v-model="draft.name" maxlength="16" @input="parameterError = ''" /></div>
            <div><label for="parameter-min">最小</label><el-input-number id="parameter-min" v-model="draft.min" :min="-10000" :max="10000" :step="1" :precision="0" controls-position="right" /></div>
            <div><label for="parameter-max">最大</label><el-input-number id="parameter-max" v-model="draft.max" :min="-10000" :max="10000" :step="1" :precision="0" controls-position="right" /></div>
            <div class="row">
              <el-button type="primary" @click="confirmParameter">确定</el-button>
              <el-button @click="cancelParameter">取消</el-button>
            </div>
          </div>
          <el-button v-else :disabled="parameters.length >= 5" @click="beginParameter">添加变量</el-button>
        </div>
        <div class="field full">
          <label for="assignment-template">题干模板</label>
          <div class="available-variables">
            <span class="sub-label">可用变量</span>
            <div v-if="parameters.length" class="variable-shortcuts">
              <button v-for="item in parameters" :key="item.name" type="button" class="variable-token variable-insert" @mousedown.prevent @click="templateEditor?.insert(item.name)">{{ item.name }}</button>
            </div>
            <span v-else class="field-hint">还没有可用变量。</span>
          </div>
          <VariableEditor id="assignment-template" ref="templateEditor" v-model="form.question_template" mode="template" :names="parameters.map(item => item.name)" :maxlength="4000" multiline placeholder="计算 (a+b)×2，写出计算过程与结果。" />
        </div>
        <div class="field full"><label for="assignment-hint">作答提示</label><el-input id="assignment-hint" v-model="form.answer_hint" type="textarea" :rows="3" maxlength="2000" placeholder="给学生的作答提示。学生作答时可以查看，不作为评分依据。" /></div>
        <div class="field full">
          <label for="assignment-expression">服务端答案表达式</label>
          <div class="available-variables">
            <span class="sub-label">可用变量</span>
            <div v-if="parameters.length" class="variable-shortcuts">
              <button v-for="item in parameters" :key="item.name" type="button" class="variable-token variable-insert" @mousedown.prevent @click="expressionEditor?.insert(item.name)">{{ item.name }}</button>
            </div>
            <span v-else class="field-hint">还没有可用变量。</span>
          </div>
          <VariableEditor id="assignment-expression" ref="expressionEditor" v-model="form.answer_expression" mode="expression" :names="parameters.map(item => item.name)" :maxlength="200" placeholder="(a+b)*2" />
        </div>
        <div class="field full"><label for="assignment-rubric">评分说明</label><el-input id="assignment-rubric" v-model="form.rubric" type="textarea" :rows="4" maxlength="2000" placeholder="用一段话说明希望关注的方面。AI 会据此自行判断并给出 0 到 100 分，不按固定分项计分。" /></div>
      </div>
      <div class="row assignment-form-actions">
        <el-button type="primary" :loading="session.busy" @click="save">{{ isNew ? '保存草稿' : '保存修改' }}</el-button>
        <el-button @click="back">取消</el-button>
      </div>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
