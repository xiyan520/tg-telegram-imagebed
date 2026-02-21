<template>
  <UModal v-model="open">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">分享管理</h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="open = false" />
        </div>
      </template>

      <div class="space-y-4">
        <!-- 分享状态 -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <UIcon
              :name="gallery?.share_enabled ? 'heroicons:link' : 'heroicons:link-slash'"
              class="w-5 h-5"
              :class="gallery?.share_enabled ? 'text-green-500' : 'text-gray-400'"
            />
            <span class="font-medium">
              {{ gallery?.share_enabled ? '分享已开启' : '分享未开启' }}
            </span>
          </div>
          <UButton
            :color="gallery?.share_enabled ? 'red' : 'green'"
            variant="soft"
            size="sm"
            :loading="toggling"
            @click="toggleShare"
          >
            {{ gallery?.share_enabled ? '关闭分享' : '开启分享' }}
          </UButton>
        </div>

        <!-- 分享链接 -->
        <div v-if="gallery?.share_enabled && shareUrl" class="space-y-2">
          <label class="text-sm text-gray-500 dark:text-gray-400">分享链接</label>
          <div class="flex gap-2">
            <UInput :model-value="shareUrl" readonly class="flex-1" />
            <UButton icon="heroicons:clipboard-document" color="gray" @click="copyShareUrl" />
          </div>
        </div>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import type { Gallery } from '~/composables/useGalleryApi'

const props = defineProps<{
  gallery: Gallery | null
}>()

const open = defineModel<boolean>({ default: false })
const emit = defineEmits<{ (e: 'updated'): void }>()

const toast = useLightToast()
const { copy } = useClipboardCopy()
const galleryApi = useGalleryApi()
const toggling = ref(false)
const shareUrl = ref('')

watch(() => props.gallery, (g) => {
  shareUrl.value = g?.share_url || ''
}, { immediate: true })

const toggleShare = async () => {
  if (!props.gallery) return
  toggling.value = true
  try {
    if (props.gallery.share_enabled) {
      await galleryApi.disableShare(props.gallery.id)
      shareUrl.value = ''
      toast.success('分享已关闭')
    } else {
      const result = await galleryApi.enableShare(props.gallery.id)
      shareUrl.value = result.share_url
      toast.success('分享已开启')
    }
    emit('updated')
  } catch (e: any) {
    toast.error('操作失败', e.message)
  } finally {
    toggling.value = false
  }
}

const copyShareUrl = () => {
  copy(shareUrl.value, '链接已复制')
}
</script>
