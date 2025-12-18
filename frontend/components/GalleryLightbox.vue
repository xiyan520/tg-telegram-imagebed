<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-[100] overscroll-contain"
        :style="overlayStyle"
        role="dialog"
        aria-modal="true"
        aria-label="图片查看器"
        tabindex="-1"
      >
        <!-- 手势容器 -->
        <div
          ref="gestureEl"
          class="absolute inset-0 touch-none overflow-hidden"
          @touchstart.passive="onTouchStart"
          @touchmove.prevent="onTouchMove"
          @touchend.passive="onTouchEnd"
          @touchcancel.passive="onTouchEnd"
          @click="onTap"
        >
          <!-- 图片滑动容器 -->
          <div
            class="absolute inset-0 flex items-center justify-center will-change-transform"
            :class="swipeTransitionClass"
            :style="{ transform: `translateX(${swipeX}px)` }"
          >
            <!-- 上一张 -->
            <div
              v-if="prevImage"
              class="absolute inset-0 flex items-center justify-center -translate-x-full"
            >
              <img
                :src="prevImage.image_url"
                :alt="prevImage.original_filename"
                class="max-w-full max-h-full object-contain"
                draggable="false"
              />
            </div>

            <!-- 当前图片 -->
            <div
              class="absolute inset-0 flex items-center justify-center origin-center will-change-transform"
              :class="imageTransitionClass"
              :style="imageStyle"
            >
              <img
                v-if="currentImage"
                :src="currentImage.image_url"
                :alt="currentImage.original_filename"
                class="max-w-full max-h-full object-contain select-none"
                draggable="false"
                decoding="async"
                fetchpriority="high"
              />
            </div>

            <!-- 下一张 -->
            <div
              v-if="nextImage"
              class="absolute inset-0 flex items-center justify-center translate-x-full"
            >
              <img
                :src="nextImage.image_url"
                :alt="nextImage.original_filename"
                class="max-w-full max-h-full object-contain"
                draggable="false"
              />
            </div>
          </div>
        </div>

        <!-- 控件层 -->
        <div
          class="absolute inset-0 pointer-events-none flex flex-col justify-between transition-opacity duration-300"
          :class="{ 'opacity-0': !showControls || isZoomed }"
        >
          <!-- 顶部栏 -->
          <div
            class="bg-gradient-to-b from-black/70 to-transparent px-4 pt-4 pb-16 text-white pointer-events-auto transition-transform duration-300"
            :class="{ '-translate-y-full': !showControls }"
            :style="{ paddingTop: 'max(env(safe-area-inset-top), 16px)' }"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium truncate">{{ currentImage?.original_filename }}</p>
                <p class="text-xs text-white/70">{{ safeIndex + 1 }} / {{ images.length }}</p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <UButton
                  icon="heroicons:arrow-down-tray"
                  color="white"
                  variant="ghost"
                  size="md"
                  aria-label="下载图片"
                  :disabled="!currentImage"
                  @click.stop="downloadCurrent"
                />
                <UButton
                  ref="closeButtonRef"
                  icon="heroicons:x-mark"
                  color="white"
                  variant="ghost"
                  size="md"
                  aria-label="关闭"
                  @click.stop="close"
                />
              </div>
            </div>
          </div>

          <!-- 左右导航按钮 (桌面端) -->
          <div class="flex-1 flex items-center justify-between px-4 pointer-events-none">
            <UButton
              v-if="hasPrev"
              icon="heroicons:chevron-left"
              color="white"
              variant="ghost"
              size="xl"
              class="pointer-events-auto hidden sm:flex bg-black/30 hover:bg-black/50 rounded-full !p-3"
              aria-label="上一张"
              @click.stop="goPrev"
            />
            <div v-else />
            <UButton
              v-if="hasNext"
              icon="heroicons:chevron-right"
              color="white"
              variant="ghost"
              size="xl"
              class="pointer-events-auto hidden sm:flex bg-black/30 hover:bg-black/50 rounded-full !p-3"
              aria-label="下一张"
              @click.stop="goNext"
            />
          </div>

          <!-- 底部提示 -->
          <div
            class="bg-gradient-to-t from-black/70 to-transparent px-4 pb-6 pt-16 text-center pointer-events-none"
            :style="{ paddingBottom: 'max(env(safe-area-inset-bottom), 24px)' }"
          >
            <p class="text-xs text-white/50 hidden sm:block">← → 切换图片 · ESC 关闭</p>
            <p class="text-xs text-white/50 sm:hidden">左右滑动切换 · 下滑关闭 · 双指缩放</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'
import { useScrollLock, useWindowSize, useEventListener } from '@vueuse/core'

const props = withDefaults(defineProps<{
  open: boolean
  index: number
  images: GalleryImage[]
}>(), {
  images: () => []
})

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'update:index', v: number): void
}>()

const { width: vw, height: vh } = useWindowSize()

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))

const safeIndex = computed(() => {
  const max = Math.max(0, props.images.length - 1)
  return clamp(props.index, 0, max)
})

const currentImage = computed(() => props.images[safeIndex.value] || null)
const prevImage = computed(() => props.images[safeIndex.value - 1] || null)
const nextImage = computed(() => props.images[safeIndex.value + 1] || null)
const hasPrev = computed(() => safeIndex.value > 0)
const hasNext = computed(() => safeIndex.value < props.images.length - 1)

// 定时器管理
let resetAfterCloseTimer: ReturnType<typeof setTimeout> | undefined
let swipeCommitTimer: ReturnType<typeof setTimeout> | undefined
let tapToggleTimer: ReturnType<typeof setTimeout> | undefined

const clearTimers = () => {
  if (resetAfterCloseTimer) { clearTimeout(resetAfterCloseTimer); resetAfterCloseTimer = undefined }
  if (swipeCommitTimer) { clearTimeout(swipeCommitTimer); swipeCommitTimer = undefined }
  if (tapToggleTimer) { clearTimeout(tapToggleTimer); tapToggleTimer = undefined }
}

const setIndex = (next: number) => emit('update:index', clamp(next, 0, Math.max(0, props.images.length - 1)))
const close = () => { clearTimers(); emit('update:open', false) }
const goPrev = () => { if (hasPrev.value) setIndex(safeIndex.value - 1) }
const goNext = () => { if (hasNext.value) setIndex(safeIndex.value + 1) }

// 滚动锁定
if (import.meta.client) {
  const locked = useScrollLock(document.body)
  watch(() => props.open, (v) => { locked.value = v }, { immediate: true })
}

// 键盘导航
useEventListener(import.meta.client ? window : undefined, 'keydown', (e: KeyboardEvent) => {
  if (!props.open) return
  if (e.key === 'Escape') { e.preventDefault(); close() }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); goPrev() }
  else if (e.key === 'ArrowRight') { e.preventDefault(); goNext() }
}, { passive: false })

// 下载当前图片
const downloadCurrent = () => {
  if (!import.meta.client || !currentImage.value) return
  const link = document.createElement('a')
  link.href = currentImage.value.image_url
  link.download = currentImage.value.original_filename || 'image'
  link.target = '_blank'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

// 预加载相邻图片（带去重）
const preloadedUrls = new Set<string>()
const preloadAt = (idx: number) => {
  if (!import.meta.client) return
  const url = props.images[idx]?.image_url
  if (!url || preloadedUrls.has(url)) return
  preloadedUrls.add(url)
  if (preloadedUrls.size > 64) preloadedUrls.clear()
  const img = new Image()
  img.decoding = 'async'
  img.src = url
}

watch([() => props.open, safeIndex], ([isOpen]) => {
  if (!isOpen) return
  preloadAt(safeIndex.value + 1)
  preloadAt(safeIndex.value - 1)
}, { immediate: true })

// 手势状态
const gestureEl = ref<HTMLElement | null>(null)
const closeButtonRef = ref<any>(null)
const showControls = ref(true)
const isDragging = ref(false)
const isZooming = ref(false)
const isAnimating = ref(false)

// 变换状态
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const swipeX = ref(0)
const dismissY = ref(0)

const isZoomed = computed(() => scale.value > 1.05)

// 手势追踪
let touchStartPoints: { x: number; y: number }[] = []
let startScale = 1
let startTranslateX = 0
let startTranslateY = 0
let startSwipeX = 0
let startDist = 0
let dragAxis: 'none' | 'x' | 'y' = 'none'
let lastTapTime = 0
let swipeStartTime = 0

const resetTransform = () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
  swipeX.value = 0
  dismissY.value = 0
  dragAxis = 'none'
  isAnimating.value = false
}

// 计算样式
const swipeTransitionClass = computed(() =>
  !isDragging.value && !isZooming.value && isAnimating.value
    ? 'transition-transform duration-300 ease-out'
    : ''
)

const imageTransitionClass = computed(() =>
  !isDragging.value && !isZooming.value
    ? 'transition-transform duration-200 ease-out'
    : ''
)

const imageStyle = computed(() => {
  const s = scale.value
  const x = translateX.value
  const y = translateY.value + dismissY.value
  const dismissScale = 1 - Math.min(0.15, Math.abs(dismissY.value) / Math.max(1, vh.value) * 0.35)
  const finalScale = dragAxis === 'y' && !isZoomed.value ? s * dismissScale : s
  return { transform: `translate(${x}px, ${y}px) scale(${finalScale})` }
})

const overlayAlpha = computed(() => {
  const base = 0.95
  if (dragAxis !== 'y' || isZoomed.value) return base
  const fade = Math.min(0.45, Math.abs(dismissY.value) / Math.max(1, vh.value))
  return Math.max(0.5, base * (1 - fade))
})

const overlayStyle = computed(() => ({
  backgroundColor: `rgba(0,0,0,${overlayAlpha.value})`,
  paddingTop: 'env(safe-area-inset-top)',
  paddingBottom: 'env(safe-area-inset-bottom)'
}))

// 触摸事件处理
const onTouchStart = (e: TouchEvent) => {
  if (!props.open) return

  touchStartPoints = Array.from(e.touches).map(t => ({ x: t.clientX, y: t.clientY }))
  startScale = scale.value
  startTranslateX = translateX.value
  startTranslateY = translateY.value
  startSwipeX = swipeX.value
  swipeStartTime = performance.now()
  dragAxis = 'none'
  isAnimating.value = false

  if (e.touches.length === 2) {
    const dist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY
    )
    startDist = dist || 1
    isZooming.value = true
    isDragging.value = false
  } else if (e.touches.length === 1) {
    isDragging.value = true
    isZooming.value = false
  }
}

const onTouchMove = (e: TouchEvent) => {
  if (!props.open) return

  if (e.touches.length === 2 && isZooming.value) {
    if (startDist <= 0) return
    const dist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY
    )
    scale.value = Math.max(1, Math.min(5, startScale * (dist / startDist)))
  } else if (e.touches.length === 1 && isDragging.value && touchStartPoints.length > 0) {
    const dx = e.touches[0].clientX - touchStartPoints[0].x
    const dy = e.touches[0].clientY - touchStartPoints[0].y

    if (isZoomed.value) {
      translateX.value = startTranslateX + dx
      translateY.value = startTranslateY + dy
    } else {
      if (dragAxis === 'none') {
        const ax = Math.abs(dx)
        const ay = Math.abs(dy)
        if (ax > 12 || ay > 12) {
          dragAxis = ax > ay * 1.3 ? 'x' : ay > ax * 1.3 ? 'y' : 'none'
        }
      }

      if (dragAxis === 'x') {
        const edgeDamp = (dx > 0 && !hasPrev.value) || (dx < 0 && !hasNext.value) ? 0.3 : 1
        swipeX.value = startSwipeX + dx * edgeDamp
        dismissY.value = 0
      } else if (dragAxis === 'y') {
        dismissY.value = dy
        swipeX.value = 0
      }
    }
  }
}

const onTouchEnd = () => {
  if (!props.open) return

  touchStartPoints = []
  const dt = Math.max(16, performance.now() - swipeStartTime)
  const velocity = swipeX.value / dt * 1000

  isDragging.value = false
  isZooming.value = false
  isAnimating.value = true

  // 下滑关闭
  if (dragAxis === 'y' && !isZoomed.value && dismissY.value > 100) {
    close()
    if (resetAfterCloseTimer) clearTimeout(resetAfterCloseTimer)
    resetAfterCloseTimer = setTimeout(resetTransform, 200)
    return
  }
  dismissY.value = 0

  // 左右滑动切换
  const threshold = Math.max(80, vw.value * 0.2)
  const velocityThreshold = 800

  if (dragAxis === 'x' && !isZoomed.value) {
    if ((swipeX.value < -threshold || velocity < -velocityThreshold) && hasNext.value) {
      swipeX.value = -vw.value
      if (swipeCommitTimer) clearTimeout(swipeCommitTimer)
      swipeCommitTimer = setTimeout(() => {
        if (!props.open) return
        isAnimating.value = false
        goNext()
        swipeX.value = 0
        dragAxis = 'none'
      }, 300)
      return
    } else if ((swipeX.value > threshold || velocity > velocityThreshold) && hasPrev.value) {
      swipeX.value = vw.value
      if (swipeCommitTimer) clearTimeout(swipeCommitTimer)
      swipeCommitTimer = setTimeout(() => {
        if (!props.open) return
        isAnimating.value = false
        goPrev()
        swipeX.value = 0
        dragAxis = 'none'
      }, 300)
      return
    }
  }

  swipeX.value = 0
  if (scale.value < 1) scale.value = 1
  dragAxis = 'none'
}

// 点击/双击处理
const onTap = (e: MouseEvent) => {
  if (isDragging.value || isZooming.value) return

  const now = Date.now()
  if (now - lastTapTime < 300) {
    // 双击缩放
    isAnimating.value = true
    if (scale.value > 1) {
      scale.value = 1
      translateX.value = 0
      translateY.value = 0
    } else {
      scale.value = 2.5
    }
  } else {
    // 单击切换控件
    if (tapToggleTimer) clearTimeout(tapToggleTimer)
    tapToggleTimer = setTimeout(() => {
      if (Date.now() - lastTapTime > 280 && swipeX.value === 0) {
        showControls.value = !showControls.value
      }
    }, 300)
  }
  lastTapTime = now
}

// 打开时重置状态并聚焦关闭按钮
watch(() => props.open, (isOpen) => {
  if (!isOpen) {
    clearTimers()
    return
  }
  resetTransform()
  showControls.value = true
  preloadedUrls.clear()
  nextTick(() => {
    closeButtonRef.value?.$el?.focus?.() || closeButtonRef.value?.focus?.()
  })
})

// 切换图片时重置缩放
watch(safeIndex, () => {
  if (props.open) {
    scale.value = 1
    translateX.value = 0
    translateY.value = 0
  }
})

// 组件卸载时清理定时器
onBeforeUnmount(() => {
  clearTimers()
})
</script>
