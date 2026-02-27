<template>
  <div class="space-y-4 pb-16">
    <AdminPageHeader
      title="图片管理"
      eyebrow="Resources"
      icon="heroicons:photo"
      :description="`共 ${totalCount} 张图片`"
    >
      <template #meta>
        <UBadge color="gray" variant="subtle" size="xs">{{ `第 ${currentPage} / ${totalPages} 页` }}</UBadge>
        <UBadge color="blue" variant="subtle" size="xs">{{ `每页 ${pageSize} 张` }}</UBadge>
        <UBadge v-if="selectedCount > 0" color="amber" variant="subtle" size="xs">
          {{ `已选 ${selectedCount} 张` }}
        </UBadge>
      </template>
    </AdminPageHeader>

    <div class="sticky top-16 z-20">
      <AdminImagesToolbar
        :search-query="searchQuery"
        :primary-filter="primaryFilter"
        :page-size="pageSize"
        :view-mode="viewMode"
        :selected-count="selectedCount"
        :loading="loading || refreshing"
        :has-active-advanced-filters="hasActiveAdvancedFilters"
        :is-all-on-page-selected="isAllOnPageSelected"
        :is-page-partially-selected="isPagePartiallySelected"
        :sort-by="sortBy"
        :sort-order="sortOrder"
        :primary-filter-options="primaryFilterOptions"
        :page-size-options="pageSizeOptions"
        :sort-by-options="sortByOptions"
        :sort-order-options="sortOrderOptions"
        @update:search-query="setSearchQuery"
        @update:primary-filter="onPrimaryFilterChange"
        @update:page-size="onPageSizeChange"
        @update:view-mode="onViewModeChange"
        @update:sort-by="onSortByChange"
        @update:sort-order="onSortOrderChange"
        @toggle-select-page="toggleSelectAllOnPage"
        @refresh="refresh"
        @open-advanced="openAdvancedPanel"
        @reset-advanced="resetAdvancedFilters"
        @delete-selected="openDeleteForSelection"
        @copy-selected="copySelectedUrls"
        @clear-selection="clearSelection"
        @clear-cache="clearCacheAction"
      />
    </div>

    <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
      <div v-if="loading" class="flex flex-col items-center justify-center py-20">
        <div class="h-14 w-14 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
        <p class="mt-3 text-sm text-stone-500 dark:text-stone-400">加载中...</p>
      </div>

      <div v-else-if="images.length === 0" class="py-20 text-center">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-stone-100 dark:bg-neutral-800">
          <UIcon name="heroicons:photo" class="h-8 w-8 text-stone-400" />
        </div>
        <p class="mt-4 text-base font-semibold text-stone-900 dark:text-white">暂无图片</p>
        <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">当前筛选条件下没有匹配结果</p>
        <div class="mt-4 flex justify-center gap-2">
          <UButton color="gray" variant="ghost" @click="resetAdvancedFilters">清空筛选</UButton>
          <UButton color="gray" variant="outline" @click="refresh">刷新数据</UButton>
        </div>
      </div>

      <AdminImagesListView
        v-else-if="viewMode === 'list'"
        :images="images"
        :selected-ids="selectedIds"
        @toggle-select="toggleSelect"
        @view-detail="openDetail"
        @copy-url="copyImageUrl"
        @delete="openDeleteForSingle"
      />

      <AdminImagesGridView
        v-else-if="viewMode === 'grid'"
        :images="images"
        :selected-ids="selectedIds"
        @toggle-select="toggleSelect"
        @view-detail="openDetail"
        @copy-url="copyImageUrl"
        @delete="openDeleteForSingle"
      />

      <AdminImagesMasonryView
        v-else
        :images="images"
        :selected-ids="selectedIds"
        @toggle-select="toggleSelect"
        @view-detail="openDetail"
        @copy-url="copyImageUrl"
        @delete="openDeleteForSingle"
      />

      <template #footer>
        <div class="flex flex-col items-center justify-between gap-3 pt-2 sm:flex-row">
          <p class="text-xs text-stone-500 dark:text-stone-400">{{ pageSummary }}</p>
          <UPagination
            v-model="currentPage"
            :total="totalCount"
            :page-count="Number(pageSize)"
            @update:model-value="changePage"
          />
        </div>
      </template>
    </UCard>

    <div
      v-if="selectedCount > 0"
      class="fixed inset-x-3 bottom-20 z-40 rounded-2xl border border-stone-200/85 bg-white/95 p-2.5 shadow-lg backdrop-blur dark:border-neutral-700/80 dark:bg-neutral-900/92 md:hidden"
    >
      <div class="mb-2 text-center text-xs font-medium text-stone-600 dark:text-stone-300">
        已选 {{ selectedCount }} 张图片
      </div>
      <div class="grid grid-cols-3 gap-2">
        <UButton color="gray" variant="soft" block size="sm" @click="clearSelection">取消</UButton>
        <UButton color="blue" variant="soft" block size="sm" icon="heroicons:link" @click="copySelectedUrls">复制</UButton>
        <UButton color="red" variant="soft" block size="sm" icon="heroicons:trash" @click="openDeleteForSelection">删除</UButton>
      </div>
    </div>

    <UModal v-model="detailModalOpen" :ui="{ width: 'sm:max-w-5xl', height: 'max-h-[92dvh]' }">
      <div class="max-h-[90dvh] overflow-hidden rounded-xl bg-white dark:bg-neutral-900">
        <AdminImagesDetailPanel
          :image="selectedImage"
          :has-prev="hasPrevDetail"
          :has-next="hasNextDetail"
          @close="closeDetail"
          @copy="copyImageUrl(selectedImage?.url)"
          @prev="goPrevDetail"
          @next="goNextDetail"
          @download="downloadImage(selectedImage)"
          @delete="deleteCurrentDetailImage"
        />
      </div>
    </UModal>

    <UModal v-model="deleteModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
        </template>

        <div class="space-y-3">
          <p class="text-sm text-stone-700 dark:text-stone-300">
            {{ tgSyncDeleteEnabled ? deleteMessage : `${deleteMessage.replace('此操作不可恢复。', '')}仅删除数据库中的图片记录。` }}
          </p>

          <div v-if="tgSyncDeleteEnabled" class="rounded-lg border border-red-300 bg-red-50 p-3 dark:border-red-700 dark:bg-red-900/30">
            <label class="flex cursor-pointer items-start gap-2 select-none">
              <input
                v-model="deleteWithStorage"
                type="checkbox"
                class="mt-0.5 rounded border-red-400 text-red-600 focus:ring-red-500 dark:border-red-600"
              >
              <div>
                <span class="text-sm font-medium text-red-700 dark:text-red-300">同时删除存储库中的文件</span>
                <p class="mt-0.5 text-xs text-red-500 dark:text-red-400">将同步删除存储后端文件与 TG 消息，此操作不可恢复</p>
              </div>
            </label>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="closeDeleteModal">取消</UButton>
            <UButton color="red" :loading="deleting" @click="confirmDelete">
              {{ tgSyncDeleteEnabled && deleteWithStorage ? '删除记录及文件' : '仅删除记录' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <USlideover v-model="advancedPanelOpen" side="right" :ui="{ width: 'max-w-md' }">
      <AdminImagesAdvancedFilters
        v-model="advancedFilters"
        :source-options="sourceOptions"
        @apply="onAdvancedApply"
        @reset="resetAdvancedFilters"
        @cancel="closeAdvancedPanel"
      />
    </USlideover>
  </div>
</template>

<script setup lang="ts">
import AdminPageHeader from '~/components/admin/common/AdminPageHeader.vue'
import AdminImagesToolbar from '~/components/admin/images/AdminImagesToolbar.vue'
import AdminImagesAdvancedFilters from '~/components/admin/images/AdminImagesAdvancedFilters.vue'
import AdminImagesDetailPanel from '~/components/admin/images/AdminImagesDetailPanel.vue'
import AdminImagesListView from '~/components/admin/images/views/AdminImagesListView.vue'
import AdminImagesGridView from '~/components/admin/images/views/AdminImagesGridView.vue'
import AdminImagesMasonryView from '~/components/admin/images/views/AdminImagesMasonryView.vue'
import type { AdminImageSortBy, AdminImageSortOrder } from '~/types/api'
import type {
  AdminLegacyFilter,
  AdminImagesAdvancedFilters as AdminImagesAdvancedFiltersValue,
  AdminImagesViewMode,
} from '~/composables/useAdminImages'

definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const {
  loading,
  refreshing,
  deleting,
  images,
  selectedIds,
  selectedCount,
  isAllOnPageSelected,
  isPagePartiallySelected,
  searchQuery,
  primaryFilter,
  sortBy,
  sortOrder,
  advancedFilters,
  hasActiveAdvancedFilters,
  currentPage,
  totalPages,
  totalCount,
  pageSize,
  viewMode,
  advancedPanelOpen,
  detailModalOpen,
  selectedImage,
  hasPrevDetail,
  hasNextDetail,
  deleteModalOpen,
  deleteMessage,
  deleteWithStorage,
  tgSyncDeleteEnabled,
  pageSizeOptions,
  primaryFilterOptions,
  sortByOptions,
  sortOrderOptions,
  sourceOptions,
  initialize,
  refresh,
  setSearchQuery,
  applyPrimaryFilter,
  applyPageSize,
  applySorting,
  applyAdvancedFilters,
  resetAdvancedFilters,
  openAdvancedPanel,
  closeAdvancedPanel,
  changePage,
  toggleSelect,
  toggleSelectAllOnPage,
  clearSelection,
  openDetail,
  goPrevDetail,
  goNextDetail,
  closeDetail,
  downloadImage,
  deleteCurrentDetailImage,
  copyImageUrl,
  copySelectedUrls,
  openDeleteForSingle,
  openDeleteForSelection,
  closeDeleteModal,
  confirmDelete,
  clearCacheAction,
} = useAdminImages()

const onPrimaryFilterChange = (value: AdminLegacyFilter) => {
  applyPrimaryFilter(value)
}

const onPageSizeChange = (value: number) => {
  applyPageSize(value)
}

const onSortByChange = (value: AdminImageSortBy) => {
  applySorting(value, sortOrder.value)
}

const onSortOrderChange = (value: AdminImageSortOrder) => {
  applySorting(sortBy.value, value)
}

const onViewModeChange = (value: AdminImagesViewMode) => {
  viewMode.value = value
}

const onAdvancedApply = (value: AdminImagesAdvancedFiltersValue) => {
  applyAdvancedFilters(value)
}

const pageSummary = computed(() => {
  if (totalCount.value <= 0) return '暂无数据'
  const start = (currentPage.value - 1) * Number(pageSize.value) + 1
  const end = Math.min(currentPage.value * Number(pageSize.value), totalCount.value)
  return `显示 ${start}-${end} / 共 ${totalCount.value} 张`
})

onMounted(() => {
  initialize()
})
</script>
