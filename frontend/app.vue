<template>
  <div class="bg-gray-50 dark:bg-neutral-950">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <!-- 新的轻量级Toast通知 - 完全不阻止交互 -->
    <LightToast />
  </div>
</template>

<script setup lang="ts">
useHead({
  htmlAttrs: {
    lang: 'zh-CN'
  },
  bodyAttrs: {
    class: 'bg-gray-50 dark:bg-neutral-950'
  }
})
</script>

<style>
/* 确保 html 和 body 元素有背景色，避免宽屏模式下透明 */
html {
  background-color: rgb(249 250 251); /* bg-gray-50 */
}

html.dark {
  background-color: rgb(10 10 10); /* bg-neutral-950 */
}

body {
  background-color: rgb(249 250 251); /* bg-gray-50 */
}

body.dark {
  background-color: rgb(10 10 10); /* bg-neutral-950 */
}

/* ========================================
   弹窗（Modal）全局优化 - 终极解决方案
   彻底解决所有分辨率下的滚动和点击问题
   ======================================== */

/* 强制重置弹窗的所有样式 */
:deep(.fixed.inset-0) {
  z-index: 50 !important;
}

/* 1. 弹窗背景遮罩 - 确保不阻止点击 */
:deep([role="dialog"]) {
  position: fixed !important;
  max-height: 90vh !important;
  max-width: 90vw !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: visible !important;
  margin: auto !important;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) !important;
}

/* 2. 所有弹窗内的元素都可交互 */
:deep([role="dialog"] *) {
  pointer-events: auto !important;
}

/* 3. UCard 组件结构优化 */
:deep([role="dialog"] > div),
:deep([role="dialog"] > div > div) {
  display: flex !important;
  flex-direction: column !important;
  max-height: 90vh !important;
  width: 100% !important;
}

/* 4. 卡片内容包装器 */
:deep([role="dialog"] [class*="space-y"]) {
  overflow-y: auto !important;
  overflow-x: hidden !important;
  max-height: calc(90vh - 6rem) !important;
  padding-right: 0.5rem !important;
}

/* 5. 确保所有按钮完全可点击 */
:deep([role="dialog"] button),
:deep([role="dialog"] input),
:deep([role="dialog"] a) {
  pointer-events: auto !important;
  cursor: pointer !important;
  position: relative !important;
  z-index: 10 !important;
  touch-action: auto !important;
}

/* 6. 确保 flex 容器内的元素可交互 */
:deep([role="dialog"] .flex),
:deep([role="dialog"] .flex > *) {
  pointer-events: auto !important;
  position: relative !important;
  z-index: 5 !important;
}

/* 7. 滚动条样式优化 */
:deep([role="dialog"] [class*="space-y"]::-webkit-scrollbar) {
  width: 6px;
}

:deep([role="dialog"] [class*="space-y"]::-webkit-scrollbar-track) {
  background: transparent;
}

:deep([role="dialog"] [class*="space-y"]::-webkit-scrollbar-thumb) {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

:deep([role="dialog"] [class*="space-y"]::-webkit-scrollbar-thumb:hover) {
  background: rgba(156, 163, 175, 0.7);
}

/* ========================================
   响应式优化 - 针对不同屏幕高度
   ======================================== */

/* 针对 1300x954 等中等分辨率 (高度 < 1000px) */
@media (max-height: 1000px) {
  :deep([role="dialog"]) {
    max-height: 85vh !important;
  }

  :deep([role="dialog"] > div),
  :deep([role="dialog"] > div > div) {
    max-height: 85vh !important;
  }

  :deep([role="dialog"] [class*="space-y"]) {
    max-height: calc(85vh - 6rem) !important;
  }
}

/* 针对较小高度屏幕 (高度 < 800px) */
@media (max-height: 800px) {
  :deep([role="dialog"]) {
    max-height: 80vh !important;
  }

  :deep([role="dialog"] > div),
  :deep([role="dialog"] > div > div) {
    max-height: 80vh !important;
  }

  :deep([role="dialog"] [class*="space-y"]) {
    max-height: calc(80vh - 5rem) !important;
  }
}

/* 针对非常小的屏幕 (高度 < 700px) */
@media (max-height: 700px) {
  :deep([role="dialog"]) {
    max-height: 75vh !important;
  }

  :deep([role="dialog"] > div),
  :deep([role="dialog"] > div > div) {
    max-height: 75vh !important;
  }

  :deep([role="dialog"] [class*="space-y"]) {
    max-height: calc(75vh - 4rem) !important;
  }
}

/* 针对极小屏幕 (高度 < 600px) */
@media (max-height: 600px) {
  :deep([role="dialog"]) {
    max-height: 70vh !important;
  }

  :deep([role="dialog"] > div),
  :deep([role="dialog"] > div > div) {
    max-height: 70vh !important;
  }

  :deep([role="dialog"] [class*="space-y"]) {
    max-height: calc(70vh - 3.5rem) !important;
  }
}

/* ========================================
   新的轻量级Toast通知系统
   样式已在 LightToast.vue 组件中定义
   ======================================== */

/* 文件夹动画和上传区域样式已迁移到 components/home/HomeUploadZone.vue */
</style>
