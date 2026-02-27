<template>
  <aside class="sticky top-24 rounded-2xl border border-stone-200/80 bg-white/95 p-3 shadow-sm backdrop-blur dark:border-neutral-700/80 dark:bg-neutral-900/90">
    <p class="px-2 pb-2 text-xs font-semibold uppercase tracking-[0.2em] text-stone-500 dark:text-stone-400">
      Setting Index
    </p>
    <nav class="space-y-1">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="group flex w-full items-start gap-2 rounded-xl px-2.5 py-2 text-left transition-colors"
        :class="item.key === activeKey
          ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
          : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-300 dark:hover:bg-neutral-800 dark:hover:text-white'"
        @click="$emit('select', item.key)"
      >
        <UIcon :name="item.icon" class="mt-0.5 h-4 w-4 flex-shrink-0" />
        <span class="min-w-0 flex-1">
          <span class="flex items-center gap-1 text-sm font-medium">
            {{ item.label }}
            <span
              v-if="dirtyMap[item.key]"
              class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
              aria-hidden="true"
            />
          </span>
          <span class="mt-0.5 block text-xs text-stone-400 dark:text-stone-500">
            {{ item.description }}
          </span>
        </span>
      </button>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import type { SettingsDirtyMap, SettingsSectionItem, SettingsSectionKey } from '~/types/admin-settings'

defineProps<{
  items: SettingsSectionItem[]
  activeKey: SettingsSectionKey
  dirtyMap: SettingsDirtyMap
}>()

defineEmits<{
  (e: 'select', key: SettingsSectionKey): void
}>()
</script>
