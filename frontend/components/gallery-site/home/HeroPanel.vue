<template>
  <section class="relative overflow-hidden border-b border-stone-200/70 dark:border-stone-800/70">
    <div class="pointer-events-none absolute inset-0">
      <div class="absolute inset-0 bg-gradient-to-br from-amber-50 via-orange-50/50 to-stone-50 dark:from-amber-950/30 dark:via-neutral-950 dark:to-neutral-950" />
      <div class="absolute -left-24 top-10 h-56 w-56 rounded-full bg-amber-400/20 blur-3xl dark:bg-amber-600/10" />
      <div class="absolute -right-16 bottom-0 h-64 w-64 rounded-full bg-orange-300/20 blur-3xl dark:bg-orange-600/10" />
    </div>

    <div class="relative mx-auto max-w-7xl px-4 py-9 sm:px-6 sm:py-14 lg:px-8 lg:py-16">
      <div class="grid items-stretch gap-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:gap-7">
        <div class="space-y-6">
          <span class="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-white/80 px-3 py-1 text-xs font-semibold tracking-[0.2em] text-amber-700 shadow-sm dark:border-amber-700/60 dark:bg-neutral-900/70 dark:text-amber-300">
            <UIcon name="heroicons:sparkles" class="h-3.5 w-3.5" />
            CURATED COLLECTIONS
          </span>

          <div class="space-y-4">
            <h1 class="max-w-3xl text-3xl font-bold font-serif leading-tight tracking-tight text-stone-900 dark:text-white sm:text-5xl lg:text-6xl">
              {{ siteName }}
            </h1>
            <p class="max-w-2xl text-sm leading-relaxed text-stone-600 dark:text-stone-300 sm:text-lg">
              {{ siteDescription }}
            </p>
          </div>

          <div class="flex flex-col items-start gap-3 min-[430px]:flex-row min-[430px]:items-center">
            <NuxtLink
              to="/gallery-site/galleries"
              class="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-amber-500/30 transition-all hover:-translate-y-0.5 hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 min-[430px]:w-auto dark:focus:ring-offset-neutral-950"
            >
              浏览全部画集
              <UIcon name="heroicons:arrow-right" class="h-4 w-4" />
            </NuxtLink>
            <span class="text-xs text-stone-500 dark:text-stone-400 sm:text-sm">
              实时公开浏览，无需登录
            </span>
          </div>

          <div class="grid grid-cols-1 gap-3 min-[390px]:grid-cols-2 sm:max-w-xl sm:grid-cols-3">
            <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/60">
              <p class="text-xs text-stone-500 dark:text-stone-400">画集总数</p>
              <USkeleton v-if="loading" class="mt-2 h-8 w-16" />
              <p v-else class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">
                {{ stats?.gallery_count ?? 0 }}
              </p>
            </div>
            <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/60">
              <p class="text-xs text-stone-500 dark:text-stone-400">图片总数</p>
              <USkeleton v-if="loading" class="mt-2 h-8 w-16" />
              <p v-else class="mt-2 text-2xl font-semibold text-stone-900 dark:text-white">
                {{ stats?.image_count ?? 0 }}
              </p>
            </div>
            <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/60">
              <p class="text-xs text-stone-500 dark:text-stone-400">更新节奏</p>
              <p class="mt-2 text-sm font-medium text-stone-900 dark:text-white">
                {{ primary ? `最近更新 ${updatedLabel}` : '等待内容上线' }}
              </p>
            </div>
          </div>
        </div>

        <div class="rounded-2xl border border-stone-200/70 bg-white/80 p-3 shadow-xl shadow-stone-900/5 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/70 dark:shadow-black/20">
          <USkeleton v-if="loading" class="aspect-[16/10] w-full rounded-xl sm:aspect-[4/3]" />

          <NuxtLink
            v-else-if="primary"
            :to="`/gallery-site/galleries/${primary.id}`"
            class="group block rounded-xl transition-transform hover:-translate-y-1"
          >
            <div class="relative overflow-hidden rounded-xl bg-stone-100 dark:bg-neutral-800">
              <img
                v-if="primary.cover_url"
                :src="primary.cover_url"
                :alt="primary.name"
                class="aspect-[16/10] w-full object-cover transition-transform duration-500 group-hover:scale-[1.03] sm:aspect-[4/3]"
                loading="eager"
              />
              <div v-else class="flex aspect-[16/10] w-full items-center justify-center bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/40 dark:to-orange-900/40 sm:aspect-[4/3]">
                <UIcon name="heroicons:photo" class="h-14 w-14 text-amber-300 dark:text-amber-700" />
              </div>
              <div class="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/45 to-transparent opacity-60 transition-opacity group-hover:opacity-80" />
              <div class="absolute bottom-0 left-0 right-0 p-4">
                <p class="text-xs uppercase tracking-[0.2em] text-white/80">Featured</p>
                <h2 class="mt-1 truncate text-lg font-semibold text-white sm:text-xl">
                  {{ primary.name }}
                </h2>
              </div>
            </div>
            <div class="mt-3 flex flex-wrap items-center justify-between gap-1.5 px-1 text-sm text-stone-600 dark:text-stone-300">
              <span class="text-xs sm:text-sm">{{ primary.image_count }} 张图片</span>
              <span class="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                查看
                <UIcon name="heroicons:arrow-up-right" class="h-4 w-4" />
              </span>
            </div>
          </NuxtLink>

          <div v-else class="flex aspect-[16/10] w-full flex-col items-center justify-center rounded-xl bg-stone-100 text-center dark:bg-neutral-800 sm:aspect-[4/3]">
            <UIcon name="heroicons:photo" class="h-12 w-12 text-stone-300 dark:text-stone-600" />
            <p class="mt-3 text-sm text-stone-500 dark:text-stone-400">暂无可展示精选画集</p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { GallerySiteItem, GallerySiteStats } from '~/composables/useGallerySite'

interface Props {
  siteName: string
  siteDescription: string
  stats: GallerySiteStats | null
  primary: GallerySiteItem | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const updatedLabel = computed(() => {
  if (!props.primary?.updated_at) return '--'
  const date = new Date(props.primary.updated_at)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit'
  }).format(date)
})
</script>
