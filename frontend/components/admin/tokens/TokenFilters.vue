<template>
  <UCard>
    <div class="flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <UInput
          :model-value="searchQuery"
          placeholder="搜索 Token / 描述 / TG用户名..."
          size="sm"
          class="w-full sm:w-60"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        >
          <template #leading>
            <UIcon name="heroicons:magnifying-glass" class="w-4 h-4" />
          </template>
        </UInput>
        <span class="text-xs text-stone-500 dark:text-stone-400">状态</span>
        <USelect
          :model-value="status"
          :options="statusOptions"
          size="sm"
          class="w-28"
          @update:model-value="emit('update:status', $event)"
        />
        <span class="text-xs text-stone-500 dark:text-stone-400">TG 绑定</span>
        <USelect
          :model-value="tgBind"
          :options="tgBindOptions"
          size="sm"
          class="w-28"
          @update:model-value="emit('update:tgBind', $event)"
        />

        <span class="text-xs text-stone-500 dark:text-stone-400">排序</span>
        <USelect
          :model-value="sortBy"
          :options="sortByOptions"
          size="sm"
          class="w-36"
          @update:model-value="emit('update:sortBy', $event)"
        />
        <USelect
          :model-value="sortOrder"
          :options="sortOrderOptions"
          size="sm"
          class="w-24"
          @update:model-value="emit('update:sortOrder', $event)"
        />
      </div>

      <!-- 批量操作按钮 -->
      <div v-if="selectedCount > 0" class="flex flex-wrap items-center gap-2">
        <span class="text-sm text-amber-600 dark:text-amber-400 font-medium">
          已选 {{ selectedCount }} 项
        </span>
        <UButton size="sm" color="green" variant="soft" @click="emit('batch', 'enable')">批量启用</UButton>
        <UButton size="sm" color="gray" variant="soft" @click="emit('batch', 'disable')">批量禁用</UButton>
        <UButton size="sm" color="red" variant="soft" @click="emit('batch', 'delete')">批量删除</UButton>
        <UButton size="sm" color="gray" variant="ghost" @click="emit('clearSelection')">取消选择</UButton>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '启用', value: 'active' },
  { label: '禁用', value: 'disabled' },
  { label: '已过期', value: 'expired' },
]

const tgBindOptions = [
  { label: '全部', value: 'all' },
  { label: '已绑定', value: 'bound' },
  { label: '未绑定', value: 'unbound' },
]

const sortByOptions = [
  { label: '创建时间', value: 'created_at' },
  { label: '上传次数', value: 'upload_count' },
  { label: '过期时间', value: 'expires_at' },
  { label: '最后使用', value: 'last_used' },
]

const sortOrderOptions = [
  { label: '降序', value: 'desc' },
  { label: '升序', value: 'asc' },
]

defineProps<{
  searchQuery: string
  status: string
  tgBind: string
  sortBy: string
  sortOrder: string
  selectedCount: number
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:status': [value: string]
  'update:tgBind': [value: string]
  'update:sortBy': [value: string]
  'update:sortOrder': [value: string]
  'batch': [action: 'enable' | 'disable' | 'delete']
  'clearSelection': []
}>()
</script>
