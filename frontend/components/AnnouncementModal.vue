<template>
  <UModal v-model="isOpen" :ui="{ width: 'sm:max-w-3xl' }">
    <div class="overflow-hidden rounded-3xl border border-amber-200/80 bg-white/95 shadow-[0_22px_55px_-26px_rgba(245,158,11,0.5)] backdrop-blur dark:border-amber-800/50 dark:bg-neutral-900/95">
      <div class="border-b border-amber-100/80 bg-gradient-to-r from-amber-50/80 to-orange-50/60 px-4 py-3 dark:border-amber-800/50 dark:from-amber-900/20 dark:to-orange-900/10 sm:px-6 sm:py-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-600 dark:text-amber-300">Announcement</p>
            <h3 class="mt-1 text-lg font-semibold text-stone-900 dark:text-white sm:text-xl">系统公告</h3>
            <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">该版本公告仅在首次看到时弹出一次</p>
          </div>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            class="shrink-0"
            @click="handleClose"
          />
        </div>
      </div>

      <div class="max-h-[62vh] overflow-y-auto px-4 py-4 sm:px-6 sm:py-5">
        <div
          v-if="announcement.content.trim()"
          class="announcement-modal-content prose max-w-none text-sm dark:prose-invert sm:text-base"
          v-html="announcement.content"
        />
        <div v-else class="flex min-h-[180px] items-center justify-center rounded-2xl border border-dashed border-stone-300 bg-stone-50/70 text-sm text-stone-500 dark:border-neutral-700 dark:bg-neutral-800/60 dark:text-stone-400">
          暂无公告内容
        </div>
      </div>

      <div class="flex flex-col-reverse gap-2 border-t border-stone-200/80 bg-stone-50/70 px-4 py-3 dark:border-neutral-700/80 dark:bg-neutral-800/50 sm:flex-row sm:items-center sm:justify-between sm:px-6 sm:py-4">
        <p class="text-xs text-stone-500 dark:text-stone-400">关闭后将标记为已读，除非公告版本更新</p>
        <UButton color="primary" class="w-full sm:w-auto" @click="handleClose">
          我知道了
        </UButton>
      </div>
    </div>
  </UModal>
</template>

<script setup lang="ts">
import type { AnnouncementState } from '~/types/announcement'

const runtimeConfig = useRuntimeConfig()

const isOpen = ref(false)
const loading = ref(false)

const announcement = ref<AnnouncementState>({
  id: 0,
  enabled: false,
  content: '',
  created_at: null,
  updated_at: null,
})

const hasShownAnnouncement = (): boolean => {
  if (!import.meta.client) return false
  if (!announcement.value.id || announcement.value.id === 0) return true
  const lastAnnouncementId = localStorage.getItem('last_announcement_id')
  return lastAnnouncementId === String(announcement.value.id)
}

const markAnnouncementShown = () => {
  if (!import.meta.client) return
  if (!announcement.value.id || announcement.value.id === 0) return
  localStorage.setItem('last_announcement_id', String(announcement.value.id))
}

const loadAnnouncement = async () => {
  if (loading.value) return
  loading.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/announcement`)
    if (response?.success && response?.data) {
      announcement.value = {
        id: Number(response.data.id) || 0,
        enabled: Boolean(response.data.enabled),
        content: response.data.content || '',
        created_at: response.data.created_at || null,
        updated_at: response.data.updated_at || null,
      }

      if (
        announcement.value.enabled &&
        announcement.value.content.trim() &&
        announcement.value.id > 0 &&
        !hasShownAnnouncement()
      ) {
        isOpen.value = true
      }
    }
  } catch (error) {
    console.error('加载公告失败:', error)
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  isOpen.value = false
  markAnnouncementShown()
}

onMounted(() => {
  loadAnnouncement()
})

defineExpose({
  show: async () => {
    if (!announcement.value.id) await loadAnnouncement()
    if (announcement.value.content.trim()) isOpen.value = true
  },
})
</script>

<style scoped>
.announcement-modal-content {
  color: rgb(63 63 70);
}

.dark .announcement-modal-content {
  color: rgb(228 228 231);
}

.announcement-modal-content:deep(h1),
.announcement-modal-content:deep(h2),
.announcement-modal-content:deep(h3) {
  margin-top: 0;
}

.announcement-modal-content:deep(p),
.announcement-modal-content:deep(li) {
  line-height: 1.75;
}

.announcement-modal-content:deep(ul),
.announcement-modal-content:deep(ol) {
  margin: 0.7rem 0;
  padding-left: 1.2rem;
}

.announcement-modal-content:deep(a) {
  text-decoration: underline;
  text-underline-offset: 0.15em;
}
</style>
