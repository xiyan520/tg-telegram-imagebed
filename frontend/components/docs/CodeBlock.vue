<template>
  <div class="relative group">
    <pre
      class="p-4 bg-stone-900 text-stone-100 rounded-lg overflow-x-auto text-sm font-mono"
    ><code :class="languageClass">{{ displayCode }}</code></pre>
    <button
      class="absolute top-2 right-2 p-1.5 rounded-md bg-stone-700/50 hover:bg-stone-600 text-stone-400 hover:text-stone-200 opacity-0 group-hover:opacity-100 transition-opacity"
      :title="copied ? '已复制' : '复制代码'"
      @click="copyCode"
    >
      <UIcon
        :name="copied ? 'heroicons:check' : 'heroicons:clipboard-document'"
        class="w-4 h-4"
      />
    </button>
  </div>
</template>

<script setup lang="ts">
import type { CodeLanguage } from '~/data/apiDocs'

const props = defineProps<{
  code: string
  language?: CodeLanguage
}>()

const copied = ref(false)

const languageClass = computed(() => {
  if (!props.language) return ''
  return `language-${props.language}`
})

const displayCode = computed(() => props.code.trim())

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(displayCode.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('复制失败:', err)
  }
}
</script>
