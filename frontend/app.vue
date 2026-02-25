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
const { seoSettings, displayName, displayDescription, displayKeywords, loadSeoSettings } = useSeoSettings()

// 动态 SEO head 配置
useHead(computed(() => {
  const head: any = {
    htmlAttrs: { lang: 'zh-CN' },
    bodyAttrs: { class: 'bg-gray-50 dark:bg-neutral-950' },
    title: displayName.value,
    meta: [
      { name: 'description', content: displayDescription.value },
      { name: 'keywords', content: displayKeywords.value },
      // OG 标签
      { property: 'og:title', content: seoSettings.value.ogTitle || displayName.value },
      { property: 'og:description', content: seoSettings.value.ogDescription || displayDescription.value },
      { property: 'og:type', content: 'website' },
      // Twitter 标签
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: seoSettings.value.ogTitle || displayName.value },
      { name: 'twitter:description', content: seoSettings.value.ogDescription || displayDescription.value },
    ],
    link: [] as any[],
  }

  // OG 图片
  if (seoSettings.value.ogImage) {
    head.meta.push({ property: 'og:image', content: seoSettings.value.ogImage })
    head.meta.push({ name: 'twitter:image', content: seoSettings.value.ogImage })
  }

  // 自定义 Favicon
  if (seoSettings.value.faviconUrl) {
    head.link.push({ rel: 'icon', href: seoSettings.value.faviconUrl })
  }

  return head
}))

// 加载 SEO 设置（SPA 模式下 setup 即客户端，尽早发起请求）
loadSeoSettings()
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
   弹窗（Modal）全局样式补充
   主要布局已通过 app.config.ts 的 ui.modal 配置
   此处仅保留 CSS 无法通过 ui prop 实现的覆盖
   ======================================== */

/*
 * 弹窗内容区滚动控制
 * Nuxt UI Modal 不提供内容区滚动的 ui prop，需要 CSS 覆盖
 * 使用 CSS 自定义属性统一管理响应式高度
 */
:root {
  --modal-max-h: 90vh;
  --modal-header-offset: 6rem;
}

/* 弹窗内容区滚动 */
[role="dialog"] [class*="space-y"] {
  overflow-y: auto;
  overflow-x: hidden;
  max-height: calc(var(--modal-max-h) - var(--modal-header-offset));
  padding-right: 0.5rem;
}

/* 弹窗内容区滚动条样式 */
[role="dialog"] [class*="space-y"]::-webkit-scrollbar {
  width: 6px;
}

[role="dialog"] [class*="space-y"]::-webkit-scrollbar-track {
  background: transparent;
}

[role="dialog"] [class*="space-y"]::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

[role="dialog"] [class*="space-y"]::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.7);
}

/* ========================================
   响应式优化 - 使用 CSS 自定义属性统一调整
   ======================================== */

@media (max-height: 1000px) {
  :root {
    --modal-max-h: 85vh;
  }
}

@media (max-height: 800px) {
  :root {
    --modal-max-h: 80vh;
    --modal-header-offset: 5rem;
  }
}

@media (max-height: 700px) {
  :root {
    --modal-max-h: 75vh;
    --modal-header-offset: 4rem;
  }
}

@media (max-height: 600px) {
  :root {
    --modal-max-h: 70vh;
    --modal-header-offset: 3.5rem;
  }
}
</style>
