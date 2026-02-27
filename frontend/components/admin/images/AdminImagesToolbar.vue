<template>
  <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
    <div class="space-y-3">
      <div class="flex flex-col gap-2 lg:flex-row lg:items-center">
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <UInput
            :model-value="searchQuery"
            placeholder="搜索文件名 / 用户名..."
            icon="heroicons:magnifying-glass"
            class="w-full lg:max-w-sm"
            @update:model-value="emit('update:searchQuery', String($event || ''))"
          />

          <UButton
            class="shrink-0 lg:hidden"
            color="gray"
            variant="outline"
            icon="heroicons:funnel"
            :label="hasActiveAdvancedFilters ? '筛选中' : '筛选'"
            @click="$emit('open-advanced')"
          />
        </div>

        <div class="hidden flex-wrap items-center gap-2 lg:flex">
          <USelect
            :model-value="primaryFilter"
            :options="primaryFilterOptions"
            option-attribute="label"
            value-attribute="value"
            size="sm"
            class="w-32"
            @update:model-value="$emit('update:primaryFilter', $event as AdminLegacyFilter)"
          />
          <USelect
            :model-value="sortBy"
            :options="sortByOptions"
            option-attribute="label"
            value-attribute="value"
            size="sm"
            class="w-36"
            @update:model-value="$emit('update:sortBy', $event as AdminImageSortBy)"
          />
          <USelect
            :model-value="sortOrder"
            :options="sortOrderOptions"
            option-attribute="label"
            value-attribute="value"
            size="sm"
            class="w-24"
            @update:model-value="$emit('update:sortOrder', $event as AdminImageSortOrder)"
          />
          <USelect
            :model-value="pageSize"
            :options="pageSizeOptions"
            option-attribute="label"
            value-attribute="value"
            size="sm"
            class="w-28"
            @update:model-value="$emit('update:pageSize', Number($event))"
          />

          <div class="inline-flex overflow-hidden rounded-lg border border-stone-200 dark:border-neutral-700">
            <button
              type="button"
              class="px-2.5 py-1.5 text-sm transition-colors"
              :class="viewMode === 'list'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'text-stone-500 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800'"
              @click="$emit('update:viewMode', 'list')"
            >
              <UIcon name="heroicons:list-bullet" class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="px-2.5 py-1.5 text-sm transition-colors"
              :class="viewMode === 'grid'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'text-stone-500 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800'"
              @click="$emit('update:viewMode', 'grid')"
            >
              <UIcon name="heroicons:squares-2x2" class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="px-2.5 py-1.5 text-sm transition-colors"
              :class="viewMode === 'masonry'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'text-stone-500 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-neutral-800'"
              @click="$emit('update:viewMode', 'masonry')"
            >
              <UIcon name="heroicons:view-columns" class="h-4 w-4" />
            </button>
          </div>

          <UButton
            color="gray"
            variant="outline"
            icon="heroicons:funnel"
            :label="hasActiveAdvancedFilters ? '筛选中' : '高级筛选'"
            @click="$emit('open-advanced')"
          />
          <UButton
            v-if="hasActiveAdvancedFilters"
            color="gray"
            variant="ghost"
            icon="heroicons:x-mark"
            @click="$emit('reset-advanced')"
          >
            清空筛选
          </UButton>
          <UButton
            color="gray"
            variant="ghost"
            icon="heroicons:arrow-path"
            :loading="loading"
            @click="$emit('refresh')"
          />
          <UButton
            color="yellow"
            variant="soft"
            icon="heroicons:bolt"
            @click="$emit('clear-cache')"
          >
            清理缓存
          </UButton>
        </div>
      </div>

      <div class="flex items-center justify-between gap-2 rounded-xl border border-stone-200/80 bg-stone-50/80 px-3 py-2 dark:border-neutral-700/80 dark:bg-neutral-800/60">
        <div class="flex min-w-0 items-center gap-2">
          <UCheckbox
            :model-value="isAllOnPageSelected"
            @change="$emit('toggle-select-page')"
          />
          <span class="text-sm text-stone-600 dark:text-stone-300">
            已选 <span class="font-semibold text-amber-600 dark:text-amber-400">{{ selectedCount }}</span> 张
          </span>
          <span
            v-if="isPagePartiallySelected"
            class="text-xs text-stone-500 dark:text-stone-400"
          >
            （本页部分选中）
          </span>
        </div>

        <div class="flex items-center gap-1.5">
          <UButton
            size="xs"
            color="gray"
            variant="ghost"
            :disabled="selectedCount === 0"
            @click="$emit('clear-selection')"
          >
            取消选择
          </UButton>
          <UButton
            size="xs"
            color="blue"
            variant="soft"
            icon="heroicons:link"
            :disabled="selectedCount === 0"
            @click="$emit('copy-selected')"
          >
            复制链接
          </UButton>
          <UButton
            size="xs"
            color="red"
            variant="soft"
            icon="heroicons:trash"
            :disabled="selectedCount === 0"
            @click="$emit('delete-selected')"
          >
            删除
          </UButton>
        </div>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { AdminImageSortBy, AdminImageSortOrder } from '~/types/api'
import type { AdminLegacyFilter, AdminImagesViewMode } from '~/composables/useAdminImages'

defineProps<{
  searchQuery: string
  primaryFilter: AdminLegacyFilter
  pageSize: number
  viewMode: AdminImagesViewMode
  selectedCount: number
  loading: boolean
  hasActiveAdvancedFilters: boolean
  isAllOnPageSelected: boolean
  isPagePartiallySelected: boolean
  sortBy: AdminImageSortBy
  sortOrder: AdminImageSortOrder
  primaryFilterOptions: Array<{ label: string; value: string }>
  pageSizeOptions: Array<{ label: string; value: number }>
  sortByOptions: Array<{ label: string; value: string }>
  sortOrderOptions: Array<{ label: string; value: string }>
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:primaryFilter': [value: AdminLegacyFilter]
  'update:pageSize': [value: number]
  'update:viewMode': [value: AdminImagesViewMode]
  'update:sortBy': [value: AdminImageSortBy]
  'update:sortOrder': [value: AdminImageSortOrder]
  'toggle-select-page': []
  refresh: []
  'open-advanced': []
  'reset-advanced': []
  'delete-selected': []
  'copy-selected': []
  'clear-selection': []
  'clear-cache': []
}>()

</script>
