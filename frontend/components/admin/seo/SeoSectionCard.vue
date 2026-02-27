<template>
  <section class="group relative scroll-mt-24 space-y-3 overflow-hidden rounded-3xl border border-stone-200/80 bg-white/95 p-3 shadow-[0_18px_40px_-30px_rgba(15,23,42,0.45)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_48px_-30px_rgba(245,158,11,0.45)] dark:border-neutral-700/80 dark:bg-neutral-900/90 sm:p-4">
    <div class="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-50/55 via-transparent to-orange-50/40 opacity-70 transition-opacity duration-300 group-hover:opacity-100 dark:from-amber-900/10 dark:to-orange-900/10" aria-hidden="true" />
    <div class="relative flex flex-wrap items-center justify-between gap-2">
      <div class="min-w-0">
        <p class="flex items-center gap-2 text-sm font-semibold text-stone-900 dark:text-white">
          <UIcon :name="icon" class="h-4 w-4 text-amber-500 transition-transform duration-300 group-hover:rotate-6 group-hover:scale-110" />
          <span>{{ title }}</span>
          <UBadge v-if="dirty" color="amber" variant="subtle" size="xs">未保存</UBadge>
        </p>
        <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">{{ description }}</p>
      </div>
      <UButton
        size="xs"
        color="amber"
        variant="soft"
        :loading="saving"
        @click="$emit('save')"
      >
        保存本分组
      </UButton>
    </div>
    <div class="relative">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
  icon: string
  dirty?: boolean
  saving?: boolean
}>()

defineEmits<{
  (e: 'save'): void
}>()
</script>
