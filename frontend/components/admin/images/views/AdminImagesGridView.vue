<template>
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
    <article
      v-for="image in images"
      :key="image.id"
      class="group relative overflow-hidden rounded-xl border-2 transition-all"
      :class="selectedIds.includes(image.id)
        ? 'border-amber-500 ring-2 ring-amber-400/50'
        : 'border-stone-200/80 hover:border-amber-300 dark:border-neutral-700/80 dark:hover:border-amber-500/60'"
    >
      <img
        :src="image.url"
        :alt="image.filename"
        loading="lazy"
        decoding="async"
        class="aspect-square w-full object-cover"
        @error="onImageError"
      >

      <div class="absolute left-2 top-2 z-10 rounded-md bg-white/90 p-1 shadow-sm dark:bg-neutral-900/85">
        <UCheckbox :model-value="selectedIds.includes(image.id)" @change="$emit('toggle-select', image.id)" />
      </div>

      <div class="absolute right-2 top-2 z-10">
        <UBadge :color="image.cached ? 'green' : 'gray'" size="xs" variant="solid">
          {{ image.cached ? '缓存' : '未缓存' }}
        </UBadge>
      </div>

      <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-2.5">
        <p class="truncate text-xs font-medium text-white">{{ image.filename }}</p>
        <p class="mt-0.5 text-[11px] text-white/80">
          访问 {{ image.access_count || 0 }} · {{ sourceLabel(image.source) }}
        </p>

        <div class="mt-2 flex items-center gap-1 opacity-100 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100">
          <UButton icon="heroicons:eye" color="white" size="xs" @click="$emit('view-detail', image)" />
          <UButton icon="heroicons:link" color="white" size="xs" @click="$emit('copy-url', image.url)" />
          <UButton icon="heroicons:trash" color="red" size="xs" @click="$emit('delete', image.id)" />
        </div>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { AdminImageItem } from '~/types/api'

defineProps<{
  images: AdminImageItem[]
  selectedIds: string[]
}>()

defineEmits<{
  'toggle-select': [id: string]
  'view-detail': [image: AdminImageItem]
  'copy-url': [url: string]
  delete: [id: string]
}>()

const sourceLabel = (source?: string) => {
  const value = String(source || '').toLowerCase()
  if (value.includes('token')) return 'Token'
  if (value === 'telegram_bot') return '机器人'
  if (value === 'group') return '群组'
  if (value === 'admin_upload') return '管理员'
  if (value === 'guest') return '匿名'
  return value || '未知'
}

const onImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="480" height="480"%3E%3Crect fill="%23ddd" width="480" height="480"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18"%3E加载失败%3C/text%3E%3C/svg%3E'
}
</script>
