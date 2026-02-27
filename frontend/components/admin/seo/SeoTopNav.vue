<template>
  <div class="sticky top-20 z-20 overflow-hidden rounded-3xl border border-stone-200/80 bg-gradient-to-r from-white/95 via-white/90 to-amber-50/70 p-2.5 shadow-[0_10px_30px_-20px_rgba(245,158,11,0.45)] backdrop-blur dark:border-neutral-700/80 dark:bg-gradient-to-r dark:from-neutral-900/95 dark:via-neutral-900/90 dark:to-amber-900/20">
    <div class="overflow-x-auto pb-0.5">
      <nav class="flex min-w-max items-center gap-2">
        <button
          v-for="item in items"
          :key="item.key"
          type="button"
          class="group inline-flex items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200"
          :class="item.key === activeKey
            ? 'bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 ring-1 ring-amber-200 shadow-sm dark:from-amber-900/40 dark:to-orange-900/30 dark:text-amber-200 dark:ring-amber-800/70'
            : 'text-stone-600 hover:-translate-y-0.5 hover:bg-stone-100/80 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-neutral-800 dark:hover:text-white'"
          @click="$emit('select', item.key)"
        >
          <UIcon :name="item.icon" class="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
          <span>{{ item.label }}</span>
          <span
            v-if="dirtyMap[item.key]"
            class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500 shadow-[0_0_0_3px_rgba(251,191,36,0.2)]"
            aria-hidden="true"
          />
        </button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SeoDirtyMap, SeoSectionItem, SeoSectionKey } from '~/types/admin-seo'

defineProps<{
  items: SeoSectionItem[]
  activeKey: SeoSectionKey
  dirtyMap: SeoDirtyMap
}>()

defineEmits<{
  (e: 'select', key: SeoSectionKey): void
}>()
</script>
