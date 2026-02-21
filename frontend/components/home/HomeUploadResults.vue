<template>
  <UCard class="shadow-xl">
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-xl font-bold text-gray-900 dark:text-white">
          上传成功 ({{ images.length }}张)
        </h3>
        <UButton color="gray" variant="ghost" @click="emit('clear')">
          清空
        </UButton>
      </div>
    </template>

    <!-- 缩略图网格 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div
        v-for="(image, index) in images"
        :key="index"
        class="relative group aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
      >
        <img
          :src="image.url"
          :alt="image.filename"
          class="w-full h-full object-cover"
        />
        <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <UButton
            icon="heroicons:eye"
            color="white"
            size="sm"
            @click="emit('preview', image)"
          />
          <UButton
            icon="heroicons:clipboard-document"
            color="white"
            size="sm"
            @click="copyUrl(image.url)"
          />
        </div>
      </div>
    </div>

    <!-- 链接格式标签页 -->
    <div class="mt-6">
      <div class="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700">
        <button
          v-for="(tab, index) in formatTabs"
          :key="index"
          @click="selectedFormat = index"
          :class="[
            'px-4 py-2 font-medium text-sm transition-colors',
            selectedFormat === index
              ? 'text-amber-600 dark:text-amber-400 border-b-2 border-amber-600 dark:border-amber-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="space-y-4 py-4">
        <UTextarea
          :model-value="getFormattedLinks(formatTabs[selectedFormat].value)"
          readonly
          :rows="6"
          class="font-mono text-sm"
        />
        <UButton
          icon="heroicons:clipboard-document"
          color="primary"
          block
          @click="copyAllLinks(formatTabs[selectedFormat].value)"
        >
          复制全部链接
        </UButton>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
const { copy: clipboardCopy } = useClipboardCopy()

const props = defineProps<{
  images: any[]
}>()

const emit = defineEmits<{
  preview: [image: any]
  clear: []
}>()

const selectedFormat = ref(0)

const formatTabs = [
  { label: 'URL', value: 'url' },
  { label: 'Markdown', value: 'markdown' },
  { label: 'HTML', value: 'html' },
  { label: 'BBCode', value: 'bbcode' },
]

const getFormattedLinks = (format: string) => {
  return props.images
    .map((img) => {
      switch (format) {
        case 'url': return img.url
        case 'markdown': return `![${img.filename}](${img.url})`
        case 'html': return `<img src="${img.url}" alt="${img.filename}" />`
        case 'bbcode': return `[img]${img.url}[/img]`
        default: return img.url
      }
    })
    .join('\n')
}

const copyUrl = (url: string) => {
  clipboardCopy(url, '已复制')
}

const copyAllLinks = (format: string) => {
  clipboardCopy(getFormattedLinks(format), '已复制全部链接')
}
</script>
