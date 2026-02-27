<template>
  <section class="relative scroll-mt-24 rounded-2xl border border-stone-200/80 bg-white p-3 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900 sm:group sm:space-y-3 sm:overflow-hidden sm:rounded-3xl sm:bg-white/95 sm:p-4 sm:shadow-[0_18px_40px_-30px_rgba(15,23,42,0.45)] sm:transition-all sm:duration-300 sm:hover:-translate-y-0.5 sm:hover:shadow-[0_24px_48px_-30px_rgba(245,158,11,0.45)] sm:dark:bg-neutral-900/90">
    <div class="pointer-events-none absolute inset-0 hidden bg-gradient-to-br from-amber-50/55 via-transparent to-orange-50/40 opacity-70 transition-opacity duration-300 sm:block sm:group-hover:opacity-100 dark:from-amber-900/10 dark:to-orange-900/10" aria-hidden="true" />
    <div class="relative flex flex-wrap items-start justify-between gap-2">
      <div class="min-w-0">
        <p class="flex items-center gap-2 text-sm font-semibold text-stone-900 dark:text-white">
          <UIcon :name="icon" class="h-4 w-4 text-amber-500 sm:transition-transform sm:duration-300 sm:group-hover:rotate-6 sm:group-hover:scale-110" />
          <span>{{ title }}</span>
          <UBadge v-if="dirty" color="amber" variant="subtle" size="xs">未保存</UBadge>
        </p>
        <p class="mt-1 hidden text-xs text-stone-500 dark:text-stone-400 sm:block">{{ description }}</p>
      </div>
      <div class="flex items-center gap-2">
        <slot name="actions" />
        <UButton
          v-if="showSave"
          size="xs"
          color="amber"
          variant="soft"
          :loading="saving"
          @click="$emit('save')"
        >
          {{ saveLabel }}
        </UButton>
      </div>
    </div>
    <div class="relative">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description: string
  icon: string
  dirty?: boolean
  saving?: boolean
  showSave?: boolean
  saveLabel?: string
}>(), {
  showSave: true,
  saveLabel: '保存本分组',
})

defineEmits<{
  (e: 'save'): void
}>()
</script>
