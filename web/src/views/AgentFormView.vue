<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { toolOptions, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import Subhead from '../components/Subhead.vue'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const missing = ref(false)
const externalTools = ref<Row[]>([])
const unavailableTools = computed(() => (form.tools as string[]).filter(name => !toolOptions.some(t => t[0] === name) && !externalTools.value.some(t => t.binding === name)))
const ready = ref(false)
const isNew = computed(() => route.path.endsWith('/apps/new'))
const agentId = computed(() => isNew.value ? 0 : Number(route.params.id))
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/apps')) : '')
const form = reactive<Row>({ name: '', prompt: '', template_id: null, material_ids: [], skill_ids: [], tools: [], enabled: true })

function blank() {
  return { name: '', prompt: '根据本班讲义引导学习，资料不足时说明。', template_id: null, material_ids: [] as number[], skill_ids: [] as number[], tools: [] as string[], enabled: true }
}

function back() {
  router.push({ path: `${prefix.value}/apps`, query: { tab: 'agents' } })
}

async function load() {
  ready.value = false
  missing.value = false
  if (!session.previewing) await session.action(async () => { externalTools.value = await api('/mcp/tools') })
  if (isNew.value) {
    Object.assign(form, blank())
    ready.value = true
    return
  }
  if (!agentId.value) { missing.value = true; ready.value = true; return }
  if (session.previewing) {
    const row = catalog.lists.agents.find(item => item.id === agentId.value)
    missing.value = !row
    if (row) Object.assign(form, JSON.parse(JSON.stringify(row)))
    ready.value = true
    return
  }
  const row = await session.action(async () => {
    await catalog.load()
    return catalog.lists.agents.find(item => item.id === agentId.value) as Row | undefined
  })
  ready.value = true
  if (!row) { missing.value = true; return }
  Object.assign(form, JSON.parse(JSON.stringify(row)))
}

watch(() => route.fullPath, () => { load() }, { immediate: true })

async function save() {
  const saved = await session.action(async () => {
    const { name, prompt, template_id, material_ids, skill_ids, tools, enabled } = form
    const result = await api(isNew.value ? '/agents' : `/agents/${agentId.value}`, isNew.value ? 'POST' : 'PATCH', { name, prompt, template_id, material_ids, skill_ids, tools, enabled })
    await catalog.load()
    return result
  })
  if (!saved) return
  ElMessage.success('应用已保存')
  back()
}

async function remove() {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后应用不能恢复，使用它的会话也会一并删除。', '删除应用', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/agents/${agentId.value}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) { ElMessage.success('应用已删除'); back() }
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
    <Subhead @back="back">返回应用列表</Subhead>
    <div class="records">
    <p v-if="missing">这个应用当前不可编辑。</p>
    <template v-else>
      <div class="fields">
        <div><label for="agent-name">应用名称</label><el-input id="agent-name" v-model="form.name" maxlength="100" /></div>
        <div><label for="agent-template">提示词模板</label><el-select id="agent-template" v-model="form.template_id" clearable><el-option v-for="template in catalog.lists.templates" :key="template.id" :value="template.id" :label="template.name" /></el-select></div>
        <div class="full"><label for="agent-prompt">应用角色（未绑定模板时使用）</label><el-input id="agent-prompt" v-model="form.prompt" type="textarea" :rows="4" /></div>
        <div><label for="agent-materials">讲义范围</label><el-select id="agent-materials" v-model="form.material_ids" multiple><el-option v-for="material in catalog.lists.materials" :key="material.id" :value="material.id" :label="material.title" /></el-select></div>
        <div><label for="agent-skills">可用技能</label><el-select id="agent-skills" v-model="form.skill_ids" multiple><el-option v-for="skill in catalog.lists.skills" :key="skill.id" :value="skill.id" :label="skill.name" /></el-select></div>
        <div class="full"><label>外部工具</label><el-checkbox-group v-model="form.tools"><el-checkbox v-for="tool in toolOptions" :key="tool[0]" :value="tool[0]">{{ tool[1] }}</el-checkbox></el-checkbox-group></div>
        <div class="full"><label>已测试的 MCP 工具</label><el-checkbox-group v-model="form.tools"><el-checkbox v-for="tool in externalTools" :key="tool.binding" :value="tool.binding">{{ tool.connection }} / {{ tool.name }}</el-checkbox></el-checkbox-group><p class="muted">在“应用与技能”页登记并测试连接；停用或重新配置后需要重新测试。</p></div>
        <div v-if="unavailableTools.length" class="full"><label>失效绑定（取消勾选以移除）</label><el-checkbox-group v-model="form.tools"><el-checkbox v-for="name in unavailableTools" :key="name" :value="name">{{ name }}</el-checkbox></el-checkbox-group></div>
      </div>
      <div class="row" style="margin-top:20px">
        <el-button type="primary" :loading="session.busy" :disabled="!ready" @click="save">保存应用</el-button>
        <el-button @click="back">取消</el-button>
        <el-button v-if="!isNew" type="danger" plain :disabled="!ready" @click="remove">删除</el-button>
      </div>
    </template>
    </div>
    </section>
  </TeacherGate>
</template>
