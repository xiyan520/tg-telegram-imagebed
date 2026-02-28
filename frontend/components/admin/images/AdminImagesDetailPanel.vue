<template>
  <div class="flex h-full min-h-0 flex-col">
    <header class="shrink-0 flex items-center justify-between border-b border-stone-200 px-4 py-3 dark:border-neutral-700">
      <div class="min-w-0">
        <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">Image Detail</p>
        <h3 class="truncate text-sm font-semibold text-stone-900 dark:text-white">{{ image?.filename || '图片详情' }}</h3>
      </div>
      <div class="ml-3 flex items-center gap-1.5">
        <UButton
          color="gray"
          variant="ghost"
          icon="heroicons:chevron-left"
          :disabled="!image || !hasPrev"
          aria-label="上一张"
          @click="$emit('prev')"
        />
        <UButton
          color="gray"
          variant="ghost"
          icon="heroicons:chevron-right"
          :disabled="!image || !hasNext"
          aria-label="下一张"
          @click="$emit('next')"
        />
        <UButton
          color="gray"
          variant="ghost"
          icon="heroicons:x-mark"
          aria-label="关闭"
          @click="$emit('close')"
        />
      </div>
    </header>

    <div v-if="image" class="min-h-0 flex-1 overflow-y-auto">
      <div class="grid gap-4 p-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(19rem,1fr)]">
        <section class="space-y-3">
          <div class="rounded-2xl border border-stone-200/80 bg-gradient-to-br from-stone-100 via-white to-stone-50 p-3 dark:border-neutral-700/80 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800">
            <div class="overflow-hidden rounded-xl bg-white/85 p-2 shadow-sm dark:bg-neutral-950/70">
              <img
                :src="image.url"
                :alt="image.filename"
                loading="lazy"
                decoding="async"
                class="mx-auto max-h-[56vh] w-full rounded-lg object-contain"
                @error="onImageError"
              >
            </div>
          </div>

          <div class="rounded-xl border border-stone-200/80 bg-white/70 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
            <p class="text-xs text-stone-500 dark:text-stone-400">链接</p>
            <code class="mt-1 block break-all rounded-lg bg-stone-100 px-2.5 py-2 text-xs text-stone-700 dark:bg-neutral-800 dark:text-stone-200">
              {{ image.url }}
            </code>
          </div>
        </section>

        <section class="space-y-3">
          <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
            <p class="text-xs font-medium text-stone-500 dark:text-stone-400">概览</p>
            <div class="mt-2 grid grid-cols-1 gap-2 text-sm">
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">文件名</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ image.filename || '--' }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">上传用户</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ image.username || 'unknown' }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">来源</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ sourceLabel(image.source) }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">上传时间</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ formatDate(image.uploadTime || image.created_at) }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">文件大小</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ formatSize(image.size ?? image.file_size) }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">缓存状态</span>
                <UBadge :color="image.cached ? 'green' : 'gray'" size="xs" variant="subtle">
                  {{ image.cached ? '已缓存' : '未缓存' }}
                </UBadge>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
            <p class="text-xs font-medium text-stone-500 dark:text-stone-400">访问统计</p>
            <div class="mt-2 grid grid-cols-3 gap-2">
              <div class="rounded-lg bg-amber-50 px-2 py-1.5 text-center dark:bg-amber-900/25">
                <p class="text-[11px] text-stone-500 dark:text-stone-400">总访问</p>
                <p class="text-sm font-semibold text-amber-700 dark:text-amber-300">{{ formatCount(image.access_count) }}</p>
              </div>
              <div class="rounded-lg bg-stone-100 px-2 py-1.5 text-center dark:bg-neutral-800">
                <p class="text-[11px] text-stone-500 dark:text-stone-400">CDN</p>
                <p class="text-sm font-semibold text-stone-700 dark:text-stone-200">{{ formatCount(image.cdn_hit_count) }}</p>
              </div>
              <div class="rounded-lg bg-stone-100 px-2 py-1.5 text-center dark:bg-neutral-800">
                <p class="text-[11px] text-stone-500 dark:text-stone-400">直连</p>
                <p class="text-sm font-semibold text-stone-700 dark:text-stone-200">{{ formatCount(image.direct_hit_count) }}</p>
              </div>
            </div>
            <div class="mt-2 rounded-lg bg-stone-100/70 px-2.5 py-2 text-xs text-stone-600 dark:bg-neutral-800/80 dark:text-stone-300">
              最近访问：{{ formatDate(image.last_accessed) }}
            </div>
          </div>

          <div class="rounded-xl border border-stone-200/80 bg-white/75 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/70">
            <p class="text-xs font-medium text-stone-500 dark:text-stone-400">技术信息</p>
            <div class="mt-2 grid grid-cols-1 gap-2 text-sm">
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">MIME Type</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ image.mime_type || '--' }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">文件 ID</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ image.file_id || '--' }}</span>
              </div>
              <div class="flex items-center justify-between gap-3 rounded-lg bg-stone-100/70 px-2.5 py-2 dark:bg-neutral-800/80">
                <span class="text-xs text-stone-500 dark:text-stone-400">加密 ID</span>
                <span class="break-all text-right text-sm font-medium text-stone-800 dark:text-stone-100">{{ image.encrypted_id || '--' }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <div v-else class="flex flex-1 items-center justify-center px-6 py-16">
      <div class="text-center">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-stone-100 dark:bg-neutral-800">
          <UIcon name="heroicons:photo" class="h-7 w-7 text-stone-400 dark:text-stone-500" />
        </div>
        <p class="mt-3 text-sm font-medium text-stone-700 dark:text-stone-200">未选择图片</p>
        <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">请先在列表中选择一张图片查看详情</p>
      </div>
    </div>

    <footer class="shrink-0 border-t border-stone-200 bg-white/95 px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] dark:border-neutral-700 dark:bg-neutral-900/95 sm:px-4">
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <UButton
          color="blue"
          variant="soft"
          icon="heroicons:link"
          :disabled="!image"
          block
          @click="$emit('copy')"
        >
          复制链接
        </UButton>
        <UButton
          color="gray"
          variant="soft"
          icon="heroicons:arrow-down-tray"
          :disabled="!image"
          block
          @click="$emit('download')"
        >
          下载图片
        </UButton>
        <UButton
          color="red"
          variant="soft"
          icon="heroicons:trash"
          :disabled="!image"
          block
          @click="$emit('delete')"
        >
          删除图片
        </UButton>
        <UButton color="gray" variant="ghost" icon="heroicons:x-mark" block @click="$emit('close')">
          关闭
        </UButton>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { AdminImageItem } from '~/types/api'

withDefaults(defineProps<{
  image: AdminImageItem | null
  hasPrev?: boolean
  hasNext?: boolean
}>(), {
  hasPrev: false,
  hasNext: false,
})

defineEmits<{
  close: []
  copy: []
  prev: []
  next: []
  download: []
  delete: []
}>()

const formatSize = (size: string | number | null | undefined) => {
  if (size === null || size === undefined || size === '') return '--'
  if (typeof size === 'string') {
    if (/[a-zA-Z]/.test(size)) return size
    const parsed = Number(size)
    if (!Number.isFinite(parsed)) return size
    return `${(parsed / (1024 * 1024)).toFixed(2)} MB`
  }
  if (!Number.isFinite(size)) return '--'
  return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

const formatCount = (value: number | null | undefined) => {
  if (value === null || value === undefined || !Number.isFinite(value)) return '0'
  return new Intl.NumberFormat('zh-CN').format(value)
}

const formatDate = (value?: string | null) => {
  const raw = String(value || '').trim()
  if (!raw) return '--'
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return raw
  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const sourceLabel = (source?: string) => {
  const value = String(source || '').toLowerCase()
  if (value.includes('token')) return 'Token 上传'
  if (value === 'telegram_bot') return '机器人上传'
  if (value === 'group') return '群组上传'
  if (value === 'admin_upload') return '管理员上传'
  if (value === 'guest') return '匿名上传'
  return value || '未知来源'
}

const onImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="640" height="420"%3E%3Crect fill="%23ddd" width="640" height="420"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18"%3E加载失败%3C/text%3E%3C/svg%3E'
}
</script>
