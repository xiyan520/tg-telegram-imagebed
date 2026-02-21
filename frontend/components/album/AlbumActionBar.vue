<template>
  <div class="flex flex-wrap items-center gap-2 py-2">
    <!-- 左侧：全选 + 条件按钮 -->
    <div class="flex flex-wrap items-center gap-2 flex-1">
      <UButton
        :icon="selectAll ? 'heroicons:check-circle' : 'heroicons:stop'"
        :color="selectAll ? 'primary' : 'gray'"
        variant="ghost"
        size="sm"
        @click="$emit('toggle-select-all')"
      >
        {{ selectAll ? '取消全选' : '全选' }}
      </UButton>

      <template v-if="selectedCount > 0">
        <UButton
          v-if="showRemove"
          icon="heroicons:trash"
          color="red"
          variant="soft"
          size="sm"
          @click="$emit('remove')"
        >
          移除 ({{ selectedCount }})
        </UButton>

        <UButton
          icon="heroicons:clipboard-document-list"
          color="gray"
          variant="soft"
          size="sm"
          @click="$emit('copy-links')"
        >
          复制链接 ({{ selectedCount }})
        </UButton>

        <UButton
          v-if="showAddToGallery"
          icon="heroicons:folder-plus"
          color="amber"
          variant="soft"
          size="sm"
          @click="$emit('add-to-gallery')"
        >
          添加到画集 ({{ selectedCount }})
        </UButton>
      </template>
    </div>

    <!-- 右侧：添加图片 + 刷新 -->
    <div class="flex items-center gap-2">
      <UButton
        v-if="showAddImages"
        icon="heroicons:plus"
        color="primary"
        variant="soft"
        size="sm"
        @click="$emit('add-images')"
      >
        添加图片
      </UButton>
      <UButton
        icon="heroicons:arrow-path"
        color="gray"
        variant="ghost"
        size="sm"
        :loading="loading"
        @click="$emit('refresh')"
      />
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
