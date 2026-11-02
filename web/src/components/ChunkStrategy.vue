<script setup lang="ts">
import type { ChunkForm } from '../chunkForm'

const chunk = defineModel<ChunkForm>({ required: true })

function set(patch: Partial<ChunkForm>) {
  chunk.value = { ...chunk.value, ...patch }
}
</script>

<template>
  <div class="chunk-box">
    <div class="strategy-option" :class="{ 'is-on': chunk.strategy === 'hierarchy' }" @click="set({ strategy: 'hierarchy' })">
      <b><span class="recommend">推荐</span>按层级分段</b>
      <p class="muted">按 Markdown 标题（#、##、###）把文档分成带标题的章节。某一章超过最大长度时，再按重叠比例切开。适合长文档。</p>
      <div v-if="chunk.strategy === 'hierarchy'" class="strategy-fields" @click.stop>
        <label>分段最大长度<input type="number" min="100" max="2000" :value="chunk.maxChars" @input="set({ maxChars: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>分段重叠度%<input type="number" min="0" max="50" :value="chunk.overlapPct" @input="set({ overlapPct: Number(($event.target as HTMLInputElement).value) })" /></label>
      </div>
    </div>
    <div class="strategy-option" :class="{ 'is-on': chunk.strategy === 'auto' }" @click="set({ strategy: 'auto' })">
      <b>自动分段与清洗</b>
      <p class="muted">优先在空行、换行、句号处断开。最大长度 800 字，重叠 80 字（10%），使用服务器默认值。</p>
    </div>
    <div class="strategy-option" :class="{ 'is-on': chunk.strategy === 'custom' }" @click="set({ strategy: 'custom' })">
      <b>自定义</b>
      <p class="muted">自己指定分段标识符、最大长度、重叠比例，以及入库前的文本清洗。</p>
      <div v-if="chunk.strategy === 'custom'" class="strategy-fields" @click.stop>
        <label>分段标识符
          <select :value="chunk.delimiter" @change="set({ delimiter: ($event.target as HTMLSelectElement).value as ChunkForm['delimiter'] })">
            <option value="blank">空行</option>
            <option value="newline">换行</option>
            <option value="period">句号</option>
          </select>
        </label>
        <label>分段最大长度<input type="number" min="100" max="2000" :value="chunk.maxChars" @input="set({ maxChars: Number(($event.target as HTMLInputElement).value) })" /></label>
        <label>分段重叠度%<input type="number" min="0" max="50" :value="chunk.overlapPct" @input="set({ overlapPct: Number(($event.target as HTMLInputElement).value) })" /></label>
        <fieldset>
          <legend>文本预处理规则</legend>
          <label class="check"><input type="checkbox" :checked="chunk.collapseWS" @change="set({ collapseWS: ($event.target as HTMLInputElement).checked })" />替换掉连续的空格、换行符和制表符</label>
          <label class="check"><input type="checkbox" :checked="chunk.stripURLs" @change="set({ stripURLs: ($event.target as HTMLInputElement).checked })" />删除所有 URL 和电子邮箱地址</label>
        </fieldset>
      </div>
    </div>
  </div>
</template>
