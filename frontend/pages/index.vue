<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <!-- Hero 区域 -->
    <div class="text-center pt-4 pb-2">
      <h1 class="text-3xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
        快速、安全的图片托管
      </h1>
      <p class="text-stone-500 mt-2">拖拽、粘贴或点击上传，支持多种格式</p>
    </div>

    <!-- 上传区域 -->
    <HomeUploadZone @uploaded="onUploaded" />

    <!-- 上传结果 -->
    <HomeUploadResults
      v-if="uploadedImages.length > 0"
      :images="uploadedImages"
      @preview="openPreview"
      @clear="uploadedImages = []"
    />

    <!-- 图片预览 -->
    <HomeImagePreview v-model:open="previewOpen" :image="previewingImage" />

    <!-- 上传历史 -->
    <HomeUploadHistory v-model:open="historyOpen" />

    <!-- 历史入口按钮 -->
    <div v-if="tokenStore.hasToken" class="flex justify-center">
      <UButton
        color="primary"
        variant="soft"
        @click="historyOpen = true"
      >
        <template #leading>
          <UIcon name="heroicons:clock" />
        </template>
        查看上传历史
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const tokenStore = useTokenStore()
const authStore = useAuthStore()

// 状态
const uploadedImages = ref<any[]>([])
const previewOpen = ref(false)
const previewingImage = ref<any>(null)
const historyOpen = ref(false)

// 上传完成回调
const onUploaded = (images: any[]) => {
  uploadedImages.value = images
}

// 预览图片
const openPreview = (image: any) => {
  previewingImage.value = image
  previewOpen.value = true
}

// 页面加载时恢复认证状态
onMounted(async () => {
  authStore.restoreAuth()
  await tokenStore.restoreToken()
})
</script>
