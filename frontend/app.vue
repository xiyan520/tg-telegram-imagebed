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

/* 文件夹动画样式 */
.upload-area {
  position: relative;
  min-height: 300px;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

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

/* 暗色模式支持 */
.dark .folder .tip {
  background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
}

.dark .folder .cover {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.dark .folder .back-side {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
}

/* 粘贴提示样式 */
.paste-hint {
  margin-top: 0.5rem;
}

.paste-hint kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
}

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

.dark .upload-card {
  background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
  border: 2px solid rgba(245, 158, 11, 0.2);
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.5),
    0 10px 10px -5px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(245, 158, 11, 0.1);
}

.dark .upload-card:hover {
  box-shadow:
    0 25px 50px -12px rgba(245, 158, 11, 0.4),
    0 0 0 1px rgba(245, 158, 11, 0.2);
}

/* 上传区域内部样式 */
.upload-area {
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

.dark .upload-area {
  background: linear-gradient(135deg,
    rgba(217, 119, 6, 0.05) 0%,
    rgba(234, 88, 12, 0.08) 50%,
    rgba(217, 119, 6, 0.05) 100%);
  border-color: rgba(245, 158, 11, 0.3);
}

.dark .upload-area:hover {
  background: linear-gradient(135deg,
    rgba(217, 119, 6, 0.1) 0%,
    rgba(234, 88, 12, 0.15) 50%,
    rgba(217, 119, 6, 0.1) 100%);
  border-color: rgba(245, 158, 11, 0.5);
}
</style>
