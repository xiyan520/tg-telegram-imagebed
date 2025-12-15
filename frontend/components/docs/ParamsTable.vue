<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="bg-stone-50 dark:bg-stone-800/50">
        <tr>
          <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">参数名</th>
          <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">位置</th>
          <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">类型</th>
          <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">必填</th>
          <th class="px-4 py-2 text-left font-medium text-stone-700 dark:text-stone-300">说明</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-stone-200 dark:divide-stone-700">
        <tr v-for="param in params" :key="param.name">
          <td class="px-4 py-2">
            <code class="text-amber-600 dark:text-amber-400">{{ param.name }}</code>
          </td>
          <td class="px-4 py-2">
            <UBadge :color="getLocationColor(param.in)" variant="subtle" size="xs">
              {{ getLocationLabel(param.in) }}
            </UBadge>
          </td>
          <td class="px-4 py-2 text-stone-600 dark:text-stone-400">
            {{ param.type || 'string' }}
          </td>
          <td class="px-4 py-2">
            <UIcon
              v-if="param.required"
              name="heroicons:check-circle-solid"
              class="w-4 h-4 text-green-500"
            />
            <span v-else class="text-stone-400">-</span>
          </td>
          <td class="px-4 py-2 text-stone-600 dark:text-stone-400">
            {{ param.description }}
            <code v-if="param.example" class="ml-1 text-xs text-stone-500">
              例: {{ param.example }}
            </code>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { ApiParam, ParamLocation } from '~/data/apiDocs'

defineProps<{
  params: ApiParam[]
}>()

const getLocationColor = (location: ParamLocation): string => {
  const colors: Record<ParamLocation, string> = {
    path: 'purple',
    query: 'blue',
    header: 'amber',
    body: 'green',
    formData: 'orange',
  }
  return colors[location] || 'gray'
}

const getLocationLabel = (location: ParamLocation): string => {
  const labels: Record<ParamLocation, string> = {
    path: 'Path',
    query: 'Query',
    header: 'Header',
    body: 'Body',
    formData: 'FormData',
  }
  return labels[location] || location
}
</script>
