<template>
  <section class="rounded-2xl border border-stone-200/85 bg-white/92 px-4 py-3 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88 sm:px-5 sm:py-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0 space-y-1">
        <div class="flex min-w-0 items-center gap-2.5">
          <div
            v-if="icon"
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 shadow-sm shadow-amber-500/20"
          >
            <UIcon :name="icon" class="h-4.5 w-4.5 text-white" />
          </div>

          <div class="min-w-0">
            <p v-if="eyebrow" class="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-600 dark:text-amber-400">
              {{ eyebrow }}
            </p>
            <h1 class="truncate text-xl font-bold text-stone-900 dark:text-white sm:text-2xl">
              {{ title }}
            </h1>
          </div>
        </div>

        <p v-if="description" class="text-sm text-stone-500 dark:text-stone-400">
          {{ description }}
        </p>

        <div v-if="$slots.meta" class="flex flex-wrap items-center gap-2 pt-1">
          <slot name="meta" />
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 sm:justify-end">
        <slot name="actions" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  eyebrow?: string
  icon?: string
}>()
</script>
