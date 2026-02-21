<template>
  <UModal
    v-model="open"
    :ui="{
      width: 'sm:max-w-2xl',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">图片预览</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="open = false"
          />
        </div>
      </template>
      <div v-if="image">
        <img
          :src="image.url"
          :alt="image.filename"
          class="w-full rounded-lg"
        />
        <div class="mt-4 space-y-2">
          <p class="text-sm text-gray-600 dark:text-gray-400">
            <strong>文件名:</strong> {{ image.filename }}
          </p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            <strong>URL:</strong>
            <code class="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
              {{ image.url }}
            </code>
          </p>
        </div>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })

defineProps<{
  image: { url: string; filename: string } | null
}>()
</script>
