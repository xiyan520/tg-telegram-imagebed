<template>
  <!-- 加载状态 -->
  <div v-if="loading" class="flex justify-center py-12">
    <div class="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
  </div>

  <!-- 空状态 -->
  <div v-else-if="images.length === 0" class="text-center py-12">
    <UIcon name="heroicons:photo" class="w-16 h-16 text-stone-400 mx-auto mb-4" />
    <p class="text-stone-600 dark:text-stone-400">暂无图片</p>
  </div>

  <!-- 图片网格 -->
  <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
    <div
      v-for="(image, idx) in images"
      :key="image.encrypted_id"
      class="relative group aspect-square rounded-lg overflow-hidden border-2 transition-all cursor-pointer"
      :class="isSelected(image.encrypted_id)
        ? 'border-amber-500 ring-2 ring-amber-500/50'
        : 'border-gray-200 dark:border-gray-700 hover:shadow-lg'"
      @click="handleClick(image, idx)"
    >
      <img
        :src="image.image_url"
        :alt="image.original_filename"
        class="w-full h-full object-cover"
        loading="lazy"
      />

      <!-- 选择模式复选框 -->
      <div
        v-if="showSelection"
        class="absolute top-2 left-2 z-10 w-8 h-8 -m-1 flex items-center justify-center"
        @click.stop="$emit('toggle-select', image.encrypted_id)"
      >
        <div
          class="w-5 h-5 rounded border-2 flex items-center justify-center"
          :class="isSelected(image.encrypted_id)
            ? 'bg-amber-500 border-amber-500'
            : 'bg-white/80 border-gray-300'"
        >
          <UIcon v-if="isSelected(image.encrypted_id)" name="heroicons:check" class="w-3.5 h-3.5 text-white" />
        </div>
      </div>

      <!-- 封面标记 -->
      <div v-if="showCoverBadge && coverImageId === image.encrypted_id" class="absolute top-2 right-2 z-10">
        <UBadge color="green" variant="solid" size="xs">
          <UIcon name="heroicons:star" class="w-3 h-3 mr-0.5" />封面
        </UBadge>
      </div>

      <!-- 悬浮操作 -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
        <div class="absolute top-2 right-2 flex gap-1" @click.stop>
          <UButton
            v-if="showCoverBadge && coverImageId !== image.encrypted_id"
            icon="heroicons:star"
            color="white"
            size="2xs"
            title="设为封面"
            @click="$emit('set-cover', image.encrypted_id)"
          />
          <UButton
            icon="heroicons:clipboard-document"
            color="white"
            size="2xs"
            title="复制链接"
            @click="copyLink(image.image_url)"
          />
        </div>
        <div class="absolute bottom-0 inset-x-0 p-2">
          <p class="text-white text-xs truncate">{{ image.original_filename }}</p>
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
