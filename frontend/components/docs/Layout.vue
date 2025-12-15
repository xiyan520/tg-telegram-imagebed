<template>
  <div class="flex gap-8">
    <!-- 侧边栏 - 桌面端（磁悬浮样式，保持原位置） -->
    <aside ref="sidebarDock" class="hidden lg:block w-64 shrink-0">
      <div
        class="docs-floating-sidebar fixed top-20 z-30 w-64 max-h-[calc(100vh-6rem)] overflow-y-auto rounded-2xl border border-amber-200/80 bg-white/95 p-4 ring-2 ring-amber-500/10 backdrop-blur-xl dark:border-amber-400/30 dark:bg-stone-900/90 dark:ring-amber-400/10 supports-[backdrop-filter]:bg-white/80 supports-[backdrop-filter]:dark:bg-stone-900/70 transition-all duration-300"
        :style="fixedSidebarStyle"
      >
        <DocsSidebar
          :sections="sections"
          :active-section="activeSection"
          :active-endpoint="activeEndpoint"
          @navigate="scrollToElement"
        />
      </div>
    </aside>

    <!-- 移动端侧边栏按钮 -->
    <div class="lg:hidden fixed bottom-4 right-4 z-40">
      <UButton
        icon="heroicons:bars-3"
        color="primary"
        size="lg"
        class="shadow-lg"
        @click="showMobileSidebar = true"
      />
    </div>

    <!-- 移动端侧边栏抽屉 -->
    <USlideover v-model="showMobileSidebar" side="left">
      <div class="p-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">目录</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            size="sm"
            @click="showMobileSidebar = false"
          />
        </div>
        <DocsSidebar
          :sections="sections"
          :active-section="activeSection"
          :active-endpoint="activeEndpoint"
          @navigate="handleMobileNavigate"
        />
      </div>
    </USlideover>

    <!-- 主内容区 -->
    <main class="flex-1 min-w-0">
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

const sidebarDock = ref<HTMLElement | null>(null)
const fixedSidebarLeft = ref<number | null>(null)

const updateFixedSidebarLeft = () => {
  const dock = sidebarDock.value
  if (!dock) return
  if (dock.getClientRects().length === 0) return
  fixedSidebarLeft.value = dock.getBoundingClientRect().left
}

const fixedSidebarStyle = computed(() =>
  fixedSidebarLeft.value === null ? undefined : { left: `${fixedSidebarLeft.value}px` }
)

const handleResize = () => {
  updateFixedSidebarLeft()
}

const scrollToElement = (id: string) => {
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
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
  updateFixedSidebarLeft()
  window.addEventListener('resize', handleResize, { passive: true })

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
    updateFixedSidebarLeft()
    requestAnimationFrame(updateFixedSidebarLeft)

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
  window.removeEventListener('resize', handleResize)
  observer?.disconnect()
  observer = null
})
</script>

<style scoped>
/* 磁悬浮效果 - 卡片浮起来的视觉感 */
.docs-floating-sidebar {
  animation: float-in 0.6s ease-out;
  /* 核心磁悬浮效果：向上浮起 + 多层阴影 */
  transform: translateY(-4px);
  box-shadow:
    0 10px 25px -5px rgba(0, 0, 0, 0.1),
    0 20px 40px -15px rgba(251, 191, 36, 0.2),
    0 0 0 1px rgba(251, 191, 36, 0.05);
}

.docs-floating-sidebar:hover {
  transform: translateY(-6px);
  box-shadow:
    0 15px 35px -5px rgba(0, 0, 0, 0.15),
    0 25px 50px -15px rgba(251, 191, 36, 0.35),
    0 0 0 1px rgba(251, 191, 36, 0.1);
}

:global(.dark) .docs-floating-sidebar {
  box-shadow:
    0 10px 25px -5px rgba(0, 0, 0, 0.4),
    0 20px 40px -15px rgba(251, 191, 36, 0.15),
    0 0 0 1px rgba(251, 191, 36, 0.08);
}

:global(.dark) .docs-floating-sidebar:hover {
  box-shadow:
    0 15px 35px -5px rgba(0, 0, 0, 0.5),
    0 25px 50px -15px rgba(251, 191, 36, 0.25),
    0 0 0 1px rgba(251, 191, 36, 0.15);
}

@keyframes float-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(-4px);
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
