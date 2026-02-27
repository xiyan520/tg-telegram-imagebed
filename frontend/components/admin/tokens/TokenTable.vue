<template>
  <UCard>
    <div v-if="loading" class="flex flex-col justify-center items-center py-16">
      <div class="w-14 h-14 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-stone-600 dark:text-stone-400">加载中...</p>
    </div>

    <div v-else-if="tokens.length === 0" class="text-center py-16">
      <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
        <UIcon name="heroicons:key" class="w-10 h-10 text-stone-400" />
      </div>
      <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无Token</p>
      <p class="text-sm text-stone-600 dark:text-stone-400">点击右上角"创建Token"开始使用</p>
    </div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left text-stone-600 dark:text-stone-300 border-b border-stone-200/60 dark:border-neutral-700/60">
            <th class="py-3 pr-2 font-medium w-10">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate="isPartialSelected"
                class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
                @change="emit('toggleSelectAll')"
              />
            </th>
            <th class="py-3 pr-4 font-medium">Token</th>
            <th class="py-3 pr-4 font-medium">描述</th>
            <th class="py-3 pr-4 font-medium">状态</th>
            <th class="py-3 pr-4 font-medium hidden md:table-cell">上传</th>
            <th class="py-3 pr-4 font-medium hidden lg:table-cell">TG 绑定</th>
            <th class="py-3 pr-4 font-medium hidden lg:table-cell">创建时间</th>
            <th class="py-3 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-stone-200/50 dark:divide-neutral-700/50">
          <tr
            v-for="t in tokens"
            :key="t.id"
            class="text-stone-800 dark:text-stone-100 cursor-pointer transition-colors"
            :class="[
              selectedIds.includes(t.id) ? 'bg-amber-50/50 dark:bg-amber-900/10' : 'hover:bg-stone-50 dark:hover:bg-neutral-800/50'
            ]"
            @click="emit('selectToken', t.id)"
          >
            <td class="py-3 pr-2" @click.stop>
              <input
                type="checkbox"
                :checked="selectedIds.includes(t.id)"
                class="rounded border-stone-300 dark:border-neutral-600 text-amber-500 focus:ring-amber-500"
                @change="emit('toggleSelect', t.id)"
              />
            </td>
            <td class="py-3 pr-4">
              <code class="font-mono text-xs px-2 py-1 rounded bg-stone-100 dark:bg-neutral-800">
                {{ t.token_masked }}
              </code>
            </td>
            <td class="py-3 pr-4 max-w-[16rem]">
              <span class="text-stone-700 dark:text-stone-300 truncate block text-xs">
                {{ t.description?.trim() ? t.description : '--' }}
              </span>
            </td>
            <td class="py-3 pr-4">
              <UBadge v-if="isExpired(t)" color="amber" variant="subtle" size="xs">已过期</UBadge>
              <UBadge v-else :color="t.is_active ? 'green' : 'gray'" variant="subtle" size="xs">
                {{ t.is_active ? '启用' : '禁用' }}
              </UBadge>
            </td>
            <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden md:table-cell">
              {{ t.upload_count }} / {{ t.upload_limit ?? '∞' }}
            </td>
            <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden lg:table-cell">
              <template v-if="t.tg_username || t.tg_first_name">
                <UIcon name="heroicons:chat-bubble-left-right" class="w-3.5 h-3.5 inline" />
                {{ t.tg_first_name || '' }}{{ t.tg_username ? ` @${t.tg_username}` : '' }}
              </template>
              <span v-else>--</span>
            </td>
            <td class="py-3 pr-4 text-xs text-stone-500 dark:text-stone-400 hidden lg:table-cell">
              {{ formatDate(t.created_at) }}
            </td>
            <td class="py-3 text-right" @click.stop>
              <div class="flex items-center justify-end gap-1">
                <UButton
                  icon="heroicons:eye"
                  color="gray"
                  variant="ghost"
                  size="sm"
                  title="查看详情"
                  @click="navigateTo(`/admin/tokens/${t.id}`)"
                />
                <UToggle
                  :model-value="t.is_active"
                  size="sm"
                  :disabled="isExpired(t) || updatingId === t.id"
                  @update:model-value="(v) => emit('updateStatus', t, v)"
                />
                <UButton
                  icon="heroicons:trash"
                  color="red"
                  variant="ghost"
                  size="sm"
                  @click="emit('askDelete', t)"
                />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <template #footer>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="text-xs text-stone-500 dark:text-stone-400">
          第 {{ page }} / {{ totalPages }} 页
        </div>
        <UPagination
          :model-value="page"
          :total="total"
          :page-count="pageSize"
          @update:model-value="emit('update:page', $event)"
        />
      </div>
    </template>
  </UCard>
</template>

<script setup lang="ts">
import type { AdminTokenItem } from '~/types/admin'

const props = defineProps<{
  tokens: AdminTokenItem[]
  loading: boolean
  selectedIds: number[]
  isAllSelected: boolean
  isPartialSelected: boolean
  updatingId: number | null
  page: number
  total: number
  pageSize: number
  totalPages: number
}>()

const emit = defineEmits<{
  'toggleSelectAll': []
  'toggleSelect': [id: number]
  'selectToken': [id: number]
  'updateStatus': [token: AdminTokenItem, value: boolean]
  'askDelete': [token: AdminTokenItem]
  'update:page': [page: number]
}>()

const isExpired = (t: AdminTokenItem) => {
  if (typeof t.is_expired === 'boolean') return t.is_expired
  if (!t.expires_at) return false
  return new Date(t.expires_at).getTime() < Date.now()
}

const formatDate = (dateString: string | null | undefined) => {
  if (!dateString) return '--'
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}
</script>
