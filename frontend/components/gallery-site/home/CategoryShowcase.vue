<template>
  <div>
    <div v-if="loading" class="space-y-8">
      <div v-for="index in 3" :key="index" class="space-y-4">
        <div class="space-y-2">
          <USkeleton class="h-7 w-44" />
          <USkeleton class="h-4 w-80 max-w-full" />
        </div>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <USkeleton v-for="i in 4" :key="i" class="h-52 rounded-2xl" />
        </div>
      </div>
    </div>

    <div v-else-if="buckets.length" class="space-y-10">
      <section v-for="bucket in buckets" :key="bucket.id" class="space-y-4">
        <header class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 class="text-xl font-semibold font-serif text-stone-900 dark:text-white">
              {{ bucket.title }}
            </h3>
            <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">
              {{ bucket.description }}
            </p>
          </div>
          <NuxtLink
            to="/gallery-site/galleries"
            class="inline-flex items-center gap-1 text-sm font-medium text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
          >
            查看更多
            <UIcon name="heroicons:arrow-right" class="h-4 w-4" />
          </NuxtLink>
        </header>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <NuxtLink
            v-for="item in bucket.items"
            :key="`${bucket.id}-${item.id}`"
            :to="`/gallery-site/galleries/${item.id}`"
            class="group overflow-hidden rounded-2xl border border-stone-200 bg-white transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
          >
            <div class="aspect-[16/11] overflow-hidden bg-stone-100 dark:bg-neutral-800">
              <img
                v-if="item.cover_url"
                :src="item.cover_url"
                :alt="item.name"
                class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                loading="lazy"
              />
              <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30">
                <UIcon name="heroicons:photo" class="h-10 w-10 text-amber-300 dark:text-amber-700" />
              </div>
            </div>
            <div class="space-y-1 p-4">
              <h4 class="truncate text-base font-semibold font-serif text-stone-900 transition-colors group-hover:text-amber-600 dark:text-white dark:group-hover:text-amber-400">
                {{ item.name }}
              </h4>
              <div class="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
                <span>{{ item.image_count }} 张图片</span>
                <span>{{ formatDate(item.updated_at) }}</span>
              </div>
            </div>
          </NuxtLink>
        </div>
      </section>
    </div>

    <div v-else class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-8 text-center dark:border-stone-700 dark:bg-neutral-900/60">
      <p class="text-sm text-stone-500 dark:text-stone-400">暂无可用分区内容</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem } from '~/composables/useGallerySite'

interface HomeBucket {
  id: string
  title: string
  description: string
  items: GallerySiteItem[]
}

interface Props {
  buckets: HomeBucket[]
  loading?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false
})

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit'
  }).format(date)
}
</script>
