<template>
  <UModal v-model="isOpen" :ui="{ width: 'max-w-2xl' }">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-bold text-gray-900 dark:text-white">系统公告</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="handleClose"
          />
        </div>
      </template>

      <div v-if="announcement.content" class="prose dark:prose-invert max-w-none" v-html="announcement.content"></div>
      <div v-else class="text-center py-8 text-gray-500">暂无公告</div>

      <template #footer>
        <div class="flex justify-end">
          <UButton color="primary" @click="handleClose">
            我知道了
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const isOpen = ref(false)
const announcement = ref({
  id: 0,
  enabled: false,
  content: ''
})

// 检查是否已经显示过公告
const hasShownAnnouncement = () => {
  if (process.client) {
    // 如果公告ID为0或无效，说明没有公告，不应该显示
    if (!announcement.value.id || announcement.value.id === 0) {
      return true
    }
    const lastAnnouncementId = localStorage.getItem('last_announcement_id')
    return lastAnnouncementId === String(announcement.value.id)
  }
  return false
}

// 标记公告已显示
const markAnnouncementShown = () => {
  if (process.client && announcement.value.id && announcement.value.id !== 0) {
    localStorage.setItem('last_announcement_id', String(announcement.value.id))
  }
}

// 加载公告
const loadAnnouncement = async () => {
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/announcement`)
    if (response.success && response.data) {
      announcement.value = response.data

      // 如果公告已启用、有内容、有有效ID且未显示过，则显示弹窗
      if (response.data.enabled &&
          response.data.content &&
          response.data.id &&
          response.data.id !== 0 &&
          !hasShownAnnouncement()) {
        isOpen.value = true
      }
    }
  } catch (error) {
    console.error('加载公告失败:', error)
  }
}

// 关闭弹窗
const handleClose = () => {
  isOpen.value = false
  markAnnouncementShown()
}

// 页面加载时获取公告
onMounted(() => {
  loadAnnouncement()
})

// 暴露方法供父组件调用
defineExpose({
  show: () => {
    isOpen.value = true
  }
})
</script>
