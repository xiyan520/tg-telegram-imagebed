<template>
  <div ref="layoutRoot" class="flex gap-4 xl:gap-8">
    <!-- 侧边栏 - 桌面端（sticky，避免遮挡正文） -->
    <aside ref="sidebarDock" class="relative hidden xl:block w-64 shrink-0">
      <div
        ref="floatingSidebar"
        class="docs-floating-sidebar w-64 max-h-[calc(100vh-7rem)] overflow-y-auto rounded-2xl border border-amber-200/80 bg-white/95 p-4 ring-1 ring-amber-500/10 backdrop-blur-xl dark:border-amber-400/30 dark:bg-stone-900/90 dark:ring-amber-400/10 supports-[backdrop-filter]:bg-white/80 supports-[backdrop-filter]:dark:bg-stone-900/70 transition-all duration-300"
        :class="floatingSidebarClass"
        :style="floatingSidebarStyle"
      >
        <DocsSidebar
          :sections="sections"
          :active-section="activeSection"
          :active-endpoint="activeEndpoint"
          @navigate="scrollToElement"
        />
      </div>
    </aside>

    <!-- 移动端侧边栏抽屉 -->
    <USlideover
      v-model="showMobileSidebar"
      side="left"
      :ui="{
        width: 'sm:max-w-md',
        base: '!bg-transparent dark:!bg-transparent !shadow-none !ring-0',
        overlay: { background: 'bg-stone-900/35 backdrop-blur-[1px]' }
      }"
    >
      <div class="h-full p-3 sm:p-4">
        <div class="flex h-full flex-col overflow-hidden rounded-3xl border border-amber-200/80 bg-white/95 ring-1 ring-amber-500/10 backdrop-blur-xl dark:border-amber-400/30 dark:bg-stone-900/92 dark:ring-amber-400/10">
          <div class="flex items-center justify-between border-b border-amber-100/80 px-4 py-3 dark:border-amber-800/40 sm:px-5">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">目录</h3>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              size="sm"
              @click="showMobileSidebar = false"
            />
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-3 py-3 sm:px-4 sm:py-4">
            <DocsSidebar
              :sections="sections"
              :active-section="activeSection"
              :active-endpoint="activeEndpoint"
              @navigate="handleMobileNavigate"
            />
          </div>
        </div>
      </div>
    </USlideover>

    <!-- 主内容区 -->
    <main class="flex-1 min-w-0">
      <div class="xl:hidden mb-4">
        <div class="rounded-xl border border-amber-200/70 bg-white/90 p-2 shadow-sm dark:border-amber-400/30 dark:bg-stone-900/85">
          <UButton
            icon="heroicons:bars-3"
            color="primary"
            variant="soft"
            size="sm"
            class="w-full justify-center"
            @click="showMobileSidebar = true"
          >
            打开目录导航
          </UButton>
        </div>
      </div>
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import type { ApiSection } from '~/data/apiDocs'

const props = defineProps<{
  sections: ApiSection[]
}>()

const showMobileSidebar = ref(false)
const activeSection = ref('')
const activeEndpoint = ref('')
const layoutRoot = ref<HTMLElement | null>(null)
const sidebarDock = ref<HTMLElement | null>(null)
const floatingSidebar = ref<HTMLElement | null>(null)
const floatingMode = ref<'fixed' | 'bottom' | 'sticky'>('sticky')
const fixedSidebarLeft = ref<number | null>(null)

let rafId: number | null = null

const floatingSidebarClass = computed(() =>
  floatingMode.value === 'fixed'
    ? 'fixed top-24 z-30'
    : floatingMode.value === 'bottom'
      ? 'absolute bottom-0 z-20'
      : 'sticky top-24 z-20'
)

const floatingSidebarStyle = computed(() => {
  if (floatingMode.value !== 'fixed' || fixedSidebarLeft.value === null) return undefined
  return { left: `${fixedSidebarLeft.value}px` }
})

const updateFloatingSidebar = () => {
  if (!import.meta.client) return

  const dock = sidebarDock.value
  const root = layoutRoot.value
  const sidebar = floatingSidebar.value
  if (!dock || !root || !sidebar || dock.getClientRects().length === 0) return

  fixedSidebarLeft.value = dock.getBoundingClientRect().left

  const rootRect = root.getBoundingClientRect()
  const sidebarHeight = sidebar.getBoundingClientRect().height
  const topOffset = 96
  const bottomBuffer = 24

  if (window.innerWidth < 1280) {
    floatingMode.value = 'sticky'
    return
  }

  // 页面还未滚到浮动触发点，保持 sticky
  if (rootRect.top > topOffset) {
    floatingMode.value = 'sticky'
    return
  }

  // 触底时吸附到底部，避免切回 sticky 出现“回弹”
  if (rootRect.bottom < topOffset + sidebarHeight + bottomBuffer) {
    floatingMode.value = 'bottom'
    return
  }

  floatingMode.value = 'fixed'
}

const scheduleFloatingSidebarUpdate = () => {
  if (!import.meta.client) return
  if (rafId !== null) return

  rafId = window.requestAnimationFrame(() => {
    rafId = null
    updateFloatingSidebar()
  })
}

const scrollToElement = (id: string) => {
  if (!import.meta.client) return
  const element = document.getElementById(id)
  if (!element) return

  const topOffset = 88
  const targetTop = element.getBoundingClientRect().top + window.scrollY - topOffset
  window.scrollTo({ top: Math.max(targetTop, 0), behavior: 'smooth' })
}

const handleMobileNavigate = (id: string) => {
  showMobileSidebar.value = false
  nextTick(() => {
    scrollToElement(id)
  })
}

// 构建有效的锚点 ID 集合（用于 scroll-spy）
const validAnchorIds = computed(() => {
  const ids = new Set<string>()
  props.sections.forEach((section) => {
    ids.add(section.id)
    section.endpoints.forEach((endpoint) => {
      ids.add(endpoint.id)
    })
  })
  return ids
})

// 用于存储 observer 实例
let observer: IntersectionObserver | null = null

// 监听滚动，更新当前激活的 section/endpoint
onMounted(() => {
  scheduleFloatingSidebarUpdate()
  window.addEventListener('resize', scheduleFloatingSidebarUpdate, { passive: true })
  window.addEventListener('scroll', scheduleFloatingSidebarUpdate, { passive: true })

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id
          // 只处理有效的锚点
          if (!validAnchorIds.value.has(id)) return

          // 判断是 section 还是 endpoint（通过查找 sections 数据）
          const isSection = props.sections.some((s) => s.id === id)
          if (isSection) {
            activeSection.value = id
            activeEndpoint.value = ''
          } else {
            activeEndpoint.value = id
            // 找到对应的 section
            const section = props.sections.find((s) =>
              s.endpoints.some((e) => e.id === id)
            )
            if (section) {
              activeSection.value = section.id
            }
          }
        }
      })
    },
    {
      rootMargin: '-20% 0px -70% 0px',
      threshold: 0,
    }
  )

  // 只观察有效的锚点元素
  nextTick(() => {
    scheduleFloatingSidebarUpdate()
    requestAnimationFrame(scheduleFloatingSidebarUpdate)

    validAnchorIds.value.forEach((id) => {
      const el = document.getElementById(id)
      if (el) {
        observer?.observe(el)
      }
    })
  })
})

// 清理 observer
onUnmounted(() => {
  window.removeEventListener('resize', scheduleFloatingSidebarUpdate)
  window.removeEventListener('scroll', scheduleFloatingSidebarUpdate)
  if (rafId !== null && import.meta.client) {
    window.cancelAnimationFrame(rafId)
    rafId = null
  }

  observer?.disconnect()
  observer = null
})
</script>

<style scoped>
/* 磁悬浮效果 - 卡片浮起来的视觉感 */
.docs-floating-sidebar {
  animation: float-in 0.45s ease-out;
  box-shadow:
    0 8px 22px -10px rgba(0, 0, 0, 0.15),
    0 12px 30px -18px rgba(251, 191, 36, 0.22);
}

.docs-floating-sidebar:hover {
  box-shadow:
    0 10px 28px -10px rgba(0, 0, 0, 0.2),
    0 16px 36px -16px rgba(251, 191, 36, 0.28);
}

:global(.dark) .docs-floating-sidebar {
  box-shadow:
    0 8px 24px -12px rgba(0, 0, 0, 0.5),
    0 14px 30px -16px rgba(251, 191, 36, 0.15);
}

:global(.dark) .docs-floating-sidebar:hover {
  box-shadow:
    0 10px 30px -10px rgba(0, 0, 0, 0.55),
    0 18px 36px -14px rgba(251, 191, 36, 0.22);
}

@keyframes float-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 滚动条样式 */
.docs-floating-sidebar::-webkit-scrollbar {
  width: 6px;
}

.docs-floating-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.docs-floating-sidebar::-webkit-scrollbar-thumb {
  background: rgba(251, 191, 36, 0.3);
  border-radius: 3px;
}

.docs-floating-sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(251, 191, 36, 0.5);
}

:global(.dark) .docs-floating-sidebar::-webkit-scrollbar-thumb {
  background: rgba(251, 191, 36, 0.2);
}

:global(.dark) .docs-floating-sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(251, 191, 36, 0.4);
}
</style>
