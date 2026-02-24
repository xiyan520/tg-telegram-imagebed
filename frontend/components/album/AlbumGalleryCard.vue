<template>
  <div
    class="relative group rounded-2xl overflow-hidden border border-stone-200/60 dark:border-neutral-700/60 hover:shadow-lg hover:shadow-amber-500/10 transition-all duration-300 cursor-pointer bg-stone-100 dark:bg-neutral-800"
    @click="$emit('click')"
  >
    <!-- 封面图（16:10 比例） -->
    <div class="aspect-[16/10] overflow-hidden">
      <img
        v-if="gallery.cover_url"
        :src="gallery.cover_url"
        :alt="gallery.name"
        class="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500"
        loading="lazy"
      />
      <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-stone-100 to-stone-200 dark:from-neutral-800 dark:to-neutral-700">
        <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-300 dark:text-neutral-600" />
      </div>
    </div>

    <!-- 分享状态徽章 -->
    <div v-if="gallery.share_enabled" class="absolute top-2.5 left-2.5">
      <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/90 backdrop-blur-sm text-white text-xs font-medium">
        <UIcon name="heroicons:link" class="w-3 h-3" />
        已分享
      </div>
    </div>

    <!-- 底部信息 -->
    <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 pt-10">
      <p class="text-white text-sm font-semibold truncate">{{ gallery.name }}</p>
      <p class="text-white/60 text-xs mt-0.5">{{ gallery.image_count }} 张图片</p>
    </div>

    <!-- hover 遮罩 -->
    <div class="absolute inset-0 bg-amber-500/0 group-hover:bg-amber-500/5 transition-colors duration-300" />
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
