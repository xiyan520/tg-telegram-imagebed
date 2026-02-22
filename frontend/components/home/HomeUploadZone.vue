<template>
  <div class="flex justify-center items-center min-h-[60vh]">
    <UCard class="upload-card shadow-2xl w-full max-w-2xl">
      <div
        class="upload-area relative rounded-2xl p-12 text-center transition-all cursor-pointer"
        :class="[
          isDragging ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20' : '',
          uploading ? 'pointer-events-none opacity-50' : '',
        ]"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          :accept="acceptAttr"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />

        <!-- 上传内容 -->
        <div v-if="!uploading" class="upload-content">
          <div class="folder-container">
            <div class="folder">
              <div class="front-side">
                <div class="tip"></div>
                <div class="cover"></div>
              </div>
              <div class="back-side cover"></div>
            </div>
          </div>
          <h3 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">
            点击或拖拽上传图片
          </h3>
          <p class="text-stone-600 dark:text-stone-400 mb-2">
            {{ formatHint }}
          </p>
          <p class="paste-hint text-sm text-stone-500 dark:text-stone-400">
            💡 你也可以直接 <kbd class="px-2 py-1 bg-stone-200 dark:bg-stone-700 rounded text-xs">Ctrl+V</kbd> 粘贴剪贴板中的图片
          </p>
        </div>
        <!-- 上传进度 -->
        <div v-else class="space-y-4">
          <div class="flex justify-center">
            <div class="w-16 h-16 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div>
            <p class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ uploadProgress.label }}
            </p>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {{ uploadProgress.percent }}%
            </p>
          </div>
          <UProgress :value="uploadProgress.percent" color="primary" />
          <UButton color="red" variant="soft" @click="cancelUpload">
            取消上传
          </UButton>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const toast = useNotification()
const { uploadFiles, abortUpload } = useUpload()
const { triggerStatsRefresh } = useStatsRefresh()
const runtimeConfig = useRuntimeConfig()

const emit = defineEmits<{
  uploaded: [images: any[]]
}>()

const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref({ label: '上传中...', percent: 0 })
const fileInput = ref<HTMLInputElement>()

// 动态允许的文件后缀
const allowedExtensions = ref('jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico')
const maxFileSizeMb = ref(20)

// 后缀 → MIME 映射（用于 accept 属性）
const extMimeMap: Record<string, string> = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
  gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp',
  avif: 'image/avif', tiff: 'image/tiff', tif: 'image/tiff',
  ico: 'image/x-icon', heic: 'image/heic', heif: 'image/heif',
}

// 动态 accept 属性
const acceptAttr = computed(() => {
  const exts = allowedExtensions.value.split(',').map(e => e.trim().toLowerCase()).filter(Boolean)
  const mimes = new Set<string>()
  for (const ext of exts) {
    if (extMimeMap[ext]) {
      mimes.add(extMimeMap[ext])
    } else {
      mimes.add(`.${ext}`)
    }
  }
  return Array.from(mimes).join(',')
})

// 动态提示文字
const formatHint = computed(() => {
  const exts = allowedExtensions.value.split(',').map(e => e.trim().toUpperCase()).filter(Boolean)
  // 去重（JPG/JPEG 合并显示）
  const unique = [...new Set(exts)]
  const display = unique.length > 6 ? unique.slice(0, 6).join('、') + ' 等' : unique.join('、')
  return `支持 ${display} 格式，最大 ${maxFileSizeMb.value}MB`
})

// 允许的后缀集合（用于校验）
const allowedExtSet = computed(() => {
  return new Set(allowedExtensions.value.split(',').map(e => e.trim().toLowerCase()).filter(Boolean))
})

// 从公共设置 API 获取动态配置
const loadPublicSettings = async () => {
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/public/settings`)
    if (response.success && response.data) {
      if (response.data.allowed_extensions) {
        allowedExtensions.value = response.data.allowed_extensions
      }
      if (response.data.max_file_size_mb) {
        maxFileSizeMb.value = response.data.max_file_size_mb
      }
    }
  } catch {
    // 加载失败使用默认值
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    handleFiles(Array.from(target.files))
  }
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files) {
    handleFiles(Array.from(event.dataTransfer.files))
  }
}

const handleFiles = async (files: File[]) => {
  if (files.length === 0) return

  const maxSize = maxFileSizeMb.value * 1024 * 1024

  // 验证文件
  const validFiles = files.filter((file) => {
    // 检查 MIME 前缀或文件后缀
    const ext = file.name.includes('.') ? file.name.split('.').pop()?.toLowerCase() : ''
    const isAllowed = file.type.startsWith('image/') || (ext && allowedExtSet.value.has(ext))
    if (!isAllowed) {
      toast.error('错误', `${file.name} 不是允许的图片格式`)
      return false
    }
    if (file.size > maxSize) {
      toast.error('错误', `${file.name} 超过 ${maxFileSizeMb.value}MB`)
      return false
    }
    return true
  })
  if (validFiles.length === 0) return

  uploading.value = true
  uploadProgress.value = { label: '上传中...', percent: 0 }

  try {
    const results = await uploadFiles(validFiles, (p) => {
      uploadProgress.value = p
    })
    uploadProgress.value = { label: '完成', percent: 100 }
    toast.success('上传成功', `成功上传 ${results.length} 张图片`)
    triggerStatsRefresh()
    emit('uploaded', results)
  } catch (error: any) {
    toast.error('上传失败', error.data?.error || error.message || '未知错误')
  } finally {
    uploading.value = false
  }
}

const cancelUpload = () => {
  abortUpload()
  uploading.value = false
  uploadProgress.value = { label: '上传中...', percent: 0 }
}

// 全局粘贴事件监听
const handlePaste = (event: ClipboardEvent) => {
  const items = event.clipboardData?.items
  if (!items) return
  const files: File[] = []
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      const file = items[i].getAsFile()
      if (file) files.push(file)
    }
  }
  if (files.length > 0) {
    event.preventDefault()
    handleFiles(files)
  }
}

onMounted(() => {
  window.addEventListener('paste', handlePaste)
  loadPublicSettings()
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
})

defineExpose({ handleFiles })
</script>

<style scoped>
/* 上传卡片增强样式 */
.upload-card {
  border-radius: 1.5rem;
  overflow: hidden;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 10px 10px -5px rgba(0, 0, 0, 0.04),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
  border: 2px solid rgba(245, 158, 11, 0.1);
  transition: all 0.3s ease;
}
.upload-card:hover {
  box-shadow:
    0 25px 50px -12px rgba(245, 158, 11, 0.25),
    0 0 0 1px rgba(245, 158, 11, 0.1);
  transform: translateY(-2px);
}
:global(.dark) .upload-card {
  background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
  border: 2px solid rgba(245, 158, 11, 0.2);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.5),
    0 10px 10px -5px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(245, 158, 11, 0.1);
}
:global(.dark) .upload-card:hover {
  box-shadow:
    0 25px 50px -12px rgba(245, 158, 11, 0.4),
    0 0 0 1px rgba(245, 158, 11, 0.2);
}

/* 上传区域 */
.upload-area {
  position: relative;
  min-height: 300px;
  background: linear-gradient(135deg,
    rgba(251, 191, 36, 0.03) 0%,
    rgba(245, 158, 11, 0.05) 50%,
    rgba(251, 191, 36, 0.03) 100%);
  border: 2px dashed rgba(245, 158, 11, 0.2);
  border-radius: 1.25rem;
  transition: all 0.3s ease;
}
.upload-area:hover {
  background: linear-gradient(135deg,
    rgba(251, 191, 36, 0.08) 0%,
    rgba(245, 158, 11, 0.1) 50%,
    rgba(251, 191, 36, 0.08) 100%);
  border-color: rgba(245, 158, 11, 0.4);
  transform: scale(1.01);
}
:global(.dark) .upload-area {
  background: linear-gradient(135deg,
    rgba(217, 119, 6, 0.05) 0%,
    rgba(234, 88, 12, 0.08) 50%,
    rgba(217, 119, 6, 0.05) 100%);
  border-color: rgba(245, 158, 11, 0.3);
}
:global(.dark) .upload-area:hover {
  background: linear-gradient(135deg,
    rgba(217, 119, 6, 0.1) 0%,
    rgba(234, 88, 12, 0.15) 50%,
    rgba(217, 119, 6, 0.1) 100%);
  border-color: rgba(245, 158, 11, 0.5);
}

/* 上传内容布局 */
.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

/* 文件夹动画 */
.folder-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 1rem;
}
.folder {
  width: 150px;
  height: 120px;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
}
.upload-area:hover .folder {
  transform: translateY(-10px);
}
.folder .front-side,
.folder .back-side {
  position: absolute;
  transition: all 0.3s ease;
}
.folder .front-side {
  width: 100%;
  height: 100%;
  z-index: 2;
}
.folder .tip {
  position: absolute;
  top: 0;
  left: 0;
  width: 60px;
  height: 15px;
  background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  border-radius: 8px 8px 0 0;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}
.folder .cover {
  position: absolute;
  top: 15px;
  left: 0;
  width: 100%;
  height: calc(100% - 15px);
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
}
.folder .back-side {
  width: 100%;
  height: 90%;
  bottom: 0;
  left: 0;
  background: linear-gradient(135deg, #fcd34d 0%, #fbbf24 100%);
  border-radius: 8px;
  opacity: 0.8;
  z-index: 1;
}
.upload-area:hover .folder .front-side {
  transform: rotateX(-10deg) translateY(-5px);
}
.upload-area:hover .folder .back-side {
  transform: rotateX(-5deg) translateY(5px);
}
.upload-area:hover .folder .tip {
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.5);
}
.upload-area:hover .folder .cover {
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.6);
}

/* 暗色模式文件夹 */
:global(.dark) .folder .tip {
  background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
}
:global(.dark) .folder .cover {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}
:global(.dark) .folder .back-side {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
}

/* 粘贴提示 */
.paste-hint {
  margin-top: 0.5rem;
}
.paste-hint kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
}
</style>
