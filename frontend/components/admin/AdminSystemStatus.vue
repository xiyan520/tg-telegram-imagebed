<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
          <UIcon name="heroicons:server" class="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">系统状态</h3>
          <p class="text-xs text-stone-500 dark:text-stone-400">当前系统运行状态</p>
        </div>
      </div>
    </template>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div
        v-for="item in items"
        :key="item.label"
        class="p-4 bg-gradient-to-br rounded-xl border"
        :class="[colorMap[item.colors].bg, colorMap[item.colors].border]"
      >
        <div class="flex items-center gap-2 mb-2">
          <UIcon :name="item.icon" class="w-4 h-4" :class="colorMap[item.colors].icon" />
          <p class="text-sm font-medium text-stone-600 dark:text-stone-400">{{ item.label }}</p>
        </div>
        <p class="text-lg font-bold text-stone-900 dark:text-white" :class="{ truncate: item.truncate }">
          {{ item.value || '--' }}
        </p>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
const props = defineProps<{
  config: Record<string, any>
}>()

const colorMap: Record<string, { bg: string; border: string; icon: string }> = {
  green: {
    bg: 'from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20',
    border: 'border-green-200 dark:border-green-800',
    icon: 'text-green-600 dark:text-green-400',
  },
  blue: {
    bg: 'from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-600 dark:text-blue-400',
  },
  purple: {
    bg: 'from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    icon: 'text-purple-600 dark:text-purple-400',
  },
  orange: {
    bg: 'from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20',
    border: 'border-orange-200 dark:border-orange-800',
    icon: 'text-orange-600 dark:text-orange-400',
  },
  indigo: {
    bg: 'from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20',
    border: 'border-indigo-200 dark:border-indigo-800',
    icon: 'text-indigo-600 dark:text-indigo-400',
  },
  teal: {
    bg: 'from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/20',
    border: 'border-teal-200 dark:border-teal-800',
    icon: 'text-teal-600 dark:text-teal-400',
  },
}

const items = computed(() => [
  { icon: 'heroicons:signal', label: 'CDN状态', value: props.config.cdnStatus, colors: 'green' },
  { icon: 'heroicons:globe-alt', label: '域名', value: props.config.cdnDomain, colors: 'blue', truncate: true },
  { icon: 'heroicons:server', label: '存储类型', value: 'Telegram Cloud', colors: 'purple' },
  { icon: 'heroicons:clock', label: '运行时间', value: props.config.uptime, colors: 'orange' },
  { icon: 'heroicons:user-group', label: '群组上传', value: props.config.groupUpload, colors: 'indigo' },
  { icon: 'heroicons:chart-bar', label: 'CDN监控', value: props.config.cdnMonitor, colors: 'teal' },
])
</script>
