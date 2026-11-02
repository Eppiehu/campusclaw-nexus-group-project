<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{ accept: string, label: string, hint: string }>()
const model = defineModel<File>()
const dragging = ref(false)
let depth = 0

function allowed(file: File) {
  const rules = props.accept.split(',').map(item => item.trim().toLowerCase()).filter(Boolean)
  const name = file.name.toLowerCase()
  return rules.some(rule => rule.startsWith('.') ? name.endsWith(rule) : file.type === rule)
}

function choose(file: File | undefined) {
  if (!file) return
  if (!allowed(file)) {
    ElMessage.warning('文件类型不符合要求')
    return
  }
  model.value = file
}

function onChange(event: Event) {
  const input = event.target as HTMLInputElement
  choose(input.files?.[0])
  input.value = ''
}

function onDrop(event: DragEvent) {
  depth = 0
  dragging.value = false
  choose(event.dataTransfer?.files?.[0])
}

function enter() {
  depth += 1
  dragging.value = true
}

function leave() {
  depth = Math.max(0, depth - 1)
  dragging.value = depth > 0
}

function sizeLabel(file: File) {
  if (file.size < 1024) return `${file.size} B`
  if (file.size < 1024 * 1024) return `${(file.size / 1024).toFixed(1)} KB`
  return `${(file.size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div class="file-drop" :class="{ dragging, filled: !!model }">
    <input type="file" :accept="accept" :aria-label="label" @change="onChange" @dragenter.prevent="enter" @dragover.prevent="enter" @dragleave.prevent="leave" @drop.prevent="onDrop" />
    <span class="file-drop-title">{{ model?.name || '将文件拖到此处，或点击上传' }}</span>
    <span class="file-drop-hint">{{ model ? sizeLabel(model) : hint }}</span>
  </div>
</template>
