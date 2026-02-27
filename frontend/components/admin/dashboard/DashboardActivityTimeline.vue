<template>
  <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
    <template #header>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2.5">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-stone-700 to-stone-900 dark:from-stone-500 dark:to-stone-700">
            <UIcon name="heroicons:clock" class="h-4.5 w-4.5 text-white" />
          </div>
          <div>
            <h3 class="text-sm font-semibold text-stone-900 dark:text-white">最近活动流</h3>
            <p class="text-xs text-stone-500 dark:text-stone-400">上传事件与安全事件统一时间线</p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <div class="inline-flex rounded-lg border border-stone-200/80 bg-stone-50/70 p-1 dark:border-neutral-700/80 dark:bg-neutral-800/70">
            <button
              v-for="option in filterOptions"
              :key="option.value"
              type="button"
              class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
              :class="filter === option.value
                ? 'bg-white text-amber-700 shadow-sm dark:bg-neutral-700 dark:text-amber-300'
                : 'text-stone-600 hover:text-stone-900 dark:text-stone-300 dark:hover:text-white'"
              @click="$emit('update:filter', option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <UButton
            icon="heroicons:arrow-path"
            color="gray"
            variant="ghost"
            size="xs"
            :disabled="loading"
            @click="$emit('refresh')"
          >
            刷新
          </UButton>
        </div>
      </div>
    </template>

    <div class="space-y-3">
      <template v-if="loading">
        <div
          v-for="i in 4"
          :key="i"
          class="h-16 animate-pulse rounded-xl border border-stone-200/80 bg-stone-100/80 dark:border-neutral-700/80 dark:bg-neutral-800/70"
        />
      </template>

      <template v-else-if="error">
        <div class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 dark:border-rose-800/70 dark:bg-rose-900/25">
          <p class="text-sm font-medium text-rose-700 dark:text-rose-300">活动流加载失败</p>
          <p class="mt-1 text-xs text-rose-600 dark:text-rose-400">{{ error }}</p>
          <UButton class="mt-2" color="red" variant="soft" size="xs" @click="$emit('refresh')">
            重试
          </UButton>
        </div>
      </template>

      <template v-else-if="items.length === 0">
        <div class="rounded-xl border border-dashed border-stone-300/80 px-4 py-8 text-center dark:border-neutral-600/70">
          <UIcon name="heroicons:clock" class="mx-auto h-8 w-8 text-stone-400" />
          <p class="mt-2 text-sm font-medium text-stone-700 dark:text-stone-200">暂无活动记录</p>
          <p class="text-xs text-stone-500 dark:text-stone-400">切换筛选或稍后刷新查看</p>
        </div>
      </template>

      <template v-else>
        <div class="space-y-2.5">
          <article
            v-for="item in items"
            :key="item.id"
            class="rounded-xl border border-stone-200/80 px-3 py-2.5 dark:border-neutral-700/80"
          >
            <div class="flex items-start gap-2.5">
              <div class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg" :class="itemUi(item).badgeBg">
                <UIcon :name="itemUi(item).icon" class="h-4.5 w-4.5" :class="itemUi(item).iconColor" />
              </div>

              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="truncate text-sm font-semibold text-stone-800 dark:text-stone-100">
                    {{ item.title }}
                  </p>
                  <UBadge
                    size="xs"
                    :color="itemUi(item).badgeColor"
                    variant="subtle"
                  >
                    {{ item.type === 'upload' ? '上传' : '安全' }}
                  </UBadge>
                </div>
                <p class="mt-0.5 text-xs text-stone-600 dark:text-stone-300">
                  {{ item.description }}
                </p>
                <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-stone-500 dark:text-stone-400">
                  <span v-if="item.actor">操作者：{{ item.actor }}</span>
                  <span v-if="item.ip">IP：{{ item.ip }}</span>
                  <span>{{ formatTime(item.time) }}</span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div v-if="hasMore" class="pt-1">
          <UButton
            color="gray"
            variant="outline"
            block
            :loading="loadingMore"
            @click="$emit('load-more')"
          >
            加载更多
          </UButton>
        </div>
      </template>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { AdminActivityType, AdminDashboardActivityItem } from '~/types/api'

defineProps<{
  items: AdminDashboardActivityItem[]
  filter: AdminActivityType
  loading?: boolean
  loadingMore?: boolean
  hasMore?: boolean
  error?: string
}>()

defineEmits<{
  'update:filter': [value: AdminActivityType]
  refresh: []
  'load-more': []
}>()

const filterOptions: Array<{ value: AdminActivityType; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'upload', label: '上传' },
  { value: 'security', label: '安全' },
]

const itemUi = (item: AdminDashboardActivityItem) => {
  if (item.type === 'upload') {
    return {
      icon: 'heroicons:cloud-arrow-up',
      badgeBg: 'bg-blue-100 dark:bg-blue-900/35',
      iconColor: 'text-blue-600 dark:text-blue-300',
      badgeColor: 'blue',
    }
  }
  if (item.level === 'error') {
    return {
      icon: 'heroicons:shield-exclamation',
      badgeBg: 'bg-rose-100 dark:bg-rose-900/35',
      iconColor: 'text-rose-600 dark:text-rose-300',
      badgeColor: 'red',
    }
  }
  if (item.level === 'warning') {
    return {
      icon: 'heroicons:exclamation-triangle',
      badgeBg: 'bg-amber-100 dark:bg-amber-900/35',
      iconColor: 'text-amber-600 dark:text-amber-300',
      badgeColor: 'amber',
    }
  }
  if (item.level === 'success') {
    return {
      icon: 'heroicons:check-badge',
      badgeBg: 'bg-emerald-100 dark:bg-emerald-900/35',
      iconColor: 'text-emerald-600 dark:text-emerald-300',
      badgeColor: 'green',
    }
  }
  return {
    icon: 'heroicons:shield-check',
    badgeBg: 'bg-stone-100 dark:bg-stone-800',
    iconColor: 'text-stone-600 dark:text-stone-300',
    badgeColor: 'gray',
  }
}

const formatTime = (timeRaw: string) => {
  const date = new Date(timeRaw)
  if (Number.isNaN(date.getTime())) return timeRaw
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}
</script>
