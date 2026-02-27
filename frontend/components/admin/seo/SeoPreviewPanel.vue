<template>
  <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,20rem)]">
    <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/80">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">社交分享预览</p>
      <div class="mt-3 max-w-xl overflow-hidden rounded-2xl border border-stone-200 dark:border-neutral-700">
        <div v-if="ogImage" class="h-44 bg-stone-100 dark:bg-neutral-800">
          <img :src="ogImage" alt="OG 预览" class="h-full w-full object-cover" @error="hideOgImage" />
        </div>
        <div class="space-y-1.5 p-4">
          <p class="line-clamp-2 text-sm font-semibold text-stone-900 dark:text-white">{{ title }}</p>
          <p class="line-clamp-2 text-xs text-stone-500 dark:text-stone-400">{{ description }}</p>
          <div class="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-stone-500 dark:text-stone-400">
            <UBadge size="xs" color="amber" variant="subtle">{{ cardType }}</UBadge>
            <span>{{ locale }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-3 rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/80">
      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">Meta 快照</p>
      <div class="space-y-2 text-xs">
        <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/80">
          <p class="font-medium text-stone-900 dark:text-white">Canonical</p>
          <p class="mt-1 break-all text-stone-500 dark:text-stone-400">{{ canonical }}</p>
        </div>
        <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/80">
          <p class="font-medium text-stone-900 dark:text-white">Robots</p>
          <p class="mt-1 text-stone-500 dark:text-stone-400">{{ robots }}</p>
        </div>
        <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/80">
          <p class="font-medium text-stone-900 dark:text-white">Footer</p>
          <p class="mt-1 text-stone-500 dark:text-stone-400">{{ footer }}</p>
        </div>
        <div v-if="themeColor" class="rounded-xl border border-stone-200/80 bg-stone-50/80 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/80">
          <p class="font-medium text-stone-900 dark:text-white">Theme Color</p>
          <div class="mt-1 flex items-center gap-2 text-stone-500 dark:text-stone-400">
            <span class="inline-block h-3 w-3 rounded-full border border-stone-300 dark:border-neutral-600" :style="{ backgroundColor: themeColor }" />
            <span>{{ themeColor }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
  canonical: string
  robots: string
  locale: string
  footer: string
  cardType: string
  ogImage?: string
  themeColor?: string
}>()

const hideOgImage = (event: Event) => {
  const target = event.target as HTMLImageElement | null
  if (target) {
    target.style.display = 'none'
  }
}
</script>
