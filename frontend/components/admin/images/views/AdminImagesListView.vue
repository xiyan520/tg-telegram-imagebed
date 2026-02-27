<template>
  <div class="overflow-x-auto">
    <table class="min-w-full text-sm">
      <thead>
        <tr class="border-b border-stone-200/70 text-left text-stone-600 dark:border-neutral-700/70 dark:text-stone-300">
          <th class="w-12 py-2.5 pr-2">选择</th>
          <th class="w-14 py-2.5 pr-2">缩略图</th>
          <th class="py-2.5 pr-3">文件名</th>
          <th class="py-2.5 pr-3 whitespace-nowrap">来源</th>
          <th class="py-2.5 pr-3 whitespace-nowrap">大小</th>
          <th class="py-2.5 pr-3 whitespace-nowrap">访问</th>
          <th class="py-2.5 pr-3 whitespace-nowrap">上传时间</th>
          <th class="py-2.5 pr-2 whitespace-nowrap">缓存</th>
          <th class="py-2.5 text-right whitespace-nowrap">操作</th>
        </tr>
      </thead>

      <tbody class="divide-y divide-stone-200/60 dark:divide-neutral-700/60">
        <tr
          v-for="image in images"
          :key="image.id"
          class="transition-colors hover:bg-stone-50 dark:hover:bg-neutral-800/60"
          :class="selectedIds.includes(image.id) ? 'bg-amber-50/70 dark:bg-amber-900/15' : ''"
        >
          <td class="py-2.5 pr-2">
            <UCheckbox :model-value="selectedIds.includes(image.id)" @change="$emit('toggle-select', image.id)" />
          </td>
          <td class="py-2.5 pr-2">
            <button
              type="button"
              class="h-10 w-10 overflow-hidden rounded-md border border-stone-200 dark:border-neutral-700"
              @click="$emit('view-detail', image)"
            >
              <img
                :src="image.url"
                :alt="image.filename"
                loading="lazy"
                class="h-full w-full object-cover"
                @error="onImageError"
              >
            </button>
          </td>
          <td class="py-2.5 pr-3">
            <p class="max-w-[18rem] truncate text-stone-800 dark:text-stone-100" :title="image.filename">
              {{ image.filename }}
            </p>
            <p class="text-[11px] text-stone-500 dark:text-stone-400">
              {{ image.username || 'unknown' }}
            </p>
          </td>
          <td class="py-2.5 pr-3 whitespace-nowrap text-stone-600 dark:text-stone-300">
            {{ sourceLabel(image.source) }}
          </td>
          <td class="py-2.5 pr-3 whitespace-nowrap text-stone-600 dark:text-stone-300">
            {{ formatSize(image.size) }}
          </td>
          <td class="py-2.5 pr-3 whitespace-nowrap text-stone-600 dark:text-stone-300">
            {{ image.access_count || 0 }}
          </td>
          <td class="py-2.5 pr-3 whitespace-nowrap text-xs text-stone-500 dark:text-stone-400">
            {{ image.uploadTime || '--' }}
          </td>
          <td class="py-2.5 pr-2 whitespace-nowrap">
            <UBadge :color="image.cached ? 'green' : 'gray'" variant="subtle" size="xs">
              {{ image.cached ? '已缓存' : '未缓存' }}
            </UBadge>
          </td>
          <td class="py-2.5 text-right">
            <div class="flex items-center justify-end gap-1">
              <UButton icon="heroicons:eye" color="gray" variant="ghost" size="xs" @click="$emit('view-detail', image)" />
              <UButton icon="heroicons:link" color="gray" variant="ghost" size="xs" @click="$emit('copy-url', image.url)" />
              <UButton icon="heroicons:trash" color="red" variant="ghost" size="xs" @click="$emit('delete', image.id)" />
            </div>
          </td>
        </tr>
      </tbody>
    </table>
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

const formatSize = (size: string | number | null | undefined) => {
  if (size === null || size === undefined || size === '') return '--'
  if (typeof size === 'string') {
    if (/[a-zA-Z]/.test(size)) return size
    const parsed = Number(size)
    if (!Number.isFinite(parsed)) return size
    return `${(parsed / (1024 * 1024)).toFixed(2)} MB`
  }
  if (!Number.isFinite(size)) return '--'
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

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
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="64" height="64"%3E%3Crect fill="%23ddd" width="64" height="64" rx="4"/%3E%3C/svg%3E'
}
</script>
