<template>
  <div class="rounded-2xl border border-stone-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-900 lg:hidden">
    <div class="flex items-center justify-between gap-2">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">当前分组</p>
        <p class="truncate text-sm font-semibold text-stone-900 dark:text-white">{{ activeItem?.label || '--' }}</p>
      </div>
      <UButton color="gray" variant="soft" icon="heroicons:bars-3" @click="open = true">
        分组导航
      </UButton>
    </div>
  </div>

  <UModal v-model="open">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-base font-semibold text-stone-900 dark:text-white">存储设置分组</h3>
          <UButton color="gray" variant="ghost" icon="heroicons:x-mark" @click="open = false" />
        </div>
      </template>
      <div class="space-y-2">
        <button
          v-for="item in items"
          :key="item.key"
          type="button"
          class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors"
          :class="item.key === activeKey
            ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
            : 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800'"
          @click="handleSelect(item.key)"
        >
          <span class="flex items-center gap-2">
            <UIcon :name="item.icon" class="h-4 w-4" />
            <span>{{ item.label }}</span>
          </span>
          <span
            v-if="dirtyMap[item.key]"
            class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
            aria-hidden="true"
          />
        </button>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import type { StorageDirtyMap, StorageSectionItem, StorageSectionKey } from '~/types/admin-storage'

const props = defineProps<{
  items: StorageSectionItem[]
  activeKey: StorageSectionKey
  dirtyMap: StorageDirtyMap
}>()

const emit = defineEmits<{
  (e: 'select', key: StorageSectionKey): void
}>()

const open = ref(false)
const activeItem = computed(() => props.items.find((item) => item.key === props.activeKey))

const handleSelect = (key: StorageSectionKey) => {
  emit('select', key)
  open.value = false
}
</script>
