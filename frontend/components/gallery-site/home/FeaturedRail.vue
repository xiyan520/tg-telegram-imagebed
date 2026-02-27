<template>
  <div>
    <div v-if="loading" class="grid gap-4 md:grid-cols-12">
      <USkeleton class="h-48 rounded-2xl md:col-span-7 md:h-[21.5rem]" />
      <div class="grid gap-4 md:col-span-5">
        <USkeleton class="h-[10.25rem] rounded-2xl" />
        <USkeleton class="h-[10.25rem] rounded-2xl" />
      </div>
      <USkeleton class="h-44 rounded-2xl md:col-span-4" />
      <USkeleton class="h-44 rounded-2xl md:col-span-4" />
      <USkeleton class="h-44 rounded-2xl md:col-span-4" />
    </div>

    <div v-else-if="items.length" class="space-y-4">
      <div class="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 md:hidden">
        <NuxtLink
          v-for="item in items"
          :key="`mobile-${item.id}`"
          :to="`/gallery-site/galleries/${item.id}`"
          class="group w-[17.5rem] flex-shrink-0 snap-start overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-md dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
        >
          <div class="aspect-[4/3] overflow-hidden bg-stone-100 dark:bg-neutral-800">
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
            <h3 class="truncate text-base font-semibold font-serif text-stone-900 transition-colors group-hover:text-amber-600 dark:text-white dark:group-hover:text-amber-400">
              {{ item.name }}
            </h3>
            <p class="text-xs text-stone-500 dark:text-stone-400">{{ item.image_count }} 张图片</p>
          </div>
        </NuxtLink>
      </div>

      <div class="hidden grid-cols-12 gap-4 md:grid">
        <NuxtLink
          v-for="(item, index) in items"
          :key="item.id"
          :to="`/gallery-site/galleries/${item.id}`"
          class="group relative overflow-hidden rounded-2xl border border-stone-200 bg-white transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-lg dark:border-stone-700 dark:bg-neutral-900 dark:hover:border-amber-600"
          :class="cardClass(index)"
        >
          <div class="absolute inset-0 bg-stone-100 dark:bg-neutral-800">
            <img
              v-if="item.cover_url"
              :src="item.cover_url"
              :alt="item.name"
              class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-[1.05]"
              loading="lazy"
            />
            <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900/30 dark:to-orange-900/30">
              <UIcon name="heroicons:photo" class="h-12 w-12 text-amber-300 dark:text-amber-700" />
            </div>
          </div>
          <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/20 to-transparent" />
          <div class="relative flex h-full flex-col justify-end p-4">
            <p class="text-xs uppercase tracking-[0.2em] text-white/70">精选</p>
            <h3 class="mt-1 line-clamp-2 text-lg font-semibold text-white">
              {{ item.name }}
            </h3>
            <p class="mt-1 text-xs text-white/80">
              {{ item.image_count }} 张图片
            </p>
          </div>
        </NuxtLink>
      </div>
    </div>

    <div v-else class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-8 text-center dark:border-stone-700 dark:bg-neutral-900/60">
      <UIcon name="heroicons:photo" class="mx-auto h-10 w-10 text-stone-300 dark:text-stone-600" />
      <p class="mt-3 text-sm text-stone-500 dark:text-stone-400">还没有可展示的精选画集</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GallerySiteItem } from '~/composables/useGallerySite'

interface Props {
  items: GallerySiteItem[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const cardClass = (index: number) => {
  if (index === 0) return 'col-span-7 row-span-2 min-h-[21.5rem]'
  if (index === 1 || index === 2) return 'col-span-5 min-h-[10.25rem]'
  return 'col-span-4 min-h-[11rem]'
}
</script>
