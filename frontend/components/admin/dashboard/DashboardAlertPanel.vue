<template>
  <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
    <template #header>
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500">
          <UIcon name="heroicons:exclamation-triangle" class="h-4.5 w-4.5 text-white" />
        </div>
        <div>
          <h3 class="text-sm font-semibold text-stone-900 dark:text-white">风险与状态</h3>
          <p class="text-xs text-stone-500 dark:text-stone-400">优先处理异常项，降低运营风险</p>
        </div>
      </div>
    </template>

    <div class="space-y-2.5">
      <template v-if="loading">
        <div
          v-for="i in 3"
          :key="i"
          class="h-14 animate-pulse rounded-xl border border-stone-200/80 bg-stone-100/80 dark:border-neutral-700/80 dark:bg-neutral-800/70"
        />
      </template>

      <template v-else>
        <div
          v-for="item in alerts"
          :key="item.id"
          class="rounded-xl border px-3 py-2.5"
          :class="[levelUi[item.level].border, levelUi[item.level].bg]"
        >
          <div class="flex items-start gap-2.5">
            <div class="mt-0.5 flex h-7 w-7 items-center justify-center rounded-lg" :class="levelUi[item.level].badgeBg">
              <UIcon :name="item.icon" class="h-4 w-4" :class="levelUi[item.level].icon" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-semibold text-stone-800 dark:text-stone-100">
                {{ item.title }}
              </p>
              <p class="mt-0.5 text-xs text-stone-600 dark:text-stone-300">
                {{ item.description }}
              </p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { AdminConfig, AdminStats } from '~/types/api'

const props = defineProps<{
  config: Partial<AdminConfig>
  stats: Partial<AdminStats>
  loading?: boolean
}>()

type AlertLevel = 'success' | 'info' | 'warning' | 'error'

const levelUi: Record<AlertLevel, { bg: string; border: string; badgeBg: string; icon: string }> = {
  success: {
    bg: 'bg-emerald-50/70 dark:bg-emerald-900/20',
    border: 'border-emerald-200/80 dark:border-emerald-800/60',
    badgeBg: 'bg-emerald-100 dark:bg-emerald-900/40',
    icon: 'text-emerald-600 dark:text-emerald-300',
  },
  info: {
    bg: 'bg-blue-50/70 dark:bg-blue-900/20',
    border: 'border-blue-200/80 dark:border-blue-800/60',
    badgeBg: 'bg-blue-100 dark:bg-blue-900/40',
    icon: 'text-blue-600 dark:text-blue-300',
  },
  warning: {
    bg: 'bg-amber-50/70 dark:bg-amber-900/20',
    border: 'border-amber-200/80 dark:border-amber-800/60',
    badgeBg: 'bg-amber-100 dark:bg-amber-900/40',
    icon: 'text-amber-600 dark:text-amber-300',
  },
  error: {
    bg: 'bg-rose-50/70 dark:bg-rose-900/20',
    border: 'border-rose-200/80 dark:border-rose-800/60',
    badgeBg: 'bg-rose-100 dark:bg-rose-900/40',
    icon: 'text-rose-600 dark:text-rose-300',
  },
}

const alerts = computed(() => {
  const list: Array<{
    id: string
    title: string
    description: string
    level: AlertLevel
    icon: string
  }> = []

  const cdnEnabled = props.config.cdnStatus === '已启用'
  const cdnMonitorEnabled = props.config.cdnMonitor === '已启用'
  const totalImages = Number(props.stats.totalImages || 0)
  const cachedCount = Number(props.stats.cdnCached || 0)
  const cacheRate = totalImages > 0 ? Math.round((cachedCount / totalImages) * 100) : 0

  if (!cdnEnabled) {
    list.push({
      id: 'cdn-disabled',
      title: 'CDN 当前未启用',
      description: '图片访问将直接命中源站，建议开启 CDN 并配置域名。',
      level: 'warning',
      icon: 'heroicons:bolt-slash',
    })
  }

  if (cdnEnabled && !cdnMonitorEnabled) {
    list.push({
      id: 'cdn-monitor-disabled',
      title: 'CDN 监控已关闭',
      description: '无法自动追踪缓存异常，建议开启监控以便及时发现问题。',
      level: 'info',
      icon: 'heroicons:eye-slash',
    })
  }

  if (totalImages > 0 && cacheRate < 20) {
    list.push({
      id: 'cache-rate-low',
      title: '缓存覆盖率偏低',
      description: `当前缓存覆盖率约 ${cacheRate}%（${cachedCount}/${totalImages}），可能影响访问速度。`,
      level: 'warning',
      icon: 'heroicons:cloud-arrow-down',
    })
  }

  if (props.config.groupUpload === '仅管理员') {
    list.push({
      id: 'group-admin-only',
      title: '群组上传为管理员模式',
      description: '普通成员上传已限制，仅管理员可通过群组入口上传。',
      level: 'info',
      icon: 'heroicons:shield-check',
    })
  }

  if (list.length === 0) {
    list.push({
      id: 'all-good',
      title: '系统运行状态正常',
      description: '当前未发现高优先级风险项，可继续日常运营。',
      level: 'success',
      icon: 'heroicons:check-circle',
    })
  }

  return list.slice(0, 4)
})
</script>
