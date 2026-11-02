<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => String(route.meta.title || ''))
const icons: Record<string, string> = {
  material: 'fa-book-open',
  'template-new': 'fa-file-lines', template: 'fa-file-lines',
  'skill-edit': 'fa-pen', skill: 'fa-wand-magic-sparkles',
  'app-new': 'fa-puzzle-piece', app: 'fa-puzzle-piece',
  'assignment-new': 'fa-clipboard-check', 'assignment-edit': 'fa-clipboard-check', assignment: 'fa-clipboard-check',
  'assignment-submission': 'fa-pen-to-square', 'assignment-answer': 'fa-pen-to-square',
}
const icon = computed(() => icons[String(route.name || '').replace(/^preview-/, '')] || 'fa-file-lines')
defineEmits<{ back: [] }>()
</script>

<template>
  <div class="subhead">
    <el-button class="page-back" text @click="$emit('back')"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i><slot>返回</slot></el-button>
    <h2 class="subtitle"><i class="fa-solid" :class="icon" aria-hidden="true"></i>{{ title }}</h2>
  </div>
</template>
