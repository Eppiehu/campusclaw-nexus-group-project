<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useSession } from '../stores/session'
import { useCatalog } from '../stores/catalog'
import TeacherGate from '../components/TeacherGate.vue'
import FileDrop from '../components/FileDrop.vue'
import { detectSkill } from '../skillPreview'

const route = useRoute()
const router = useRouter()
const session = useSession()
const catalog = useCatalog()
const skillFile = ref<File>()
const skillDialog = ref(false)
const skillSource = ref('')
const skillForm = reactive({ name: '', description: '', body: '' })
const prefix = computed(() => route.path.includes('/preview/') ? route.path.slice(0, route.path.indexOf('/apps')) : '')
const tab = computed({
  get: () => route.query.tab === 'skills' || route.query.tab === 'agents' ? String(route.query.tab) : 'templates',
  set: (value: string) => {
    const next = value === 'templates' ? {} : { tab: value }
    if ((route.query.tab || '') === (next.tab || '')) return
    router.replace({ path: route.path, query: next })
  },
})

function openAgent(id?: number) {
  router.push(id ? `${prefix.value}/apps/${id}` : `${prefix.value}/apps/new`)
}

async function removeAgent(id: number) {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后应用不能恢复，使用它的会话也会一并删除。', '删除应用', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/agents/${id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) ElMessage.success('应用已删除')
  return removed
}

function openSkill(id: number) {
  router.push(`${prefix.value}/apps/skills/${id}`)
}

function editSkill(id: number) {
  router.push(`${prefix.value}/apps/skills/${id}/edit`)
}

async function removeSkill(id: number) {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后技能不能恢复，已绑定的应用也会去掉这项技能。', '删除技能', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/skills/${id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) ElMessage.success('技能已删除')
  return removed
}

function openTemplate(id?: number) {
  router.push(id ? `${prefix.value}/apps/templates/${id}` : `${prefix.value}/apps/templates/new`)
}

async function removeTemplate(id: number) {
  const removed = await session.action(async () => {
    try {
      await ElMessageBox.confirm('删除后模板不能恢复，已选用它的应用会改为不使用模板。', '删除模板', { confirmButtonText: '确定', cancelButtonText: '取消' })
    } catch { return false }
    await api(`/templates/${id}`, 'DELETE')
    await catalog.load()
    return true
  })
  if (removed) ElMessage.success('模板已删除')
  return removed
}

watch(skillFile, async file => {
  if (!file || skillDialog.value) return
  skillSource.value = await file.text()
  Object.assign(skillForm, detectSkill(skillSource.value))
  skillDialog.value = true
})

function closeSkillDialog() {
  skillDialog.value = false
  skillFile.value = undefined
  skillSource.value = ''
}

async function confirmSkill() {
  if (session.previewing) { ElMessage.info('静态预览不会提交到服务器'); closeSkillDialog(); return }
  const saved = await session.action(async () => {
    const result = await api('/skills', 'POST', { name: skillForm.name, description: skillForm.description, body: skillForm.body, source_text: skillSource.value.slice(0, 8000) })
    await catalog.load()
    return result
  })
  if (!saved) return
  closeSkillDialog()
  ElMessage.success('技能已上传')
}
</script>

<template>
  <TeacherGate probe="/students">
    <section class="card fill">
      <el-tabs v-model="tab" class="section-tabs">
        <el-tab-pane name="templates">
          <template #label><i class="fa-solid fa-file-lines" aria-hidden="true"></i>提示词模板</template>
          <el-button type="primary" @click="openTemplate()"><i class="fa-solid fa-plus" aria-hidden="true"></i>新建模板</el-button>
          <div class="tab-list">
            <div v-for="template in catalog.lists.templates" :key="template.id" class="list-item assignment-item">
              <button type="button" class="assignment-open" @click="openTemplate(template.id)">
                <b>{{ template.name }}</b>
              </button>
              <div class="assignment-actions">
                <el-button type="danger" plain @click="removeTemplate(template.id)">删除</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane name="skills">
          <template #label><i class="fa-solid fa-wand-magic-sparkles" aria-hidden="true"></i>技能文件</template>
          <p class="muted">选择 SKILL.md 或 TXT 后先预览，确认标题、适用条件和正文再上传。</p>
          <FileDrop v-model="skillFile" accept=".md,.txt" label="选择技能文件" hint="支持 Markdown 和 TXT，选择后预览" />
          <div class="tab-list with-upload">
            <div v-for="skill in catalog.lists.skills" :key="skill.id" class="list-item assignment-item">
              <button type="button" class="assignment-open" @click="openSkill(skill.id)">
                <b>{{ skill.name }}</b>
                <p class="muted">{{ skill.description }}</p>
                <span class="status-tag" :class="skill.enabled ? 'on' : 'off'">{{ skill.enabled ? '已启用' : '已停用' }}</span>
              </button>
              <div class="assignment-actions">
                <el-button @click="editSkill(skill.id)">编辑</el-button>
                <el-button type="danger" plain @click="removeSkill(skill.id)">删除</el-button>
                <el-switch :model-value="skill.enabled" :aria-label="skill.name + '启用'" @change="session.action(async () => { await api('/skills/' + skill.id, 'PATCH', { enabled: !skill.enabled }); await catalog.load() })" />
              </div>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane name="agents">
          <template #label><i class="fa-solid fa-puzzle-piece" aria-hidden="true"></i>应用</template>
          <el-button type="primary" @click="openAgent()"><i class="fa-solid fa-plus" aria-hidden="true"></i>创建应用</el-button>
          <div class="tab-list">
            <div v-for="agent in catalog.lists.agents" :key="agent.id" class="list-item assignment-item">
              <button type="button" class="assignment-open" @click="openAgent(agent.id)">
                <b>{{ agent.name }}</b>
                <p class="muted">{{ agent.material_ids.length }} 份讲义 · {{ agent.skill_ids.length }} 个技能 · {{ agent.tools.length }} 项工具</p>
                <span class="status-tag" :class="agent.enabled ? 'on' : 'off'">{{ agent.enabled ? '已启用' : '已停用' }}</span>
              </button>
              <div class="assignment-actions">
                <el-button @click="openAgent(agent.id)">编辑</el-button>
                <el-button type="danger" plain @click="removeAgent(agent.id)">删除</el-button>
                <el-switch :model-value="agent.enabled" :aria-label="agent.name + (agent.enabled ? '已启用' : '已停用')" @change="session.action(async () => { await api('/agents/' + agent.id, 'PATCH', { enabled: !agent.enabled }); await catalog.load() })" />
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </TeacherGate>
  <el-dialog :model-value="skillDialog" title="上传技能" width="680px" :close-on-click-modal="false" @close="closeSkillDialog">
    <label for="skill-name">技能标题</label>
    <el-input id="skill-name" v-model="skillForm.name" maxlength="64" placeholder="自动识别，可修改" />
    <label for="skill-condition">适用条件</label>
    <el-input id="skill-condition" v-model="skillForm.description" type="textarea" :rows="3" maxlength="2000" placeholder="自动识别，可修改" />
    <label for="skill-body">正文</label>
    <el-input id="skill-body" v-model="skillForm.body" type="textarea" :rows="8" maxlength="2000" placeholder="自动识别，可修改" />
    <template #footer>
      <el-button @click="closeSkillDialog">取消</el-button>
      <el-button type="primary" @click="confirmSkill">确定</el-button>
    </template>
  </el-dialog>
</template>
