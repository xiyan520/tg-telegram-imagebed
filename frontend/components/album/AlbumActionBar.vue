<template>
  <div class="flex flex-wrap items-center gap-2 py-2.5 px-3 bg-white/60 dark:bg-neutral-800/60 backdrop-blur-sm rounded-xl border border-stone-200/50 dark:border-neutral-700/50">
    <!-- 左侧：全选 + 条件按钮 -->
    <div class="flex flex-wrap items-center gap-1.5 flex-1">
      <button
        class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all"
        :class="selectAll
          ? 'bg-amber-500 text-white shadow-sm shadow-amber-500/25'
          : 'text-stone-500 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-neutral-700/50'"
        @click="$emit('toggle-select-all')"
      >
        <UIcon :name="selectAll ? 'heroicons:check-circle' : 'heroicons:stop'" class="w-3.5 h-3.5" />
        {{ selectAll ? '取消全选' : '全选' }}
      </button>

      <template v-if="selectedCount > 0">
        <div class="w-px h-4 bg-stone-200 dark:bg-neutral-700" />

        <button
          v-if="showRemove"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
          @click="$emit('remove')"
        >
          <UIcon name="heroicons:trash" class="w-3.5 h-3.5" />
          移除 ({{ selectedCount }})
        </button>

        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-700/50 transition-all"
          @click="$emit('copy-links')"
        >
          <UIcon name="heroicons:clipboard-document-list" class="w-3.5 h-3.5" />
          复制链接 ({{ selectedCount }})
        </button>

        <button
          v-if="showAddToGallery"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all"
          @click="$emit('add-to-gallery')"
        >
          <UIcon name="heroicons:folder-plus" class="w-3.5 h-3.5" />
          添加到画集 ({{ selectedCount }})
        </button>
      </template>
    </div>

    <!-- 右侧：添加图片 + 刷新 -->
    <div class="flex items-center gap-1.5">
      <button
        v-if="showAddImages"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500 text-white hover:bg-amber-600 shadow-sm shadow-amber-500/25 transition-all"
        @click="$emit('add-images')"
      >
        <UIcon name="heroicons:plus" class="w-3.5 h-3.5" />
        添加图片
      </button>
      <button
        class="inline-flex items-center justify-center w-8 h-8 rounded-lg text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-700/50 transition-all"
        :class="{ 'animate-spin': loading }"
        @click="$emit('refresh')"
      >
        <UIcon name="heroicons:arrow-path" class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  selectedCount: number
  totalCount: number
  selectAll: boolean
  showRemove?: boolean
  showAddToGallery?: boolean
  showAddImages?: boolean
  loading?: boolean
}>()

defineEmits<{
  (e: 'toggle-select-all'): void
  (e: 'remove'): void
  (e: 'copy-links'): void
  (e: 'add-to-gallery'): void
  (e: 'add-images'): void
  (e: 'refresh'): void
}>()
</script>
