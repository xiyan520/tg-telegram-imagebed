<template>
  <div class="space-y-6">
    <AdminPageHeader
      title="仪表板"
      eyebrow="Monitor"
      icon="heroicons:squares-2x2"
      description="核心指标、风险告警与最近活动一屏掌控"
    >
      <template #meta>
        <UBadge color="gray" variant="subtle" size="xs">
          {{ formattedLastUpdated }}
        </UBadge>
        <UBadge color="amber" variant="subtle" size="xs">
          CDN 缓存率 {{ cdnCacheRate }}%
        </UBadge>
        <UBadge color="blue" variant="subtle" size="xs">
          活动 {{ activities.length }} 条
        </UBadge>
      </template>

      <template #actions>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="refreshing"
          @click="refreshDashboard"
        >
          刷新仪表板
        </UButton>
      </template>
    </AdminPageHeader>

    <UAlert
      v-if="statsError"
      color="red"
      variant="soft"
      icon="heroicons:exclamation-triangle"
      :description="statsError"
    />

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <DashboardStatCard
        label="总图片数"
        :value="stats.totalImages"
        icon="heroicons:photo"
        tone="indigo"
        :loading="loadingStats"
      />
      <DashboardStatCard
        label="总存储量"
        :value="stats.totalSize"
        icon="heroicons:cube"
        tone="blue"
        :loading="loadingStats"
      />
      <DashboardStatCard
        label="今日上传"
        :value="stats.todayUploads"
        icon="heroicons:cloud-arrow-up"
        tone="emerald"
        :loading="loadingStats"
      />
      <DashboardStatCard
        label="CDN 缓存"
        :value="stats.cdnCached"
        :hint="stats.totalImages ? `占比 ${cdnCacheRate}%` : ''"
        icon="heroicons:bolt"
        tone="amber"
        :loading="loadingStats"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <div class="xl:col-span-2">
        <DashboardAlertPanel
          :stats="stats"
          :config="systemConfig"
          :loading="loadingStats"
        />
      </div>
      <DashboardQuickActions />
    </div>

    <DashboardActivityTimeline
      :items="activities"
      :filter="activityFilter"
      :loading="loadingActivities"
      :loading-more="loadingMoreActivities"
      :has-more="activityHasMore"
      :error="activityError"
      @update:filter="activityFilter = $event"
      @refresh="loadActivities({ reset: true })"
      @load-more="loadMoreActivities"
    />
  </div>
</template>

<script setup lang="ts">
import AdminPageHeader from '~/components/admin/common/AdminPageHeader.vue'
import DashboardStatCard from '~/components/admin/dashboard/DashboardStatCard.vue'
import DashboardAlertPanel from '~/components/admin/dashboard/DashboardAlertPanel.vue'
import DashboardQuickActions from '~/components/admin/dashboard/DashboardQuickActions.vue'
import DashboardActivityTimeline from '~/components/admin/dashboard/DashboardActivityTimeline.vue'
import type {
  AdminStats,
  AdminConfig,
  AdminActivityType,
  AdminDashboardActivityItem,
} from '~/types/api'

definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const notification = useNotification()
const { getAdminStats, getAdminDashboardActivity } = useImageApi()

// 状态
const loadingStats = ref(false)
const loadingActivities = ref(false)
const loadingMoreActivities = ref(false)
const refreshing = ref(false)
const stats = ref<Partial<AdminStats>>({})
const systemConfig = ref<Partial<AdminConfig>>({})
const activities = ref<AdminDashboardActivityItem[]>([])
const activityFilter = ref<AdminActivityType>('all')
const activityPage = ref(1)
const activityLimit = 20
const activityHasMore = ref(false)
const statsError = ref('')
const activityError = ref('')
const lastUpdatedAt = ref<Date | null>(null)

// 加载统计信息
const loadStats = async (opts: { silent?: boolean } = {}) => {
  loadingStats.value = true
  statsError.value = ''
  try {
    const data = await getAdminStats()
    stats.value = data.stats
    systemConfig.value = data.config
    lastUpdatedAt.value = new Date()
    if (!opts.silent) {
      notification.success('已刷新', '统计数据已更新')
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
    statsError.value = '无法获取统计信息，请检查后台服务状态。'
    if (!opts.silent) {
      notification.error('加载失败', statsError.value)
    }
  } finally {
    loadingStats.value = false
  }
}

const loadActivities = async (opts: { reset?: boolean; silent?: boolean } = {}) => {
  const reset = opts.reset ?? false
  const targetPage = reset ? 1 : activityPage.value + 1

  if (reset) {
    loadingActivities.value = true
    activityError.value = ''
  } else {
    loadingMoreActivities.value = true
  }

  try {
    const data = await getAdminDashboardActivity({
      type: activityFilter.value,
      page: targetPage,
      limit: activityLimit,
    })

    if (reset) {
      activities.value = data.items || []
    } else {
      activities.value = [...activities.value, ...(data.items || [])]
    }

    activityPage.value = data.page || targetPage
    activityHasMore.value = Boolean(data.has_more)
  } catch (error) {
    console.error('加载活动流失败:', error)
    activityError.value = '活动流加载失败，请稍后重试。'
    if (!opts.silent) {
      notification.error('加载失败', activityError.value)
    }
  } finally {
    loadingActivities.value = false
    loadingMoreActivities.value = false
  }
}

const loadMoreActivities = () => {
  if (!activityHasMore.value || loadingMoreActivities.value || loadingActivities.value) return
  loadActivities({ reset: false, silent: true })
}

const refreshDashboard = async () => {
  refreshing.value = true
  await Promise.all([
    loadStats({ silent: true }),
    loadActivities({ reset: true, silent: true }),
  ])
  refreshing.value = false
  notification.success('已刷新', '仪表板数据已更新')
}

const formattedLastUpdated = computed(() => {
  if (!lastUpdatedAt.value) return '首次加载中'
  return `更新于 ${lastUpdatedAt.value.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })}`
})

const cdnCacheRate = computed(() => {
  const total = Number(stats.value.totalImages || 0)
  const cached = Number(stats.value.cdnCached || 0)
  if (total <= 0) return 0
  return Math.round((cached / total) * 100)
})

watch(activityFilter, () => {
  loadActivities({ reset: true, silent: true })
})

// 页面加载
onMounted(async () => {
  await Promise.all([
    loadStats({ silent: true }),
    loadActivities({ reset: true, silent: true }),
  ])
})
</script>
