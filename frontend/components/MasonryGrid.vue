<template>
  <div
    ref="containerRef"
    class="masonry-grid"
    :style="{ columnWidth: `${columnWidth}px`, columnGap: `${gap}px` }"
  >
    <div
      v-for="item in items"
      :key="item.id || item.encrypted_id"
      class="masonry-item"
      :style="{ marginBottom: `${gap}px` }"
    >
      <slot :item="item">
        <div class="relative group rounded-xl overflow-hidden border-2 border-stone-200 dark:border-neutral-700 hover:border-amber-400 transition-all hover:shadow-lg">
          <img
            :src="item.url || item.image_url"
            :alt="item.filename || item.original_filename"
            loading="lazy"
            decoding="async"
            class="w-full h-auto object-cover"
            @error="handleImageError"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <div class="absolute bottom-0 left-0 right-0 p-2">
              <p class="text-white text-xs truncate">{{ item.filename || item.original_filename }}</p>
            </div>
          </div>
        </div>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface MasonryItem {
  id?: string
  encrypted_id?: string
  url?: string
  image_url?: string
  filename?: string
  original_filename?: string
  [key: string]: any
}

withDefaults(defineProps<{
  items: MasonryItem[]
  columnWidth?: number
  gap?: number
}>(), {
  columnWidth: 240,
  gap: 12
})

const containerRef = ref<HTMLElement | null>(null)

const handleImageError = (e: Event) => {
  const img = e.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="240" height="180"%3E%3Crect fill="%23ddd" width="240" height="180" rx="8"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14"%3E加载失败%3C/text%3E%3C/svg%3E'
}
</script>

<style scoped>
.masonry-grid {
  column-count: auto;
}

.masonry-item {
  break-inside: avoid;
}
</style>
