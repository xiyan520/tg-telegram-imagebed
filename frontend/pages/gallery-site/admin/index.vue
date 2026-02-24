<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div>
      <h1 class="text-2xl font-bold text-stone-900 dark:text-white">仪表板</h1>
      <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">画集站点概览</p>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- 公开画集数 -->
      <UCard>
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center flex-shrink-0">
            <UIcon name="heroicons:photo" class="w-6 h-6 text-white" />
          </div>
          <div v-if="loading" class="flex-1 space-y-2">
            <USkeleton class="h-4 w-20" />
            <USkeleton class="h-7 w-12" />
          </div>
          <div v-else class="flex-1">
            <p class="text-sm text-stone-500 dark:text-stone-400">公开画集</p>
            <p class="text-2xl font-bold text-stone-900 dark:text-white">{{ stats.gallery_count }}</p>
          </div>
        </div>
      </UCard>

      <!-- 总图片数 -->
      <UCard>
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-gradient-to-br from-violet-500 to-purple-500 rounded-xl flex items-center justify-center flex-shrink-0">
            <UIcon name="heroicons:squares-2x2" class="w-6 h-6 text-white" />
          </div>
          <div v-if="loading" class="flex-1 space-y-2">
            <USkeleton class="h-4 w-20" />
            <USkeleton class="h-7 w-12" />
          </div>
          <div v-else class="flex-1">
            <p class="text-sm text-stone-500 dark:text-stone-400">总图片数</p>
            <p class="text-2xl font-bold text-stone-900 dark:text-white">{{ stats.image_count }}</p>
          </div>
        </div>
      </UCard>
    </div>

    <!-- 快捷操作 -->
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold text-stone-900 dark:text-white">快捷操作</h3>
      </template>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <NuxtLink to="/gallery-site/admin/settings">
          <div class="flex items-center gap-3 p-4 rounded-xl border border-stone-200 dark:border-neutral-700 hover:border-amber-300 dark:hover:border-amber-700 hover:bg-amber-50/50 dark:hover:bg-amber-900/10 transition-all cursor-pointer">
            <UIcon name="heroicons:cog-6-tooth" class="w-5 h-5 text-amber-500" />
            <div>
              <p class="font-medium text-stone-900 dark:text-white">站点设置</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">配置站点名称、描述等</p>
            </div>
          </div>
        </NuxtLink>
        <NuxtLink to="/gallery-site/admin/galleries">
          <div class="flex items-center gap-3 p-4 rounded-xl border border-stone-200 dark:border-neutral-700 hover:border-amber-300 dark:hover:border-amber-700 hover:bg-amber-50/50 dark:hover:bg-amber-900/10 transition-all cursor-pointer">
            <UIcon name="heroicons:rectangle-stack" class="w-5 h-5 text-violet-500" />
            <div>
              <p class="font-medium text-stone-900 dark:text-white">画集管理</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">管理画集分享和访问权限</p>
            </div>
          </div>
        </NuxtLink>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteStats } from '~/composables/useGallerySite'

definePageMeta({
  layout: 'gallery-site-admin',
  middleware: 'gallery-site-admin-auth'
})

const { getStats } = useGallerySiteApi()

const loading = ref(true)
const stats = ref<GallerySiteStats>({ gallery_count: 0, image_count: 0 })

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch (e) {
    console.error('获取统计数据失败:', e)
  } finally {
    loading.value = false
  }
})
</script>
