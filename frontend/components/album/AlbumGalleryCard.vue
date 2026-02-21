<template>
  <div
    class="relative group aspect-square rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-xl transition-all cursor-pointer bg-gray-100 dark:bg-gray-800"
    @click="$emit('click')"
  >
    <!-- 封面图 -->
    <img
      v-if="gallery.cover_url"
      :src="gallery.cover_url"
      :alt="gallery.name"
      class="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-300"
      loading="lazy"
    />
    <div v-else class="w-full h-full flex items-center justify-center">
      <UIcon name="heroicons:photo" class="w-12 h-12 text-gray-300 dark:text-gray-600" />
    </div>

    <!-- 分享状态徽章 -->
    <div v-if="gallery.share_enabled" class="absolute top-2 left-2">
      <UBadge color="green" variant="solid" size="xs">
        <UIcon name="heroicons:link" class="w-3 h-3 mr-1" />
        已分享
      </UBadge>
    </div>

    <!-- 底部渐变遮罩 -->
    <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent p-3 pt-8">
      <p class="text-white text-sm font-semibold truncate">{{ gallery.name }}</p>
      <p class="text-white/70 text-xs">{{ gallery.image_count }} 张图片</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Gallery } from '~/composables/useGalleryApi'

defineProps<{
  gallery: Gallery
}>()

defineEmits<{
  (e: 'click'): void
}>()
</script>
