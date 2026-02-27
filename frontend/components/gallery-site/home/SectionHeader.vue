<template>
  <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div class="space-y-2">
      <p v-if="eyebrow" class="text-xs font-semibold uppercase tracking-[0.24em] text-amber-600 dark:text-amber-400">
        {{ eyebrow }}
      </p>
      <h2 class="text-2xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-3xl">
        {{ title }}
      </h2>
      <p v-if="description" class="max-w-2xl text-sm leading-relaxed text-stone-500 dark:text-stone-400 sm:text-base">
        {{ description }}
      </p>
    </div>
    <NuxtLink
      v-if="actionTo && actionLabel"
      :to="actionTo"
      class="inline-flex items-center gap-1.5 text-sm font-medium text-amber-600 transition-colors hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
    >
      {{ actionLabel }}
      <UIcon name="heroicons:arrow-right" class="h-4 w-4" />
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string
  description?: string
  eyebrow?: string
  actionTo?: string
  actionLabel?: string
}

defineProps<Props>()
</script>
