<template>
  <div class="overflow-x-auto">
    <table class="min-w-full text-sm">
      <thead>
        <tr class="text-left text-stone-600 dark:text-stone-300 border-b border-stone-200/60 dark:border-neutral-700/60">
          <th class="py-3 pr-2 font-medium w-10">
            <input
              type="checkbox"
              :checked="isAllSelected"
              :indeterminate="isPartialSelected"
              class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
              @change="toggleAll"
            />
          </th>
          <th class="py-3 pr-3 font-medium w-14">缩略图</th>
          <th class="py-3 pr-4 font-medium">文件名</th>
          <th class="py-3 pr-4 font-medium whitespace-nowrap">大小</th>
          <th class="py-3 pr-4 font-medium whitespace-nowrap">来源</th>
          <th class="py-3 pr-4 font-medium whitespace-nowrap">上传时间</th>
          <th class="py-3 pr-4 font-medium whitespace-nowrap">访问次数</th>
          <th class="py-3 pr-4 font-medium">缓存</th>
          <th class="py-3 text-right font-medium">操作</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-stone-200/50 dark:divide-neutral-700/50">
        <tr
          v-for="image in images"
          :key="image.id"
          class="text-stone-800 dark:text-stone-100 hover:bg-stone-50 dark:hover:bg-neutral-800/50 transition-colors"
          :class="{ 'bg-amber-50/50 dark:bg-amber-900/10': selectedImages.includes(image.id) }"
        >
          <td class="py-2 pr-2">
            <input
              type="checkbox"
              :checked="selectedImages.includes(image.id)"
              class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
              @change="emit('toggle-select', image.id)"
            />
          </td>
          <td class="py-2 pr-3">
            <div class="w-12 h-12 rounded-lg overflow-hidden bg-stone-100 dark:bg-neutral-800 flex-shrink-0">
              <img
                :src="image.url"
                :alt="image.filename"
                loading="lazy"
                class="w-full h-full object-cover cursor-pointer hover:scale-110 transition-transform"
                @click="emit('view-detail', image)"
                @error="handleImageError"
              />
            </div>
          </td>
          <td class="py-2 pr-4 max-w-[16rem]">
            <span class="truncate block text-stone-700 dark:text-stone-300" :title="image.filename">{{ image.filename }}</span>
          </td>
          <td class="py-2 pr-4 whitespace-nowrap text-stone-600 dark:text-stone-400">{{ image.size || '--' }}</td>
          <td class="py-2 pr-4 whitespace-nowrap">
            <UBadge v-if="image.source === 'group'" color="blue" variant="subtle" size="xs">群组</UBadge>
            <UBadge v-else-if="image.source === 'token'" color="amber" variant="subtle" size="xs">Token</UBadge>
            <span v-else class="text-stone-500 dark:text-stone-400 text-xs">{{ image.source || '匿名' }}</span>
          </td>
          <td class="py-2 pr-4 whitespace-nowrap text-stone-600 dark:text-stone-400 text-xs">{{ image.uploadTime || '--' }}</td>
          <td class="py-2 pr-4 whitespace-nowrap">
            <div class="flex items-center gap-1">
              <UIcon name="heroicons:eye" class="w-3.5 h-3.5 text-stone-400" />
              <span class="text-stone-700 dark:text-stone-300">{{ image.access_count || 0 }}</span>
            </div>
          </td>
          <td class="py-2 pr-4">
            <UBadge :color="image.cached ? 'green' : 'gray'" variant="subtle" size="xs">
              {{ image.cached ? '已缓存' : '未缓存' }}
            </UBadge>
          </td>
          <td class="py-2 text-right">
            <div class="flex items-center justify-end gap-1">
              <UButton icon="heroicons:eye" color="gray" variant="ghost" size="xs" @click="emit('view-detail', image)" />
              <UButton icon="heroicons:clipboard-document" color="gray" variant="ghost" size="xs" @click="emit('copy-url', image.url)" />
              <UButton icon="heroicons:trash" color="red" variant="ghost" size="xs" @click="emit('delete', image.id)" />
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="images.length === 0" class="text-center py-12 text-stone-500 dark:text-stone-400">暂无图片</div>
  </div>
</template>

<script setup lang="ts">
interface AdminImageItem {
  id: string
  url: string
  filename: string
  size?: string
  source?: string
  uploadTime?: string
  access_count?: number
  cached?: boolean
  cdn_url?: string
  [key: string]: any
}

const props = defineProps<{
  images: AdminImageItem[]
  selectedImages: string[]
}>()

const emit = defineEmits<{
  (e: 'toggle-select', id: string): void
  (e: 'view-detail', image: AdminImageItem): void
  (e: 'copy-url', url: string): void
  (e: 'delete', id: string): void
}>()

const isAllSelected = computed(() => props.images.length > 0 && props.selectedImages.length === props.images.length)
const isPartialSelected = computed(() => props.selectedImages.length > 0 && props.selectedImages.length < props.images.length)

const toggleAll = () => {
  if (isAllSelected.value) {
    // 取消全选：逐个触发
    props.selectedImages.forEach(id => emit('toggle-select', id))
  } else {
    // 全选：触发未选中的
    props.images.forEach(img => {
      if (!props.selectedImages.includes(img.id)) emit('toggle-select', img.id)
    })
  }
}

const handleImageError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="48" height="48"%3E%3Crect fill="%23ddd" width="48" height="48" rx="4"/%3E%3C/svg%3E'
}
</script>