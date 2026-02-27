<template>
  <div class="space-y-6 sm:space-y-8">
    <section class="relative overflow-hidden rounded-3xl border border-stone-200/70 bg-white/80 p-5 shadow-sm backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/75 sm:p-7">
      <div class="pointer-events-none absolute inset-0">
        <div class="absolute inset-0 bg-gradient-to-r from-amber-50/80 via-transparent to-orange-50/80 dark:from-amber-900/20 dark:to-orange-900/10" />
        <div class="absolute -right-20 top-0 h-48 w-48 rounded-full bg-orange-300/20 blur-3xl dark:bg-orange-600/10" />
      </div>
      <div class="relative grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
        <div class="space-y-3">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber-600 dark:text-amber-400">Dashboard</p>
          <h1 class="text-2xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-4xl">画集管理仪表板</h1>
          <p class="max-w-2xl text-sm leading-relaxed text-stone-600 dark:text-stone-300 sm:text-base">
            这里是管理后台主控台，快速查看站点内容规模并跳转到配置和画集管理模块。
          </p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-xl border border-stone-200/80 bg-white/90 p-3 dark:border-stone-700/70 dark:bg-neutral-900/70">
            <p class="text-xs text-stone-500 dark:text-stone-400">公开画集</p>
            <USkeleton v-if="loading" class="mt-2 h-7 w-14" />
            <p v-else class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">{{ stats.gallery_count }}</p>
          </div>
          <div class="rounded-xl border border-stone-200/80 bg-white/90 p-3 dark:border-stone-700/70 dark:bg-neutral-900/70">
            <p class="text-xs text-stone-500 dark:text-stone-400">总图片数</p>
            <USkeleton v-if="loading" class="mt-2 h-7 w-14" />
            <p v-else class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">{{ stats.image_count }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-4 sm:grid-cols-2">
      <NuxtLink
        to="/gallery-site/admin/settings"
        class="group rounded-2xl border border-stone-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
      >
        <div class="flex items-start gap-3">
          <div class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 shadow-md">
            <UIcon name="heroicons:cog-6-tooth" class="h-5 w-5 text-white" />
          </div>
          <div class="space-y-1">
            <p class="text-lg font-semibold text-stone-900 transition-colors group-hover:text-amber-700 dark:text-white dark:group-hover:text-amber-300">站点设置</p>
            <p class="text-sm text-stone-500 dark:text-stone-400">配置站点名称、描述、启用状态和分页参数。</p>
          </div>
        </div>
      </NuxtLink>

      <NuxtLink
        to="/gallery-site/admin/galleries"
        class="group rounded-2xl border border-stone-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
      >
        <div class="flex items-start gap-3">
          <div class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-amber-500 shadow-md">
            <UIcon name="heroicons:rectangle-stack" class="h-5 w-5 text-white" />
          </div>
          <div class="space-y-1">
            <p class="text-lg font-semibold text-stone-900 transition-colors group-hover:text-amber-700 dark:text-white dark:group-hover:text-amber-300">画集管理</p>
            <p class="text-sm text-stone-500 dark:text-stone-400">管理分享链接、访问权限、封面与画集内图片。</p>
          </div>
        </div>
      </NuxtLink>
    </section>

    <section class="rounded-2xl border border-stone-200 bg-white/90 p-5 dark:border-stone-700 dark:bg-neutral-900/80">
      <h2 class="text-base font-semibold text-stone-900 dark:text-white sm:text-lg">运营建议</h2>
      <ul class="mt-3 space-y-2 text-sm text-stone-600 dark:text-stone-300">
        <li>保持画集封面质量统一，提升前台首屏点击率。</li>
        <li>优先检查长期未更新画集，避免首页内容老化。</li>
        <li>对敏感内容使用 `token` 或 `password` 访问模式分级管理。</li>
      </ul>
    </section>
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
