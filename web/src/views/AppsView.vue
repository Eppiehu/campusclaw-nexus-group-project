<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { toolOptions, type Row } from '../format'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'

const session = useSession()
const catalog = useCatalog()
const templateForm = reactive({ id: 0, name: '', content: '' })
const skillFile = ref<File>()
const agentForm = reactive<Row>({ id: 0, name: '', prompt: '根据本班讲义引导学习，资料不足时说明。', template_id: null, material_ids: [], skill_ids: [], tools: [], enabled: true })

function fileChange(event: Event) { skillFile.value = (event.target as HTMLInputElement).files?.[0] }
function editAgent(row: Row) { Object.assign(agentForm, JSON.parse(JSON.stringify(row))); document.getElementById('agent-form')?.scrollIntoView({ behavior: 'smooth' }) }

async function saveTemplate() {
  await session.action(async () => {
    await api('/templates' + (templateForm.id ? '/' + templateForm.id : ''), templateForm.id ? 'PATCH' : 'POST', { name: templateForm.name, content: templateForm.content })
    Object.assign(templateForm, { id: 0, name: '', content: '' })
    await catalog.load()
    ElMessage.success('模板已保存')
  })
}
async function uploadSkill() {
  await session.action(async () => {
    if (!skillFile.value) throw new Error('请选择技能文件')
    const form = new FormData()
    form.append('file', skillFile.value)
    await api('/skills', 'POST', form)
    await catalog.load()
    ElMessage.success('技能已上传')
  })
}
async function saveAgent() {
  await session.action(async () => {
    const { id, name, prompt, template_id, material_ids, skill_ids, tools, enabled } = agentForm
    await api('/agents' + (id ? '/' + id : ''), id ? 'PATCH' : 'POST', { name, prompt, template_id, material_ids, skill_ids, tools, enabled })
    await catalog.load()
    ElMessage.success('应用已保存')
  })
}
</script>

<template>
  <TeacherGate probe="/students">
    <div class="grid">
      <section class="card">
        <h2>提示词模板</h2>
        <label>名称</label><el-input v-model="templateForm.name" />
        <label>模板正文</label><el-input v-model="templateForm.content" type="textarea" :rows="5" />
        <el-button type="primary" style="margin-top:12px" @click="saveTemplate">保存模板</el-button>
        <div v-for="template in catalog.lists.templates" :key="template.id" class="list-item">
          <div class="row spread"><b>{{ template.name }}</b><el-button text @click="Object.assign(templateForm, template)">编辑</el-button></div>
          <p class="muted">{{ template.content }}</p>
        </div>
      </section>
      <section class="card">
        <h2>技能文件</h2>
        <p class="muted">标准 SKILL.md：YAML 中填写 name 和 description，随后用 Markdown 描述技能行为。</p>
        <input type="file" accept=".md,.txt" aria-label="选择技能文件" @change="fileChange" />
        <el-button type="primary" style="margin-top:12px" @click="uploadSkill">上传技能</el-button>
        <div v-for="skill in catalog.lists.skills" :key="skill.id" class="list-item">
          <div class="row spread"><b>{{ skill.name }}</b><el-switch :model-value="skill.enabled" :aria-label="skill.name + '启用'" @change="session.action(async () => { await api('/skills/' + skill.id, 'PATCH', { enabled: !skill.enabled }); await catalog.load() })" /></div>
          <p class="muted">{{ skill.description }}</p>
          <details><summary class="muted">技能正文</summary><pre class="pre">{{ skill.body }}</pre></details>
        </div>
      </section>
    </div>
    <section id="agent-form" class="card">
      <h2>{{ agentForm.id ? '编辑应用' : '创建应用' }}</h2>
      <div class="fields">
        <div><label>应用名称</label><el-input v-model="agentForm.name" /></div>
        <div><label>提示词模板</label><el-select v-model="agentForm.template_id" clearable><el-option v-for="template in catalog.lists.templates" :key="template.id" :value="template.id" :label="template.name" /></el-select></div>
        <div class="full"><label>应用角色（未绑定模板时使用）</label><el-input v-model="agentForm.prompt" type="textarea" :rows="2" /></div>
        <div><label>讲义范围</label><el-select v-model="agentForm.material_ids" multiple><el-option v-for="material in catalog.lists.materials" :key="material.id" :value="material.id" :label="material.title" /></el-select></div>
        <div><label>可用技能</label><el-select v-model="agentForm.skill_ids" multiple><el-option v-for="skill in catalog.lists.skills" :key="skill.id" :value="skill.id" :label="skill.name" /></el-select></div>
        <div class="full"><label>外部工具</label><el-checkbox-group v-model="agentForm.tools"><el-checkbox v-for="tool in toolOptions" :key="tool[0]" :value="tool[0]">{{ tool[1] }}</el-checkbox></el-checkbox-group></div>
      </div>
      <div class="row" style="margin-top:20px">
        <el-button type="primary" @click="saveAgent">保存应用</el-button>
        <el-button @click="Object.assign(agentForm, { id: 0, name: '', template_id: null, material_ids: [], skill_ids: [], tools: [], enabled: true })">新建</el-button>
      </div>
    </section>
    <section class="card">
      <div v-for="agent in catalog.lists.agents" :key="agent.id" class="list-item row spread">
        <div><b>{{ agent.name }}</b><p class="muted">{{ agent.material_ids.length }} 份讲义 · {{ agent.skill_ids.length }} 个技能 · {{ agent.tools.length }} 项工具</p></div>
        <div>
          <el-button @click="editAgent(agent)">编辑</el-button>
          <el-button text @click="session.action(async () => { await api('/agents/' + agent.id, 'PATCH', { enabled: !agent.enabled }); await catalog.load() })">{{ agent.enabled ? '停用' : '启用' }}</el-button>
        </div>
      </div>
    </section>
  </TeacherGate>
</template>
