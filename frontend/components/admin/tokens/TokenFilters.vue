<template>
  <UCard>
    <div class="flex flex-col gap-4 md:flex-row md:items-center">
      <div class="flex items-center gap-2 flex-wrap">
        <UInput
          :model-value="searchQuery"
          placeholder="搜索 Token / 描述 / TG用户名..."
          size="sm"
          class="w-48"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        >
          <template #leading>
            <UIcon name="heroicons:magnifying-glass" class="w-4 h-4" />
          </template>
        </UInput>
        <span class="text-sm text-stone-600 dark:text-stone-400">状态</span>
        <USelect
          :model-value="status"
          :options="statusOptions"
          size="sm"
          @update:model-value="emit('update:status', $event)"
        />
        <span class="text-sm text-stone-600 dark:text-stone-400">TG绑定</span>
        <USelect
          :model-value="tgBind"
          :options="tgBindOptions"
          size="sm"
          @update:model-value="emit('update:tgBind', $event)"
        />
      </div>

      <!-- 批量操作按钮 -->
      <div v-if="selectedCount > 0" class="flex items-center gap-2">
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

defineProps<{
  searchQuery: string
  status: string
  tgBind: string
  selectedCount: number
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:status': [value: string]
  'update:tgBind': [value: string]
  'batch': [action: 'enable' | 'disable' | 'delete']
  'clearSelection': []
}>()
</script>
