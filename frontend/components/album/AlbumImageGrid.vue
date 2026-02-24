<template>
  <!-- 加载状态 -->
  <div v-if="loading" class="flex justify-center py-16">
    <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
  </div>

  <!-- 空状态 -->
  <div v-else-if="images.length === 0" class="text-center py-16">
    <div class="w-16 h-16 mx-auto bg-stone-100 dark:bg-neutral-800 rounded-2xl flex items-center justify-center mb-4">
      <UIcon name="heroicons:photo" class="w-8 h-8 text-stone-300 dark:text-neutral-600" />
    </div>
    <p class="text-stone-500 dark:text-stone-400 text-sm">暂无图片</p>
  </div>

  <!-- 图片网格 -->
  <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
    <div
      v-for="(image, idx) in images"
      :key="image.encrypted_id"
      class="relative group rounded-xl overflow-hidden transition-all duration-200 cursor-pointer"
      :class="isSelected(image.encrypted_id)
        ? 'ring-2 ring-amber-500 ring-offset-2 ring-offset-white dark:ring-offset-neutral-900 shadow-lg shadow-amber-500/20'
        : 'hover:shadow-lg hover:shadow-black/10 dark:hover:shadow-black/30'"
      @click="handleClick(image, idx)"
    >
      <div class="aspect-square bg-stone-100 dark:bg-neutral-800">
        <img
          :src="image.image_url"
          :alt="image.original_filename"
          class="w-full h-full object-cover"
          loading="lazy"
        />
      </div>

      <!-- 选择模式复选框 -->
      <div
        v-if="showSelection"
        class="absolute top-2 left-2 z-10"
        @click.stop="$emit('toggle-select', image.encrypted_id)"
      >
        <div
          class="w-6 h-6 rounded-md flex items-center justify-center transition-all"
          :class="isSelected(image.encrypted_id)
            ? 'bg-amber-500 shadow-sm shadow-amber-500/30'
            : 'bg-white/80 dark:bg-neutral-800/80 backdrop-blur-sm border border-stone-200 dark:border-neutral-600'"
        >
          <UIcon v-if="isSelected(image.encrypted_id)" name="heroicons:check" class="w-3.5 h-3.5 text-white" />
        </div>
      </div>

      <!-- 封面标记 -->
      <div v-if="showCoverBadge && coverImageId === image.encrypted_id" class="absolute top-2 right-2 z-10">
        <div class="flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-green-500/90 backdrop-blur-sm text-white text-xs font-medium">
          <UIcon name="heroicons:star" class="w-3 h-3" />封面
        </div>
      </div>

      <!-- 悬浮操作 -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        <div class="absolute top-2 right-2 flex gap-1" @click.stop>
          <button
            v-if="showCoverBadge && coverImageId !== image.encrypted_id"
            class="w-7 h-7 rounded-md bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm flex items-center justify-center hover:bg-white transition-colors"
            title="设为封面"
            @click="$emit('set-cover', image.encrypted_id)"
          >
            <UIcon name="heroicons:star" class="w-3.5 h-3.5 text-stone-600 dark:text-stone-300" />
          </button>
          <button
            class="w-7 h-7 rounded-md bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm flex items-center justify-center hover:bg-white transition-colors"
            title="复制链接"
            @click="copyLink(image.image_url)"
          >
            <UIcon name="heroicons:clipboard-document" class="w-3.5 h-3.5 text-stone-600 dark:text-stone-300" />
          </button>
        </div>
        <div class="absolute bottom-0 inset-x-0 p-2.5">
          <p class="text-white text-xs truncate font-medium">{{ image.original_filename }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'

const props = defineProps<{
  images: GalleryImage[]
  selectedIds: string[]
  loading?: boolean
  showSelection?: boolean
  showCoverBadge?: boolean
  coverImageId?: string
}>()

const emit = defineEmits<{
  (e: 'toggle-select', id: string): void
  (e: 'view-image', images: GalleryImage[], index: number): void
  (e: 'set-cover', encryptedId: string): void
}>()

const toast = useLightToast()
const { copy: clipboardCopy } = useClipboardCopy()

const isSelected = (id: string) => props.selectedIds.includes(id)

const handleClick = (_image: GalleryImage, idx: number) => {
  emit('view-image', props.images, idx)
}

const copyLink = (url: string) => {
  clipboardCopy(url, '链接已复制')
}
</script>
