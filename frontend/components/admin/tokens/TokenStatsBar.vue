<template>
  <UCard>
    <div v-if="loading" class="flex items-center gap-2 py-1 text-sm text-stone-500 dark:text-stone-400">
      <div class="h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
      正在加载 Token 统计...
    </div>
    <div v-else class="grid grid-cols-2 gap-2 md:grid-cols-5">
      <div class="rounded-lg border border-stone-200/80 bg-stone-50/70 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/60">
        <p class="text-xs text-stone-500 dark:text-stone-400">总量</p>
        <p class="mt-0.5 text-lg font-semibold text-stone-900 dark:text-white">{{ metrics.total }}</p>
      </div>
      <div class="rounded-lg border border-green-200/80 bg-green-50/70 px-3 py-2 dark:border-green-900/60 dark:bg-green-900/20">
        <p class="text-xs text-green-700/80 dark:text-green-300/80">启用中</p>
        <p class="mt-0.5 text-lg font-semibold text-green-700 dark:text-green-300">{{ metrics.active }}</p>
      </div>
      <div class="rounded-lg border border-stone-200/80 bg-stone-50/70 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/60">
        <p class="text-xs text-stone-500 dark:text-stone-400">禁用中</p>
        <p class="mt-0.5 text-lg font-semibold text-stone-900 dark:text-white">{{ metrics.disabled }}</p>
      </div>
      <div class="rounded-lg border border-amber-200/80 bg-amber-50/70 px-3 py-2 dark:border-amber-900/60 dark:bg-amber-900/20">
        <p class="text-xs text-amber-700/80 dark:text-amber-300/80">已过期</p>
        <p class="mt-0.5 text-lg font-semibold text-amber-700 dark:text-amber-300">{{ metrics.expired }}</p>
      </div>
      <div class="rounded-lg border border-blue-200/80 bg-blue-50/70 px-3 py-2 dark:border-blue-900/60 dark:bg-blue-900/20">
        <p class="text-xs text-blue-700/80 dark:text-blue-300/80">TG 绑定</p>
        <p class="mt-0.5 text-lg font-semibold text-blue-700 dark:text-blue-300">{{ metrics.tg_bound }}</p>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { AdminTokenMetrics } from '~/types/admin'

defineProps<{
  loading: boolean
  metrics: AdminTokenMetrics
}>()
</script>
