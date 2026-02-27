<template>
  <div class="space-y-4">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-base font-semibold text-stone-900 dark:text-white">控制台总览</h2>
          <UBadge :color="hasToken ? 'green' : 'gray'" variant="subtle" size="xs">
            {{ hasToken ? '已激活 Token' : '未激活 Token' }}
          </UBadge>
        </div>
      </template>

      <div class="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <div class="rounded-xl border border-stone-200 dark:border-stone-700 p-3 bg-stone-50/70 dark:bg-neutral-800/70">
          <p class="text-xs text-stone-500 dark:text-stone-400">Token 数量</p>
          <p class="text-xl font-semibold text-stone-900 dark:text-white mt-1">{{ tokenCount }}</p>
        </div>
        <div class="rounded-xl border border-stone-200 dark:border-stone-700 p-3 bg-stone-50/70 dark:bg-neutral-800/70">
          <p class="text-xs text-stone-500 dark:text-stone-400">累计上传</p>
          <p class="text-xl font-semibold text-stone-900 dark:text-white mt-1">{{ uploadCount }}</p>
        </div>
        <div class="rounded-xl border border-stone-200 dark:border-stone-700 p-3 bg-stone-50/70 dark:bg-neutral-800/70">
          <p class="text-xs text-stone-500 dark:text-stone-400">剩余额度</p>
          <p class="text-xl font-semibold text-stone-900 dark:text-white mt-1">{{ remainingUploads }}</p>
        </div>
        <div class="rounded-xl border border-stone-200 dark:border-stone-700 p-3 bg-stone-50/70 dark:bg-neutral-800/70">
          <p class="text-xs text-stone-500 dark:text-stone-400">TG 状态</p>
          <p class="text-sm font-semibold mt-2" :class="isTgLoggedIn ? 'text-blue-600 dark:text-blue-400' : 'text-stone-700 dark:text-stone-300'">
            {{ isTgLoggedIn ? '已绑定 Telegram' : '未绑定 Telegram' }}
          </p>
        </div>
      </div>

      <div v-if="uploadLimit > 0" class="mt-4">
        <div class="flex justify-between text-xs text-stone-500 dark:text-stone-400 mb-1">
          <span>当前 Token 配额</span>
          <span>{{ uploadCount }} / {{ uploadLimit }}</span>
        </div>
        <div class="h-2 rounded-full bg-stone-200 dark:bg-neutral-700 overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="quotaPercent > 90 ? 'bg-red-500' : quotaPercent > 70 ? 'bg-orange-500' : 'bg-gradient-to-r from-amber-400 to-orange-500'"
            :style="{ width: `${Math.min(100, quotaPercent)}%` }"
          />
        </div>
      </div>
    </UCard>

    <UCard>
      <template #header>
        <h3 class="text-sm font-semibold text-stone-900 dark:text-white">快捷操作</h3>
      </template>
      <div class="grid sm:grid-cols-2 gap-2.5">
        <UButton color="primary" variant="solid" icon="heroicons:plus" @click="emit('generate-token')">
          新建 Token
        </UButton>
        <UButton color="gray" variant="soft" icon="heroicons:clock" @click="emit('open-history')">
          上传历史
        </UButton>
        <UButton color="gray" variant="soft" icon="heroicons:key" @click="emit('navigate', 'tokens')">
          管理 Token
        </UButton>
        <UButton color="gray" variant="soft" icon="heroicons:cloud-arrow-up" @click="emit('navigate', 'uploads')">
          我的上传
        </UButton>
        <UButton color="gray" variant="soft" icon="heroicons:photo" @click="emit('navigate', 'galleries')">
          画集管理
        </UButton>
        <UButton
          v-if="showTgAction"
          color="gray"
          variant="soft"
          icon="heroicons:chat-bubble-left-right"
          @click="emit('navigate', 'tg')"
        >
          TG 绑定
        </UButton>
      </div>

      <div v-if="hasUnboundTokens" class="mt-3 p-3 rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20">
        <p class="text-xs text-blue-700 dark:text-blue-300">检测到未绑定的 Token，可在 TG 绑定中完成关联。</p>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { MeNavKey } from '~/components/MeConsoleShell.vue'

const props = defineProps<{
  isTgLoggedIn: boolean
  hasToken: boolean
  tokenCount: number
  uploadCount: number
  uploadLimit: number
  remainingUploads: number
  hasUnboundTokens: boolean
  showTgAction?: boolean
}>()

const emit = defineEmits<{
  (e: 'navigate', target: MeNavKey): void
  (e: 'generate-token'): void
  (e: 'open-history'): void
}>()

const quotaPercent = computed(() => {
  if (!props.uploadLimit) return 0
  return Math.round((props.uploadCount / props.uploadLimit) * 100)
})
</script>
