<template>
  <!-- 删除确认弹窗 -->
  <UModal :model-value="deleteOpen" @update:model-value="emit('update:deleteOpen', $event)">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
      </template>

      <div class="space-y-3">
        <p class="text-stone-700 dark:text-stone-300">确定要删除该Token吗？此操作不可恢复。</p>
        <div v-if="deletingToken" class="text-xs text-stone-600 dark:text-stone-400">
          <div>ID：<span class="font-mono">{{ deletingToken.id }}</span></div>
          <div>Token：<span class="font-mono">{{ deletingToken.token_masked }}</span></div>
        </div>
        <!-- 影响范围 -->
        <div v-if="deleteImpact" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm space-y-1">
          <p class="font-medium text-red-700 dark:text-red-300">删除影响范围：</p>
          <p class="text-red-600 dark:text-red-400">关联图片：{{ deleteImpact.upload_count }} 张（将解除关联）</p>
          <p class="text-red-600 dark:text-red-400">拥有画集：{{ deleteImpact.gallery_count }} 个（将解除关联）</p>
          <p v-if="deleteImpact.access_count > 0" class="text-red-600 dark:text-red-400">画集授权：{{ deleteImpact.access_count }} 条（将被清除）</p>
        </div>
        <div v-else-if="loadingImpact" class="flex items-center gap-2 text-sm text-stone-500">
          <div class="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          正在查询影响范围...
        </div>
        <!-- 同时删除图片选项 -->
        <div v-if="deleteImpact && deleteImpact.upload_count > 0" class="p-3 border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/30 rounded-lg">
          <label class="flex items-start gap-2 cursor-pointer select-none">
            <input
              v-model="localDeleteWithImages"
              type="checkbox"
              class="mt-0.5 rounded border-red-400 dark:border-red-600 text-red-600 focus:ring-red-500"
            />
            <div>
              <span class="text-sm font-medium text-red-700 dark:text-red-300">
                {{ tgSyncDeleteEnabled ? '同时永久删除该Token关联的所有图片' : '同时删除该Token关联的所有图片记录' }}
              </span>
              <p class="text-xs text-red-500 dark:text-red-400 mt-0.5">
                {{ tgSyncDeleteEnabled
                  ? `将从数据库和存储后端中永久删除 ${deleteImpact.upload_count} 张图片，此操作不可恢复`
                  : `仅删除数据库中的 ${deleteImpact.upload_count} 张图片记录，存储文件将保留`
                }}
              </p>
            </div>
          </label>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="emit('update:deleteOpen', false)">取消</UButton>
          <UButton color="red" :loading="deleting" :disabled="deleting" @click="emit('confirmDelete', localDeleteWithImages)">
            {{ localDeleteWithImages ? (tgSyncDeleteEnabled ? '删除Token及图片' : '删除Token及记录') : '删除' }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>

  <!-- 批量操作确认弹窗 -->
  <UModal :model-value="batchOpen" @update:model-value="emit('update:batchOpen', $event)">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold" :class="batchAction === 'delete' ? 'text-red-600' : 'text-stone-900 dark:text-white'">
          {{ batchModalTitle }}
        </h3>
      </template>

      <div class="space-y-3">
        <p class="text-stone-700 dark:text-stone-300">{{ batchModalDesc }}</p>
        <!-- 批量删除影响范围 -->
        <div v-if="batchAction === 'delete' && batchImpact" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm space-y-1">
          <p class="font-medium text-red-700 dark:text-red-300">删除影响范围汇总：</p>
          <p class="text-red-600 dark:text-red-400">关联图片：{{ batchImpact.upload_count }} 张</p>
          <p class="text-red-600 dark:text-red-400">拥有画集：{{ batchImpact.gallery_count }} 个</p>
          <p v-if="batchImpact.access_count > 0" class="text-red-600 dark:text-red-400">画集授权：{{ batchImpact.access_count }} 条</p>
        </div>
        <div v-else-if="batchAction === 'delete' && loadingBatchImpact" class="flex items-center gap-2 text-sm text-stone-500">
          <div class="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          正在查询影响范围...
        </div>
        <!-- 批量删除：同时删除图片选项 -->
        <div v-if="batchAction === 'delete' && batchImpact && batchImpact.upload_count > 0" class="p-3 border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/30 rounded-lg">
          <label class="flex items-start gap-2 cursor-pointer select-none">
            <input
              v-model="localBatchDeleteWithImages"
              type="checkbox"
              class="mt-0.5 rounded border-red-400 dark:border-red-600 text-red-600 focus:ring-red-500"
            />
            <div>
              <span class="text-sm font-medium text-red-700 dark:text-red-300">
                {{ tgSyncDeleteEnabled ? '同时永久删除这些Token关联的所有图片' : '同时删除这些Token关联的所有图片记录' }}
              </span>
              <p class="text-xs text-red-500 dark:text-red-400 mt-0.5">
                {{ tgSyncDeleteEnabled
                  ? `将从数据库和存储后端中永久删除 ${batchImpact.upload_count} 张图片，此操作不可恢复`
                  : `仅删除数据库中的 ${batchImpact.upload_count} 张图片记录，存储文件将保留`
                }}
              </p>
            </div>
          </label>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="emit('update:batchOpen', false)">取消</UButton>
          <UButton
            :color="batchAction === 'delete' ? 'red' : 'primary'"
            :loading="batchProcessing"
            :disabled="batchProcessing"
            @click="emit('confirmBatch', localBatchDeleteWithImages)"
          >
            {{ batchAction === 'delete' && localBatchDeleteWithImages ? (tgSyncDeleteEnabled ? '删除Token及图片' : '删除Token及记录') : '确认' }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import type { AdminTokenItem } from '~/types/admin'

export interface ImpactData {
  upload_count: number
  gallery_count: number
  access_count: number
  token_count?: number
}

const props = defineProps<{
  // 删除弹窗
  deleteOpen: boolean
  deletingToken: AdminTokenItem | null
  deleteImpact: ImpactData | null
  loadingImpact: boolean
  deleting: boolean
  // 批量弹窗
  batchOpen: boolean
  batchAction: 'enable' | 'disable' | 'delete'
  batchImpact: ImpactData | null
  loadingBatchImpact: boolean
  batchProcessing: boolean
  selectedCount: number
  // 共享
  tgSyncDeleteEnabled: boolean
}>()

const emit = defineEmits<{
  'update:deleteOpen': [value: boolean]
  'confirmDelete': [withImages: boolean]
  'update:batchOpen': [value: boolean]
  'confirmBatch': [withImages: boolean]
}>()

// 本地 checkbox 状态
const localDeleteWithImages = ref(false)
const localBatchDeleteWithImages = ref(false)

// 弹窗关闭时重置
watch(() => props.deleteOpen, (v) => { if (!v) localDeleteWithImages.value = false })
watch(() => props.batchOpen, (v) => { if (!v) localBatchDeleteWithImages.value = false })

const batchModalTitle = computed(() => {
  const map = { enable: '批量启用', disable: '批量禁用', delete: '批量删除' }
  return map[props.batchAction] || '批量操作'
})

const batchModalDesc = computed(() => {
  const n = props.selectedCount
  const map = {
    enable: `确定要启用选中的 ${n} 个 Token 吗？`,
    disable: `确定要禁用选中的 ${n} 个 Token 吗？禁用后这些 Token 将无法使用。`,
    delete: `确定要删除选中的 ${n} 个 Token 吗？此操作不可恢复。`,
  }
  return map[props.batchAction] || ''
})
</script>
