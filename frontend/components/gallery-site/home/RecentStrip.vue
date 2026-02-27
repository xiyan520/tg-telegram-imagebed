<template>
  <div>
    <div v-if="loading" class="-mx-4 flex gap-3 overflow-x-auto px-4 pb-2">
      <USkeleton v-for="i in 6" :key="i" class="h-24 w-64 flex-shrink-0 rounded-xl" />
    </div>

    <div v-else-if="items.length" class="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2">
      <NuxtLink
        v-for="item in items"
        :key="item.id"
        :to="`/gallery-site/galleries/${item.id}`"
        class="group flex w-[18rem] flex-shrink-0 snap-start items-center gap-3 rounded-xl border border-stone-200 bg-white p-3 shadow-sm transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-md dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
      >
        <div class="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-stone-100 dark:bg-neutral-800">
          <img
            v-if="item.cover_url"
            :src="item.cover_url"
            :alt="item.name"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.05]"
            loading="lazy"
          />
          <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30">
            <UIcon name="heroicons:photo" class="h-6 w-6 text-amber-300 dark:text-amber-700" />
          </div>
        </div>
        <div class="min-w-0 flex-1 space-y-1">
          <p class="truncate text-sm font-semibold text-stone-900 transition-colors group-hover:text-amber-600 dark:text-white dark:group-hover:text-amber-400">
            {{ item.name }}
          </p>
          <p class="text-xs text-stone-500 dark:text-stone-400">
            {{ item.image_count }} 张图片
          </p>
          <p class="text-xs text-stone-400 dark:text-stone-500">
            更新于 {{ formatDate(item.updated_at) }}
          </p>
        </div>
      </NuxtLink>
    </div>

    <div v-else class="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-5 text-center dark:border-stone-700 dark:bg-neutral-900/60">
      <p class="text-sm text-stone-500 dark:text-stone-400">最近还没有新的更新记录</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem } from '~/composables/useGallerySite'

interface Props {
  items: GallerySiteItem[]
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
