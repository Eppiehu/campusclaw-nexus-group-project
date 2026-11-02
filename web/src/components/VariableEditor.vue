<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{
  id: string
  modelValue: string
  names: string[]
  mode: 'template' | 'expression'
  maxlength: number
  placeholder: string
  multiline?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [string] }>()
const editor = ref<HTMLElement | null>(null)
let savedRange: Range | null = null

function names() {
  return props.names.filter(name => /^[a-z][a-z0-9_]{0,15}$/.test(name))
}

function token(name: string) {
  const span = document.createElement('span')
  span.className = 'variable-token'
  span.contentEditable = 'false'
  span.dataset.variable = name
  span.textContent = name
  return span
}

function encoded(name: string) {
  return props.mode === 'template' ? `{${name}}` : name
}

function paint(value: string) {
  const root = editor.value
  if (!root) return
  root.replaceChildren()
  const known = names()
  if (props.mode === 'template') {
    const pattern = /\{([a-z][a-z0-9_]{0,15})\}/g
    let last = 0
    for (const match of value.matchAll(pattern)) {
      const index = match.index ?? 0
      if (index > last) root.append(document.createTextNode(value.slice(last, index)))
      root.append(known.includes(match[1]) ? token(match[1]) : document.createTextNode(match[0]))
      last = index + match[0].length
    }
    if (last < value.length) root.append(document.createTextNode(value.slice(last)))
    return
  }
  if (!known.length) {
    if (value) root.append(document.createTextNode(value))
    return
  }
  const pattern = new RegExp(`(?<![A-Za-z0-9_])(${known.slice().sort((a, b) => b.length - a.length).map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})(?![A-Za-z0-9_])`, 'g')
  let last = 0
  for (const match of value.matchAll(pattern)) {
    const index = match.index ?? 0
    if (index > last) root.append(document.createTextNode(value.slice(last, index)))
    root.append(token(match[1]))
    last = index + match[0].length
  }
  if (last < value.length) root.append(document.createTextNode(value.slice(last)))
}

function serialize(root: Node) {
  let text = ''
  root.childNodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE) text += node.textContent || ''
    else if (node instanceof HTMLBRElement) text += '\n'
    else if (node instanceof HTMLElement && node.dataset.variable) text += encoded(node.dataset.variable)
    else if (node instanceof HTMLElement) {
      if ((node.tagName === 'DIV' || node.tagName === 'P') && text && !text.endsWith('\n')) text += '\n'
      text += serialize(node)
    }
  })
  return text.replace(/\u00a0/g, ' ').replace(/\u200b/g, '')
}

function remember() {
  const selection = window.getSelection()
  if (!selection?.rangeCount || !editor.value?.contains(selection.anchorNode)) return
  savedRange = selection.getRangeAt(0).cloneRange()
}

function caretOffset() {
  const root = editor.value
  const selection = window.getSelection()
  if (!root || !selection?.rangeCount || !root.contains(selection.anchorNode)) return null
  const probe = document.createRange()
  probe.selectNodeContents(root)
  probe.setEnd(selection.getRangeAt(0).endContainer, selection.getRangeAt(0).endOffset)
  const holder = document.createElement('div')
  holder.append(probe.cloneContents())
  return serialize(holder).length
}

function placeCaret(offset: number) {
  const root = editor.value
  if (!root) return
  let remaining = offset
  const select = (node: Node, at: number, after = false) => {
    const range = document.createRange()
    if (after) range.setStartAfter(node)
    else range.setStart(node, at)
    range.collapse(true)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    savedRange = range.cloneRange()
  }
  const walk = (node: Node): boolean => {
    if (node.nodeType === Node.TEXT_NODE) {
      const length = (node.textContent || '').length
      if (remaining <= length) { select(node, remaining); return true }
      remaining -= length
      return false
    }
    if (node instanceof HTMLElement && node.dataset.variable) {
      const length = encoded(node.dataset.variable).length
      if (remaining <= length) { select(node, 0, true); return true }
      remaining -= length
      return false
    }
    for (const child of Array.from(node.childNodes)) if (walk(child)) return true
    return false
  }
  if (!walk(root)) {
    const range = document.createRange()
    range.selectNodeContents(root)
    range.collapse(false)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    savedRange = range.cloneRange()
  }
}

function templateNeedsPaint(root: HTMLElement) {
  return root.querySelectorAll('div,p,br').length > 0 || Array.from(root.childNodes).some(node => node.nodeType === Node.TEXT_NODE && /\{[a-z][a-z0-9_]{0,15}\}/.test(node.textContent || ''))
}

function commit() {
  const root = editor.value
  if (!root) return
  const raw = serialize(root)
  const value = raw.length > props.maxlength ? props.modelValue : raw
  const offset = caretOffset()
  emit('update:modelValue', value)
  if (value !== raw || templateNeedsPaint(root)) {
    paint(value)
    if (offset != null) placeCaret(Math.min(offset, value.length))
  }
}

function rangeInEditor() {
  const root = editor.value
  const selection = window.getSelection()
  if (root && selection?.rangeCount && root.contains(selection.anchorNode)) return selection.getRangeAt(0)
  if (root && savedRange && root.contains(savedRange.startContainer)) return savedRange
  const range = document.createRange()
  if (root) {
    range.selectNodeContents(root)
    range.collapse(false)
  }
  return range
}

function insert(name: string) {
  const root = editor.value
  if (!root || !names().includes(name)) return
  root.focus()
  const range = rangeInEditor()
  range.deleteContents()
  const node = token(name)
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
  savedRange = range.cloneRange()
  const value = serialize(root)
  if (value.length > props.maxlength) {
    paint(props.modelValue)
    return
  }
  emit('update:modelValue', value)
}

function onPaste(event: ClipboardEvent) {
  event.preventDefault()
  const root = editor.value
  if (!root) return
  root.focus()
  const range = rangeInEditor()
  range.deleteContents()
  const node = document.createTextNode(event.clipboardData?.getData('text/plain') || '')
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
  commit()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  event.preventDefault()
  if (!props.multiline) return
  const root = editor.value
  if (!root) return
  root.focus()
  const range = rangeInEditor()
  range.deleteContents()
  const node = document.createTextNode('\n')
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
  commit()
}

onMounted(() => paint(props.modelValue))

watch(() => props.modelValue, value => {
  if (!editor.value || serialize(editor.value) === value) return
  const focused = document.activeElement === editor.value
  const offset = focused ? caretOffset() : null
  paint(value)
  if (focused && offset != null) placeCaret(offset)
})

watch(() => props.names.join('\0'), () => {
  if (!editor.value) return
  const focused = document.activeElement === editor.value
  const offset = focused ? caretOffset() : null
  paint(props.modelValue)
  if (focused && offset != null) placeCaret(offset)
})

defineExpose({ insert })
</script>

<template>
  <div
    :id="id"
    ref="editor"
    class="variable-editor"
    :class="{ multiline, 'is-blank': !modelValue }"
    contenteditable="true"
    role="textbox"
    :aria-multiline="multiline ? 'true' : 'false'"
    :data-placeholder="placeholder"
    @input="commit"
    @keydown="onKeydown"
    @paste="onPaste"
    @mouseup="remember"
    @keyup="remember"
    @blur="remember"
  />
</template>
