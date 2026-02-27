<template>
  <div class="flex min-h-[60vh] items-center justify-center">
    <UCard class="upload-card w-full max-w-2xl shadow-2xl">
      <div
        class="upload-area relative cursor-pointer rounded-2xl p-6 text-center sm:p-12"
        :class="[phaseClass, isInteractiveLocked ? 'pointer-events-none' : '']"
        @dragover.prevent="handleDragOver"
        @dragleave.prevent="handleDragLeave"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <div class="upload-area-glow" aria-hidden="true" />
        <div class="upload-area-focus" aria-hidden="true" />

        <input
          ref="fileInput"
          type="file"
          :accept="acceptAttr"
          multiple
          class="hidden"
          @change="handleFileSelect"
        >

        <Transition name="phase-fade" mode="out-in">
          <div v-if="uploadPhase === 'uploading'" key="uploading" class="phase-panel space-y-4">
            <div class="flex justify-center">
              <div class="progress-ring" :class="{ 'progress-ring-pulse': progressPulse }" :style="progressRingStyle">
                <div class="progress-ring-inner">
                  <UIcon name="heroicons:cloud-arrow-up" class="h-6 w-6 text-amber-600 dark:text-amber-300" />
                </div>
              </div>
            </div>
            <div>
              <p class="text-lg font-semibold text-stone-900 dark:text-white">
                {{ uploadProgress.label || '上传中...' }}
              </p>
              <p class="text-sm text-stone-600 dark:text-stone-400">
                {{ uploadProgress.percent }}%
              </p>
            </div>
            <UProgress :value="uploadProgress.percent" color="primary" />
            <UButton color="red" variant="soft" class="w-full sm:w-auto" @click.stop="cancelUpload">
              取消上传
            </UButton>
          </div>

          <div v-else-if="uploadPhase === 'success'" key="success" class="phase-panel space-y-4">
            <div class="flex justify-center">
              <div class="success-ring">
                <UIcon name="heroicons:check-circle" class="h-9 w-9 text-emerald-500 dark:text-emerald-300" />
              </div>
            </div>
            <div>
              <p class="text-lg font-semibold text-stone-900 dark:text-white">上传完成</p>
              <p class="text-sm text-stone-600 dark:text-stone-400">
                成功上传 {{ lastUploadCount }} 张图片
              </p>
            </div>
          </div>

          <div v-else-if="uploadPhase === 'error'" key="error" class="phase-panel space-y-3">
            <div class="flex justify-center">
              <div class="error-ring">
                <UIcon name="heroicons:exclamation-triangle" class="h-8 w-8 text-rose-500 dark:text-rose-300" />
              </div>
            </div>
            <div>
              <p class="text-lg font-semibold text-stone-900 dark:text-white">上传失败</p>
              <p class="text-sm text-stone-600 dark:text-stone-400">
                {{ lastErrorMessage || '网络异常，请稍后重试' }}
              </p>
            </div>
          </div>

          <div v-else :key="uploadPhase === 'dragging' ? 'dragging' : 'idle'" class="upload-content">
            <div class="folder-container">
              <div class="folder">
                <div class="front-side">
                  <div class="tip" />
                  <div class="cover" />
                </div>
                <div class="back-side cover" />
              </div>
            </div>
            <h3 class="mb-2 text-2xl font-bold text-stone-900 dark:text-white">
              {{ uploadPhase === 'dragging' ? '松手即可上传图片' : '点击或拖拽上传图片' }}
            </h3>
            <p class="mb-2 text-stone-600 dark:text-stone-400">
              {{ uploadPhase === 'dragging' ? '文件已就绪，松开即可开始上传' : formatHint }}
            </p>
            <p class="mb-2 text-sm text-stone-500 dark:text-stone-400">
              💡 支持拖拽文件夹上传，也可以
              <kbd class="rounded bg-stone-200 px-2 py-1 text-xs dark:bg-stone-700">Ctrl+V</kbd>
              粘贴图片
            </p>
          </div>
        </Transition>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { CSSProperties } from 'vue'
import type { UploadResult } from '~/types/upload'

type UploadPhase = 'idle' | 'dragging' | 'uploading' | 'success' | 'error'

const toast = useNotification()
const { uploadFiles, abortUpload } = useUpload()
const { triggerStatsRefresh } = useStatsRefresh()
const runtimeConfig = useRuntimeConfig()

const emit = defineEmits<{
  uploaded: [images: UploadResult[]]
}>()

const isDragging = ref(false)
const uploading = ref(false)
const uploadPhase = ref<UploadPhase>('idle')
const uploadProgress = ref({ label: '上传中...', percent: 0 })
const fileInput = ref<HTMLInputElement>()
const lastUploadCount = ref(0)
const lastErrorMessage = ref('')
const progressPulse = ref(false)
const pulseTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const phaseTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const milestoneThresholds = [25, 50, 75, 100]
const nextMilestoneIndex = ref(0)

const isInteractiveLocked = computed(() => uploading.value || uploadPhase.value === 'success')
const phaseClass = computed(() => `upload-phase-${uploadPhase.value}`)
const progressRingStyle = computed(() => ({
  '--progress': `${uploadProgress.value.percent}%`,
} as CSSProperties))

// 动态允许的文件后缀
const allowedExtensions = ref('jpg,jpeg,png,gif,webp,bmp,avif,tiff,tif,ico')
const maxFileSizeMb = ref(20)

// 后缀 -> MIME 映射（用于 accept 属性）
const extMimeMap: Record<string, string> = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
  gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp',
  avif: 'image/avif', tiff: 'image/tiff', tif: 'image/tiff',
  ico: 'image/x-icon', heic: 'image/heic', heif: 'image/heif',
}

const clearPhaseTimer = () => {
  if (!phaseTimer.value) return
  clearTimeout(phaseTimer.value)
  phaseTimer.value = null
}

const clearPulseTimer = () => {
  if (!pulseTimer.value) return
  clearTimeout(pulseTimer.value)
  pulseTimer.value = null
}

const scheduleIdle = (delayMs: number) => {
  clearPhaseTimer()
  phaseTimer.value = setTimeout(() => {
    if (!uploading.value) uploadPhase.value = 'idle'
  }, delayMs)
}

const triggerProgressPulse = () => {
  progressPulse.value = true
  clearPulseTimer()
  pulseTimer.value = setTimeout(() => {
    progressPulse.value = false
  }, 260)
}

// 动态 accept 属性
const acceptAttr = computed(() => {
  const exts = allowedExtensions.value.split(',').map((e) => e.trim().toLowerCase()).filter(Boolean)
  const mimes = new Set<string>()
  for (const ext of exts) {
    if (extMimeMap[ext]) mimes.add(extMimeMap[ext])
    else mimes.add(`.${ext}`)
  }
  return Array.from(mimes).join(',')
})

// 动态提示文字
const formatHint = computed(() => {
  const exts = allowedExtensions.value.split(',').map((e) => e.trim().toUpperCase()).filter(Boolean)
  const unique = [...new Set(exts)]
  const display = unique.length > 6 ? `${unique.slice(0, 6).join('、')} 等` : unique.join('、')
  return `支持 ${display} 格式，最大 ${maxFileSizeMb.value}MB`
})

// 允许的后缀集合（用于校验）
const allowedExtSet = computed(() => {
  return new Set(allowedExtensions.value.split(',').map((e) => e.trim().toLowerCase()).filter(Boolean))
})

const resetToIdle = () => {
  uploading.value = false
  isDragging.value = false
  uploadPhase.value = 'idle'
  uploadProgress.value = { label: '上传中...', percent: 0 }
  nextMilestoneIndex.value = 0
  progressPulse.value = false
  clearPhaseTimer()
}

// 从公共设置 API 获取动态配置
const loadPublicSettings = async () => {
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/public/settings`)
    if (response.success && response.data) {
      if (response.data.allowed_extensions) allowedExtensions.value = response.data.allowed_extensions
      if (response.data.max_file_size_mb) maxFileSizeMb.value = response.data.max_file_size_mb
    }
  } catch {
    // 加载失败使用默认值
  }
}

const triggerFileInput = () => {
  if (isInteractiveLocked.value) return
  fileInput.value?.click()
}

const handleDragOver = () => {
  if (isInteractiveLocked.value) return
  isDragging.value = true
  uploadPhase.value = 'dragging'
}

const handleDragLeave = () => {
  if (uploading.value) return
  isDragging.value = false
  if (uploadPhase.value === 'dragging') uploadPhase.value = 'idle'
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    void handleFiles(Array.from(target.files))
  }
  target.value = ''
}

const handleDrop = async (event: DragEvent) => {
  if (isInteractiveLocked.value) return
  isDragging.value = false
  if (!event.dataTransfer) {
    uploadPhase.value = 'idle'
    return
  }

  const items = event.dataTransfer.items
  if (items && items.length > 0 && typeof items[0].webkitGetAsEntry === 'function') {
    const allFiles: File[] = []
    const entries: FileSystemEntry[] = []
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry()
      if (entry) entries.push(entry)
    }
    for (const entry of entries) {
      const files = await readEntryFiles(entry)
      allFiles.push(...files)
    }
    if (allFiles.length > 0) {
      void handleFiles(allFiles)
      return
    }
  } else if (event.dataTransfer.files) {
    const dropped = Array.from(event.dataTransfer.files)
    if (dropped.length > 0) {
      void handleFiles(dropped)
      return
    }
  }

  uploadPhase.value = 'idle'
}

/** 递归读取 FileSystemEntry 中的所有文件 */
const readEntryFiles = (entry: FileSystemEntry): Promise<File[]> => {
  return new Promise((resolve) => {
    if (entry.isFile) {
      ;(entry as FileSystemFileEntry).file(
        (file) => resolve([file]),
        () => resolve([]),
      )
      return
    }
    if (entry.isDirectory) {
      const reader = (entry as FileSystemDirectoryEntry).createReader()
      const allFiles: File[] = []
      const readBatch = () => {
        reader.readEntries(async (entries) => {
          if (entries.length === 0) {
            resolve(allFiles)
            return
          }
          for (const child of entries) {
            const files = await readEntryFiles(child)
            allFiles.push(...files)
          }
          readBatch()
        }, () => resolve(allFiles))
      }
      readBatch()
      return
    }
    resolve([])
  })
}

const handleFiles = async (files: File[]) => {
  if (files.length === 0 || uploading.value) return

  const maxSize = maxFileSizeMb.value * 1024 * 1024
  lastErrorMessage.value = ''
  clearPhaseTimer()

  const validFiles = files.filter((file) => {
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
  uploadPhase.value = 'uploading'
  nextMilestoneIndex.value = 0
  uploadProgress.value = { label: `准备上传 ${validFiles.length} 张图片...`, percent: 0 }

  try {
    const results = await uploadFiles(validFiles, (p) => {
      uploadProgress.value = p
    })
    uploadProgress.value = { label: '上传完成', percent: 100 }
    lastUploadCount.value = results.length
    toast.success('上传成功', `成功上传 ${results.length} 张图片`)
    triggerStatsRefresh()
    emit('uploaded', results)
    uploading.value = false
    uploadPhase.value = 'success'
    scheduleIdle(720)
  } catch (error: any) {
    const message = error?.data?.error || error?.message || '未知错误'
    uploading.value = false
    if (message === '上传已取消') {
      resetToIdle()
      return
    }
    lastErrorMessage.value = message
    toast.error('上传失败', message)
    uploadPhase.value = 'error'
    scheduleIdle(1000)
  }
}

const cancelUpload = () => {
  abortUpload()
  resetToIdle()
}

// 全局粘贴事件监听
const handlePaste = (event: ClipboardEvent) => {
  if (isInteractiveLocked.value) return
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
    void handleFiles(files)
  }
}

watch(
  () => uploadProgress.value.percent,
  (percent) => {
    if (uploadPhase.value !== 'uploading') return
    while (
      nextMilestoneIndex.value < milestoneThresholds.length &&
      percent >= milestoneThresholds[nextMilestoneIndex.value]
    ) {
      triggerProgressPulse()
      nextMilestoneIndex.value += 1
    }
  },
)

onMounted(() => {
  window.addEventListener('paste', handlePaste)
  void loadPublicSettings()
})

onUnmounted(() => {
  window.removeEventListener('paste', handlePaste)
  clearPhaseTimer()
  clearPulseTimer()
})

defineExpose({ handleFiles })
</script>

<style scoped>
.upload-card {
  overflow: hidden;
  border: 2px solid rgba(245, 158, 11, 0.12);
  border-radius: 1.5rem;
  background: linear-gradient(145deg, #fff 0%, #fafaf9 100%);
  box-shadow:
    0 20px 30px -20px rgba(15, 23, 42, 0.25),
    0 0 0 1px rgba(245, 158, 11, 0.08);
  transition: transform 220ms ease, box-shadow 220ms ease;
}

.upload-card:hover {
  transform: translateY(-1px);
  box-shadow:
    0 24px 36px -18px rgba(245, 158, 11, 0.28),
    0 0 0 1px rgba(245, 158, 11, 0.14);
}

:global(.dark) .upload-card {
  border-color: rgba(245, 158, 11, 0.2);
  background: linear-gradient(145deg, #1c1917 0%, #111827 100%);
  box-shadow:
    0 20px 34px -22px rgba(0, 0, 0, 0.6),
    0 0 0 1px rgba(245, 158, 11, 0.12);
}

.upload-area {
  position: relative;
  overflow: hidden;
  min-height: 320px;
  border: 2px dashed rgba(245, 158, 11, 0.28);
  background: linear-gradient(145deg, rgba(251, 191, 36, 0.06) 0%, rgba(245, 158, 11, 0.1) 45%, rgba(251, 191, 36, 0.05) 100%);
  transition: transform 220ms ease, border-color 220ms ease, background 260ms ease, box-shadow 260ms ease;
}

.upload-area-glow {
  position: absolute;
  inset: -30%;
  z-index: 0;
  background: radial-gradient(circle at 50% 40%, rgba(251, 191, 36, 0.34), rgba(251, 191, 36, 0));
  opacity: 0.5;
  animation: idle-breathe 3.2s ease-in-out infinite;
  pointer-events: none;
}

.upload-area-focus {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 58%;
  aspect-ratio: 1 / 1;
  z-index: 0;
  transform: translate(-50%, -50%) scale(0.84);
  border-radius: 9999px;
  background: radial-gradient(circle, rgba(251, 191, 36, 0.35) 0%, rgba(251, 191, 36, 0) 66%);
  opacity: 0;
  transition: transform 220ms ease, opacity 220ms ease;
  pointer-events: none;
}

.phase-panel,
.upload-content {
  position: relative;
  z-index: 1;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.folder-container {
  display: flex;
  margin-bottom: 0.8rem;
  justify-content: center;
  align-items: center;
}

.folder {
  position: relative;
  width: 150px;
  height: 120px;
  animation: idle-float 3.1s ease-in-out infinite;
  transition: transform 220ms ease;
}

.folder .front-side,
.folder .back-side {
  position: absolute;
  transition: transform 220ms ease, box-shadow 220ms ease;
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
  border-radius: 8px 8px 0 0;
  background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}

.folder .cover {
  position: absolute;
  top: 15px;
  left: 0;
  width: 100%;
  height: calc(100% - 15px);
  border-radius: 8px;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
}

.folder .back-side {
  bottom: 0;
  left: 0;
  z-index: 1;
  width: 100%;
  height: 90%;
  opacity: 0.85;
  border-radius: 8px;
  background: linear-gradient(135deg, #fcd34d 0%, #fbbf24 100%);
}

.progress-ring {
  --progress: 0%;
  position: relative;
  display: grid;
  width: 74px;
  height: 74px;
  place-items: center;
  border-radius: 9999px;
  background: conic-gradient(#f59e0b var(--progress), rgba(245, 158, 11, 0.18) 0%);
  transition: background 180ms linear, transform 180ms ease;
}

.progress-ring::after {
  position: absolute;
  inset: 6px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.94);
  content: '';
}

.progress-ring-inner {
  position: relative;
  z-index: 1;
}

.progress-ring-pulse {
  animation: progress-pulse 280ms ease;
}

.success-ring,
.error-ring {
  display: grid;
  width: 76px;
  height: 76px;
  place-items: center;
  border-radius: 9999px;
}

.success-ring {
  border: 2px solid rgba(16, 185, 129, 0.35);
  background: radial-gradient(circle at 30% 30%, rgba(16, 185, 129, 0.24), rgba(16, 185, 129, 0.1));
  animation: success-pop 360ms ease;
}

.error-ring {
  border: 2px solid rgba(244, 63, 94, 0.35);
  background: radial-gradient(circle at 30% 30%, rgba(244, 63, 94, 0.25), rgba(244, 63, 94, 0.08));
}

.upload-phase-idle .upload-area-glow {
  opacity: 0.48;
}

.upload-phase-dragging {
  border-style: solid;
  border-color: rgba(245, 158, 11, 0.75);
  background: linear-gradient(145deg, rgba(251, 191, 36, 0.12) 0%, rgba(245, 158, 11, 0.16) 55%, rgba(251, 191, 36, 0.1) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(251, 191, 36, 0.28),
    0 16px 24px -18px rgba(245, 158, 11, 0.5);
  transform: translateY(-1px) scale(1.004);
}

.upload-phase-dragging .upload-area-focus {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
}

.upload-phase-dragging .folder {
  transform: translateY(-4px) scale(1.03);
}

.upload-phase-uploading {
  border-style: solid;
  border-color: rgba(245, 158, 11, 0.6);
  background: linear-gradient(145deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.14) 52%, rgba(251, 191, 36, 0.08) 100%);
}

.upload-phase-uploading .upload-area-glow {
  animation-duration: 2s;
  opacity: 0.56;
}

.upload-phase-success {
  border-style: solid;
  border-color: rgba(16, 185, 129, 0.44);
  background: linear-gradient(145deg, rgba(16, 185, 129, 0.12), rgba(5, 150, 105, 0.08));
}

.upload-phase-error {
  border-style: solid;
  border-color: rgba(244, 63, 94, 0.5);
  background: linear-gradient(145deg, rgba(244, 63, 94, 0.11), rgba(225, 29, 72, 0.08));
  animation: error-shake 300ms ease;
}

:global(.dark) .upload-area {
  border-color: rgba(245, 158, 11, 0.34);
  background: linear-gradient(145deg, rgba(217, 119, 6, 0.1) 0%, rgba(180, 83, 9, 0.16) 52%, rgba(146, 64, 14, 0.08) 100%);
}

:global(.dark) .progress-ring::after {
  background: rgba(24, 24, 27, 0.95);
}

:global(.dark) .folder .tip {
  background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
}

:global(.dark) .folder .cover {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

:global(.dark) .folder .back-side {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
}

.phase-fade-enter-active,
.phase-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.phase-fade-enter-from,
.phase-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@keyframes idle-breathe {
  0%, 100% {
    opacity: 0.42;
    transform: scale(0.98);
  }
  50% {
    opacity: 0.64;
    transform: scale(1.03);
  }
}

@keyframes idle-float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

@keyframes progress-pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.06);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes success-pop {
  0% {
    transform: scale(0.9);
    opacity: 0.6;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes error-shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-3px);
  }
  75% {
    transform: translateX(3px);
  }
}

@media (max-width: 640px) {
  .upload-area {
    min-height: 270px;
  }

  .folder {
    width: 130px;
    height: 104px;
  }

  .progress-ring,
  .success-ring,
  .error-ring {
    width: 68px;
    height: 68px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .upload-card,
  .upload-area,
  .upload-area-glow,
  .upload-area-focus,
  .folder,
  .progress-ring,
  .success-ring,
  .error-ring,
  .phase-fade-enter-active,
  .phase-fade-leave-active {
    animation: none !important;
    transition: none !important;
  }

  .upload-phase-dragging,
  .upload-phase-error {
    transform: none !important;
  }
}
</style>
