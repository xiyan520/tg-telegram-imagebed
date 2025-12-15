<template>
  <nav class="space-y-1">
    <div v-for="section in sections" :key="section.id" class="mb-4">
      <!-- 分组标题 -->
      <a
        :href="`#${section.id}`"
        class="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-stone-900 dark:text-white hover:bg-amber-50/60 dark:hover:bg-stone-800/70 rounded-lg transition-colors"
        :class="{ 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400': activeSection === section.id }"
        @click.prevent="handleClick(section.id)"
      >
        <UIcon v-if="section.icon" :name="section.icon" class="w-4 h-4" />
        <span>{{ section.title }}</span>
      </a>
      <!-- 端点列表 -->
      <div class="ml-6 mt-1 space-y-0.5">
        <a
          v-for="endpoint in section.endpoints"
          :key="endpoint.id"
          :href="`#${endpoint.id}`"
          class="block px-3 py-1.5 text-sm text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-white hover:bg-amber-50/50 dark:hover:bg-stone-800/70 rounded-md transition-colors"
          :class="{
            'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20': activeEndpoint === endpoint.id,
            'line-through opacity-60': endpoint.deprecated
          }"
          @click.prevent="handleClick(endpoint.id)"
        >
          <span class="inline-block w-12 font-mono text-xs" :class="getMethodClass(endpoint.method)">
            {{ endpoint.method }}
          </span>
          {{ endpoint.title }}
        </a>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import type { ApiSection, HttpMethod } from '~/data/apiDocs'

defineProps<{
  sections: ApiSection[]
  activeSection?: string
  activeEndpoint?: string
}>()

const emit = defineEmits<{
  navigate: [id: string]
}>()

const handleClick = (id: string) => {
  emit('navigate', id)
}

const getMethodClass = (method: HttpMethod): string => {
  const classes: Record<HttpMethod, string> = {
    GET: 'text-blue-600 dark:text-blue-400',
    POST: 'text-green-600 dark:text-green-400',
    PUT: 'text-amber-600 dark:text-amber-400',
    DELETE: 'text-red-600 dark:text-red-400',
    HEAD: 'text-stone-600 dark:text-stone-400',
  }
  return classes[method] || ''
}
</script>
