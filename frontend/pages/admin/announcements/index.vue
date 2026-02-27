<template>
  <div class="relative space-y-6 pb-10">
    <div class="pointer-events-none absolute -top-20 right-0 h-44 w-44 rounded-full bg-amber-200/30 blur-3xl dark:bg-amber-700/15" />
    <div class="pointer-events-none absolute top-56 -left-10 h-40 w-40 rounded-full bg-orange-200/25 blur-3xl dark:bg-orange-700/10" />

    <AdminPageHeader
      title="公告管理"
      eyebrow="Config"
      icon="heroicons:megaphone"
      description="编辑站点公告内容、展示状态与发布行为"
    >
      <template #actions>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadAnnouncement"
        >
          刷新
        </UButton>
        <UButton
          icon="heroicons:arrow-uturn-left"
          color="gray"
          variant="outline"
          :disabled="!hasUnsavedChanges"
          @click="resetAnnouncement"
        >
          重置未保存
        </UButton>
        <UButton
          icon="heroicons:check"
          color="primary"
          :loading="saving"
          @click="saveAnnouncement"
        >
          保存公告
          <UBadge v-if="dirtyCount > 0" color="amber" variant="solid" size="xs" class="ml-1.5">
            {{ dirtyCount }}
          </UBadge>
        </UButton>
      </template>
    </AdminPageHeader>

    <div v-if="loading && !initialLoaded" class="flex justify-center py-12">
      <div class="h-12 w-12 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
    </div>

    <template v-else>
      <div class="space-y-4">
        <AdminAnnouncementTopNav
          class="hidden lg:block"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />
        <AdminAnnouncementMobileNavDrawer
          class="lg:hidden"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />

        <AdminAnnouncementSectionCard
          :id="sectionDomId('status')"
          title="状态与展示策略"
          description="控制公告是否展示给访客，以及当前版本状态"
          icon="heroicons:power"
          :dirty="Boolean(dirtyMap.status)"
          :saving="Boolean(sectionSaving.status)"
          save-label="保存状态"
          @save="saveSection('status')"
        >
          <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/70">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-xl"
                  :class="announcement.enabled ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-stone-100 text-stone-600 dark:bg-neutral-800 dark:text-stone-300'"
                >
                  <UIcon :name="announcement.enabled ? 'heroicons:check-badge' : 'heroicons:pause-circle'" class="h-5 w-5" />
                </div>
                <div>
                  <p class="text-base font-semibold text-stone-900 dark:text-white">
                    {{ announcement.enabled ? '公告已启用' : '公告已禁用' }}
                  </p>
                  <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">
                    {{ announcement.enabled ? '前台访客会收到本公告弹窗' : '前台不会弹出公告' }}
                  </p>
                </div>
              </div>
              <UToggle v-model="announcement.enabled" size="lg" />
            </div>

            <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3">
              <div class="rounded-xl border border-stone-200/70 bg-white/80 p-2.5 dark:border-neutral-700/70 dark:bg-neutral-900/70 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400 sm:text-xs sm:tracking-[0.16em]">当前公告 ID</p>
                <p class="mt-1 text-base font-semibold text-stone-900 dark:text-white sm:text-lg">#{{ announcement.id || 0 }}</p>
              </div>
              <div class="rounded-xl border border-stone-200/70 bg-white/80 p-2.5 dark:border-neutral-700/70 dark:bg-neutral-900/70 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400 sm:text-xs sm:tracking-[0.16em]">更新时间</p>
                <p class="mt-1 text-xs font-medium text-stone-900 dark:text-white sm:text-sm">{{ formatDate(announcement.updated_at) }}</p>
              </div>
              <div class="col-span-2 rounded-xl border border-amber-200/70 bg-amber-50/75 p-2.5 dark:border-amber-800/70 dark:bg-amber-900/20 sm:col-span-1 sm:rounded-2xl sm:p-3">
                <p class="text-[10px] uppercase tracking-[0.12em] text-amber-700 dark:text-amber-300 sm:text-xs sm:tracking-[0.16em]">展示策略</p>
                <p class="mt-1 text-xs font-medium text-amber-800 dark:text-amber-200 sm:text-sm">每条公告仅弹一次</p>
              </div>
            </div>
          </div>
        </AdminAnnouncementSectionCard>

        <AdminAnnouncementSectionCard
          :id="sectionDomId('editor')"
          title="内容编辑与预览"
          description="左侧编辑 HTML 公告内容，右侧实时预览"
          icon="heroicons:pencil-square"
          :dirty="Boolean(dirtyMap.editor)"
          :saving="Boolean(sectionSaving.editor)"
          save-label="保存内容"
          @save="saveSection('editor')"
        >
          <div class="grid gap-4 xl:grid-cols-2">
            <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/70">
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <UIcon name="heroicons:code-bracket-square" class="h-4 w-4 text-amber-500" />
                  <p class="text-sm font-medium text-stone-900 dark:text-white">HTML 编辑器</p>
                </div>
                <p class="text-xs text-stone-500 dark:text-stone-400">支持 HTML 标签</p>
              </div>
              <UTextarea
                v-model="announcement.content"
                :rows="16"
                placeholder="请输入公告内容，支持 HTML..."
                class="mt-3 font-mono text-sm"
              />
              <div class="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 dark:text-stone-400">
                <p>可用标签：&lt;strong&gt;、&lt;p&gt;、&lt;ul&gt;、&lt;a&gt;</p>
                <p>字符数：{{ contentLength }}</p>
              </div>
            </div>

            <div class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/70">
              <div class="flex items-center gap-2">
                <UIcon name="heroicons:eye" class="h-4 w-4 text-emerald-500" />
                <p class="text-sm font-medium text-stone-900 dark:text-white">实时预览</p>
              </div>
              <div class="mt-3 min-h-[280px] max-h-[520px] overflow-y-auto rounded-xl border border-dashed border-stone-300 bg-stone-50/70 p-4 dark:border-neutral-700 dark:bg-neutral-800/70">
                <div
                  v-if="announcement.content.trim()"
                  class="announcement-preview-content prose max-w-none text-sm dark:prose-invert"
                  v-html="announcement.content"
                />
                <div v-else class="flex min-h-[180px] items-center justify-center text-sm text-stone-400 dark:text-stone-500">
                  暂无公告内容，先在左侧输入文案
                </div>
              </div>
            </div>
          </div>
        </AdminAnnouncementSectionCard>

        <AdminAnnouncementSectionCard
          :id="sectionDomId('templates')"
          title="模板库"
          description="快速应用常用公告模版，再按需修改"
          icon="heroicons:document-duplicate"
          :show-save="false"
        >
          <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <button
              v-for="(template, index) in announcementTemplates"
              :key="index"
              type="button"
              class="group rounded-2xl border border-stone-200/80 bg-white/85 p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-[0_12px_26px_-18px_rgba(245,158,11,0.45)] dark:border-neutral-700/80 dark:bg-neutral-900/70 dark:hover:border-amber-700/70"
              @click="useTemplate(template.content)"
            >
              <div class="flex items-start justify-between gap-2">
                <p class="text-sm font-semibold text-stone-900 dark:text-white">{{ template.name }}</p>
                <UIcon name="heroicons:arrow-right-circle" class="h-4 w-4 text-amber-500 transition-transform duration-200 group-hover:translate-x-0.5" />
              </div>
              <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">{{ template.description }}</p>
              <p class="mt-2 line-clamp-2 text-xs text-stone-500/90 dark:text-stone-400/90">{{ extractTemplateSummary(template.content) }}</p>
            </button>
          </div>
        </AdminAnnouncementSectionCard>

        <AdminAnnouncementSectionCard
          :id="sectionDomId('publish')"
          title="发布与元信息"
          description="查看元数据并执行最终发布操作"
          icon="heroicons:rocket-launch"
          :dirty="Boolean(dirtyMap.publish)"
          :show-save="false"
        >
          <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">公告 ID</p>
              <p class="mt-1 text-base font-semibold text-stone-900 dark:text-white">#{{ announcement.id || 0 }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">创建时间</p>
              <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ formatDate(announcement.created_at) }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">更新时间</p>
              <p class="mt-1 text-sm font-semibold text-stone-900 dark:text-white">{{ formatDate(announcement.updated_at) }}</p>
            </div>
            <div class="rounded-xl border border-stone-200/70 bg-white/80 p-3 dark:border-neutral-700/70 dark:bg-neutral-900/70">
              <p class="text-xs uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">状态</p>
              <UBadge :color="announcement.enabled ? 'green' : 'gray'" variant="subtle" class="mt-1">
                {{ announcement.enabled ? '已启用' : '已禁用' }}
              </UBadge>
            </div>
          </div>
          <div class="mt-4 flex flex-wrap justify-end gap-2">
            <UButton color="gray" variant="outline" :disabled="!hasUnsavedChanges" @click="resetAnnouncement">
              重置未保存
            </UButton>
            <UButton color="primary" :loading="saving" @click="saveAnnouncement">
              <template #leading>
                <UIcon name="heroicons:check" />
              </template>
              保存公告
            </UButton>
          </div>
        </AdminAnnouncementSectionCard>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type {
  AnnouncementDirtyMap,
  AnnouncementSectionItem,
  AnnouncementSectionKey,
  AnnouncementState,
  AnnouncementTemplate,
} from '~/types/announcement'

definePageMeta({
  layout: 'admin',
  middleware: 'auth',
})

const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const createDefaultAnnouncement = (): AnnouncementState => ({
  id: 0,
  enabled: false,
  content: '',
  created_at: null,
  updated_at: null,
})

const cloneAnnouncement = (value: AnnouncementState): AnnouncementState => ({
  id: value.id || 0,
  enabled: Boolean(value.enabled),
  content: value.content || '',
  created_at: value.created_at || null,
  updated_at: value.updated_at || null,
})

const sectionItems: AnnouncementSectionItem[] = [
  { key: 'status', label: '状态', description: '启用与展示策略', icon: 'heroicons:power' },
  { key: 'editor', label: '编辑', description: '双栏编辑与预览', icon: 'heroicons:pencil-square' },
  { key: 'templates', label: '模板', description: '常用预设内容', icon: 'heroicons:document-duplicate' },
  { key: 'publish', label: '发布', description: '元信息与发布动作', icon: 'heroicons:rocket-launch' },
]

const announcementTemplates: AnnouncementTemplate[] = [
  {
    name: '欢迎公告',
    description: '介绍站点特性与上传优势',
    content: `<div class="space-y-3">
  <h3 class="text-lg font-bold text-stone-900 dark:text-white">欢迎来到花语阁图床</h3>
  <p class="text-stone-700 dark:text-stone-300">支持游客上传、Token 管理和画集分享，图片链接可长期访问。</p>
  <ul class="list-disc space-y-1 pl-5 text-stone-700 dark:text-stone-300">
    <li>上传流程简洁，支持批量与拖拽</li>
    <li>画集页面支持公开分享与封面展示</li>
    <li>后台可灵活管理存储、路由与访问策略</li>
  </ul>
</div>`,
  },
  {
    name: '维护通知',
    description: '系统维护窗口提醒',
    content: `<div class="space-y-3">
  <h3 class="text-lg font-bold text-rose-600 dark:text-rose-400">系统维护通知</h3>
  <p class="text-stone-700 dark:text-stone-300">为了提升稳定性，系统将在维护窗口进行升级，期间可能出现短时上传延迟。</p>
  <p class="text-stone-700 dark:text-stone-300">建议提前完成关键上传任务，维护完成后会第一时间恢复全部能力。</p>
</div>`,
  },
  {
    name: '功能更新',
    description: '发布新版功能亮点',
    content: `<div class="space-y-3">
  <h3 class="text-lg font-bold text-blue-600 dark:text-blue-400">功能更新已上线</h3>
  <p class="text-stone-700 dark:text-stone-300">本次更新包含以下内容：</p>
  <ul class="list-disc space-y-1 pl-5 text-stone-700 dark:text-stone-300">
    <li>画集首页展示机制优化，信息密度更高</li>
    <li>后台管理界面重构，移动端交互更友好</li>
    <li>Token 与登录链路稳定性提升</li>
  </ul>
</div>`,
  },
]

const loading = ref(false)
const saving = ref(false)
const initialLoaded = ref(false)
const sectionSaving = ref<Partial<Record<AnnouncementSectionKey, boolean>>>({})
const announcement = ref<AnnouncementState>(createDefaultAnnouncement())
const originalAnnouncement = ref<AnnouncementState>(createDefaultAnnouncement())

const activeSection = ref<AnnouncementSectionKey>('status')
let sectionObserver: IntersectionObserver | null = null

const contentLength = computed(() => announcement.value.content.trim().length)
const isEnabledDirty = computed(() => announcement.value.enabled !== originalAnnouncement.value.enabled)
const isContentDirty = computed(() => announcement.value.content !== originalAnnouncement.value.content)
const hasUnsavedChanges = computed(() => isEnabledDirty.value || isContentDirty.value)
const dirtyCount = computed(() => Number(isEnabledDirty.value) + Number(isContentDirty.value))

const dirtyMap = computed<AnnouncementDirtyMap>(() => ({
  status: isEnabledDirty.value,
  editor: isContentDirty.value,
  templates: false,
  publish: hasUnsavedChanges.value,
}))

const sectionDomId = (key: AnnouncementSectionKey) => `announcement-section-${key}`

const formatDate = (dateString: string | null) => {
  if (!dateString) return '--'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const extractTemplateSummary = (html: string): string => {
  const plain = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return plain.slice(0, 70) + (plain.length > 70 ? '...' : '')
}

const canSaveCurrentState = (): boolean => {
  if (!announcement.value.enabled) return true
  if (announcement.value.content.trim()) return true
  notification.warning('提示', '启用公告时内容不能为空')
  return false
}

const loadAnnouncement = async () => {
  loading.value = true
  try {
    const response = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
      credentials: 'include',
    })

    if (response?.success && response?.data) {
      const loaded = cloneAnnouncement(response.data as AnnouncementState)
      announcement.value = loaded
      originalAnnouncement.value = cloneAnnouncement(loaded)
      initialLoaded.value = true
    }
  } catch (error: any) {
    console.error('加载公告失败:', error)
    notification.error('加载失败', error?.data?.error || '无法加载公告信息')
  } finally {
    loading.value = false
  }
}

const persistAnnouncement = async () => {
  await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/announcement`, {
    method: 'POST',
    credentials: 'include',
    body: {
      enabled: announcement.value.enabled,
      content: announcement.value.content,
    },
  })
  await loadAnnouncement()
}

const saveSection = async (key: AnnouncementSectionKey) => {
  if (key === 'status' && !isEnabledDirty.value) {
    notification.info('无变更', '公告状态没有变化')
    return
  }
  if (key === 'editor' && !isContentDirty.value) {
    notification.info('无变更', '公告内容没有变化')
    return
  }
  if (!hasUnsavedChanges.value) {
    notification.info('无变更', '当前没有需要保存的内容')
    return
  }
  if (!canSaveCurrentState()) return

  sectionSaving.value[key] = true
  try {
    await persistAnnouncement()
    notification.success('已保存', key === 'status' ? '公告状态已更新' : '公告内容已更新')
  } catch (error: any) {
    console.error(`保存公告分组失败 [${key}]:`, error)
    notification.error('保存失败', error?.data?.error || error?.message || '无法保存公告')
  } finally {
    sectionSaving.value[key] = false
  }
}

const saveAnnouncement = async () => {
  if (!hasUnsavedChanges.value) {
    notification.info('无变更', '当前没有需要保存的内容')
    return
  }
  if (!canSaveCurrentState()) return

  saving.value = true
  try {
    await persistAnnouncement()
    notification.success('保存成功', '公告已更新')
  } catch (error: any) {
    console.error('保存公告失败:', error)
    notification.error('保存失败', error?.data?.error || error?.message || '无法保存公告')
  } finally {
    saving.value = false
  }
}

const resetAnnouncement = () => {
  if (!hasUnsavedChanges.value) {
    notification.info('无变更', '没有需要重置的内容')
    return
  }
  announcement.value = cloneAnnouncement(originalAnnouncement.value)
  notification.info('已重置', '未保存修改已恢复')
}

const useTemplate = (content: string) => {
  announcement.value.content = content
  notification.success('模板已应用', '你可以继续修改后保存')
}

const scrollToSection = (key: AnnouncementSectionKey) => {
  activeSection.value = key
  if (!import.meta.client) return
  const target = document.getElementById(sectionDomId(key))
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const initSectionObserver = () => {
  if (!import.meta.client) return
  sectionObserver?.disconnect()
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
    if (!visible) return
    const matched = sectionItems.find((item) => sectionDomId(item.key) === visible.target.id)
    if (matched) activeSection.value = matched.key
  }, {
    root: null,
    rootMargin: '-15% 0px -65% 0px',
    threshold: [0.2, 0.4, 0.7],
  })

  for (const item of sectionItems) {
    const el = document.getElementById(sectionDomId(item.key))
    if (el) sectionObserver.observe(el)
  }
}

onMounted(async () => {
  await loadAnnouncement()
  await nextTick()
  initSectionObserver()
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
  sectionObserver = null
})
</script>

<style scoped>
.announcement-preview-content {
  color: rgb(63 63 70);
}

.dark .announcement-preview-content {
  color: rgb(228 228 231);
}

.announcement-preview-content:deep(h1),
.announcement-preview-content:deep(h2),
.announcement-preview-content:deep(h3) {
  margin-top: 0;
}

.announcement-preview-content:deep(p),
.announcement-preview-content:deep(li) {
  line-height: 1.7;
}

.announcement-preview-content:deep(ul),
.announcement-preview-content:deep(ol) {
  margin: 0.6rem 0;
  padding-left: 1.2rem;
}
</style>
