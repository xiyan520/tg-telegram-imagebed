<template>
  <div class="space-y-6 sm:space-y-8">
    <section class="rounded-3xl border border-stone-200/70 bg-white/85 p-5 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/75 sm:p-7">
      <div class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-amber-600 dark:text-amber-400">Settings</p>
        <h1 class="text-2xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-4xl">站点设置</h1>
        <p class="max-w-3xl text-sm leading-relaxed text-stone-600 dark:text-stone-300 sm:text-base">
          除了基础信息，这里也负责首页编排策略。保存后会立即影响画集首页，建议先配置分区再调优展示数量。
        </p>
      </div>
    </section>

    <section v-if="loading" class="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-700 dark:bg-neutral-900">
      <div class="space-y-5">
        <div v-for="i in 6" :key="i" class="space-y-2">
          <USkeleton class="h-4 w-24" />
          <USkeleton class="h-10 w-full" />
        </div>
      </div>
    </section>

    <section v-else class="space-y-5">
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_260px]">
        <div class="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-700 dark:bg-neutral-900">
          <div class="mb-5 flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 shadow-md">
              <UIcon name="heroicons:cog-6-tooth" class="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-stone-900 dark:text-white">基础配置</h2>
              <p class="text-xs text-stone-500 dark:text-stone-400">名称、描述、开关与分页参数</p>
            </div>
          </div>

          <div class="space-y-5">
            <UFormGroup label="站点名称">
              <UInput v-model="form.gallery_site_name" placeholder="输入站点名称" />
            </UFormGroup>

            <UFormGroup label="站点描述">
              <UTextarea v-model="form.gallery_site_description" placeholder="输入站点描述" :rows="4" />
            </UFormGroup>

            <div class="flex items-center justify-between rounded-xl border border-stone-200 bg-stone-50 p-4 dark:border-stone-700 dark:bg-neutral-800/70">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">启用站点</p>
                <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">关闭后画集站点将不可访问</p>
              </div>
              <UToggle v-model="form.gallery_site_enabled" size="lg" />
            </div>

            <UFormGroup label="每页图片数">
              <UInput
                v-model.number="form.gallery_site_images_per_page"
                type="number"
                :min="1"
                :max="100"
                placeholder="20"
              />
              <template #hint>
                <span class="text-xs text-stone-500">画集详情页每页显示的图片数量（1 - 100）</span>
              </template>
            </UFormGroup>
          </div>

          <div class="mt-6 flex justify-end">
            <UButton color="primary" :loading="saving" @click="handleSaveBase">
              <template #leading>
                <UIcon name="heroicons:check" />
              </template>
              保存基础设置
            </UButton>
          </div>
        </div>

        <div class="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-700 dark:bg-neutral-900">
          <div class="mb-5 flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 shadow-md">
              <UIcon name="heroicons:squares-2x2" class="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-stone-900 dark:text-white">首页全局编排</h2>
              <p class="text-xs text-stone-500 dark:text-stone-400">Hero 与移动端承载策略</p>
            </div>
          </div>

          <div class="space-y-5">
            <UFormGroup label="Hero 来源">
              <USelect
                v-model="homeConfig.hero_mode"
                :options="heroModeOptions"
                option-attribute="label"
                value-attribute="value"
              />
            </UFormGroup>

            <UFormGroup v-if="homeConfig.hero_mode === 'manual'" label="Hero 画集 ID">
              <UInput
                v-model.number="homeConfig.hero_gallery_id"
                type="number"
                :min="1"
                placeholder="输入画集 ID"
              />
            </UFormGroup>

            <div class="grid gap-4 sm:grid-cols-2">
              <UFormGroup label="移动端每分区项数">
                <UInput
                  v-model.number="homeConfig.mobile_items_per_section"
                  type="number"
                  :min="1"
                  :max="12"
                />
              </UFormGroup>
              <UFormGroup label="桌面端每分区项数">
                <UInput
                  v-model.number="homeConfig.desktop_items_per_section"
                  type="number"
                  :min="1"
                  :max="24"
                />
              </UFormGroup>
            </div>

            <div class="flex items-center justify-between rounded-xl border border-stone-200 bg-stone-50 p-4 dark:border-stone-700 dark:bg-neutral-800/70">
              <div>
                <p class="font-medium text-stone-900 dark:text-white">显示“最近更新”条带</p>
                <p class="mt-1 text-sm text-stone-500 dark:text-stone-400">关闭后首页只展示精选与分区模块</p>
              </div>
              <UToggle v-model="homeConfig.enable_recent_strip" size="lg" />
            </div>
          </div>

          <div class="mt-6 flex justify-end">
            <UButton color="primary" :loading="homeSaving" @click="handleSaveHomeConfig">
              <template #leading>
                <UIcon name="heroicons:check" />
              </template>
              保存首页配置
            </UButton>
          </div>
        </div>

        <aside class="rounded-2xl border border-stone-200 bg-white/95 p-5 dark:border-stone-700 dark:bg-neutral-900/80">
          <h3 class="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">操作提示</h3>
          <ul class="mt-3 space-y-2 text-sm text-stone-600 dark:text-stone-300">
            <li>首页策略建议用 `hybrid`，手动精选 + 自动补位最稳。</li>
            <li>单分区 `max_items` 不建议超过 12，避免移动端信息过载。</li>
            <li>手动编排项填写画集 ID，按顺序展示。</li>
          </ul>
        </aside>
      </div>

      <div class="rounded-2xl border border-stone-200 bg-white p-5 dark:border-stone-700 dark:bg-neutral-900">
        <div class="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 class="text-lg font-semibold text-stone-900 dark:text-white">首页分区编排</h2>
            <p class="text-sm text-stone-500 dark:text-stone-400">支持分区文案、规则和手动画集顺序。</p>
          </div>
          <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" @click="loadHomeSections" />
        </div>

        <div v-if="sections.length === 0" class="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-6 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-neutral-800/50 dark:text-stone-400">
          暂无分区配置
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="section in sections"
            :key="section.section_key"
            class="rounded-xl border border-stone-200 p-4 dark:border-stone-700"
          >
            <div class="mb-3 flex items-center justify-between gap-3">
              <div>
                <p class="text-base font-semibold text-stone-900 dark:text-white">
                  {{ section.title }}
                  <span class="ml-2 text-xs text-stone-400">({{ section.section_key }})</span>
                </p>
                <p class="text-xs text-stone-500 dark:text-stone-400">
                  当前手动项：{{ section.item_ids?.length || 0 }}，自动排序：{{ section.auto_sort }}
                </p>
              </div>
              <UToggle v-model="section.enabled" />
            </div>

            <div class="grid gap-3 lg:grid-cols-2">
              <UFormGroup label="分区标题">
                <UInput v-model="section.title" />
              </UFormGroup>
              <UFormGroup label="分区副标题">
                <UInput v-model="section.subtitle" />
              </UFormGroup>
              <UFormGroup class="lg:col-span-2" label="分区描述">
                <UTextarea v-model="section.description" :rows="2" />
              </UFormGroup>
            </div>

            <div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <UFormGroup label="排序序号">
                <UInput v-model.number="section.display_order" type="number" :min="0" :max="999" />
              </UFormGroup>
              <UFormGroup label="最大展示数">
                <UInput v-model.number="section.max_items" type="number" :min="1" :max="30" />
              </UFormGroup>
              <UFormGroup label="数据来源">
                <USelect
                  v-model="section.source_mode"
                  :options="sourceModeOptions"
                  option-attribute="label"
                  value-attribute="value"
                />
              </UFormGroup>
              <UFormGroup label="自动排序">
                <USelect
                  v-model="section.auto_sort"
                  :options="autoSortOptions"
                  option-attribute="label"
                  value-attribute="value"
                />
              </UFormGroup>
            </div>

            <div class="mt-3 grid gap-3 sm:grid-cols-[220px_minmax(0,1fr)]">
              <UFormGroup label="自动时间窗（天）">
                <UInput v-model.number="section.auto_window_days" type="number" :min="0" :max="3650" />
              </UFormGroup>
              <UFormGroup label="手动画集 ID 列表">
                <UInput
                  v-model="sectionItemDraft[section.section_key]"
                  placeholder="例如：12, 18, 26"
                />
                <template #hint>
                  <span class="text-xs text-stone-500">逗号/空格分隔，按填写顺序展示。</span>
                </template>
              </UFormGroup>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-2">
              <UBadge
                v-for="item in section.items?.slice(0, 8) || []"
                :key="`sec-${section.section_key}-item-${item.id}`"
                color="gray"
                variant="soft"
              >
                #{{ item.id }} {{ item.name }}
              </UBadge>
            </div>

            <div class="mt-4 flex flex-wrap justify-end gap-2">
              <UButton
                color="gray"
                variant="soft"
                :loading="Boolean(sectionItemsSaving[section.section_key])"
                @click="handleSaveSectionItems(section)"
              >
                保存手动编排
              </UButton>
              <UButton
                color="primary"
                :loading="Boolean(sectionSaving[section.section_key])"
                @click="handleSaveSection(section)"
              >
                保存分区配置
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type {
  GallerySiteHomeConfig,
  GallerySiteHomeSection,
  GallerySiteSettings
} from '~/composables/useGallerySiteAdmin'

definePageMeta({
  layout: 'gallery-site-admin',
  middleware: 'gallery-site-admin-auth'
})

const {
  getSettings,
  updateSettings,
  getHomeConfigAdmin,
  updateHomeConfigAdmin,
  getHomeSections,
  updateHomeSection,
  replaceHomeSectionItems
} = useGallerySiteAdmin()
const notification = useNotification()

const heroModeOptions = [
  { label: '自动选择', value: 'auto' },
  { label: '指定画集', value: 'manual' }
]

const sourceModeOptions = [
  { label: '混合编排', value: 'hybrid' },
  { label: '纯手动', value: 'manual' },
  { label: '全自动', value: 'auto' }
]

const autoSortOptions = [
  { label: '最近更新', value: 'updated_desc' },
  { label: '图片数量', value: 'image_count_desc' },
  { label: '精选权重', value: 'editor_pick_desc' },
  { label: '创建时间', value: 'created_desc' },
  { label: '名称 A-Z', value: 'name_asc' }
]

const loading = ref(true)
const saving = ref(false)
const homeSaving = ref(false)
const sectionSaving = reactive<Record<string, boolean>>({})
const sectionItemsSaving = reactive<Record<string, boolean>>({})
const sectionItemDraft = reactive<Record<string, string>>({})

const form = ref<GallerySiteSettings>({
  gallery_site_name: '',
  gallery_site_description: '',
  gallery_site_enabled: true,
  gallery_site_images_per_page: 20
})

const homeConfig = ref<GallerySiteHomeConfig>({
  hero_mode: 'auto',
  hero_gallery_id: null,
  mobile_items_per_section: 4,
  desktop_items_per_section: 8,
  enable_recent_strip: true
})

const sections = ref<GallerySiteHomeSection[]>([])

const normalizeSectionDraft = (sectionList: GallerySiteHomeSection[]) => {
  for (const section of sectionList) {
    sectionItemDraft[section.section_key] = (section.item_ids || []).join(', ')
  }
}

const loadHomeSections = async () => {
  const result = await getHomeSections()
  sections.value = result
  normalizeSectionDraft(result)
}

const loadData = async () => {
  loading.value = true
  try {
    const [siteSettings, home, sectionList] = await Promise.all([
      getSettings(),
      getHomeConfigAdmin(),
      getHomeSections()
    ])
    form.value = siteSettings
    homeConfig.value = home
    sections.value = sectionList
    normalizeSectionDraft(sectionList)
  } catch (e: any) {
    notification.error('加载失败', e.message || '无法加载站点设置')
  } finally {
    loading.value = false
  }
}

const handleSaveBase = async () => {
  saving.value = true
  try {
    await updateSettings(form.value)
    notification.success('保存成功', '基础设置已更新')
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法保存基础设置')
  } finally {
    saving.value = false
  }
}

const handleSaveHomeConfig = async () => {
  homeSaving.value = true
  try {
    homeConfig.value = await updateHomeConfigAdmin(homeConfig.value)
    notification.success('保存成功', '首页全局配置已更新')
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法保存首页配置')
  } finally {
    homeSaving.value = false
  }
}

const parseSectionIds = (raw: string) => {
  const seen = new Set<number>()
  return (raw || '')
    .split(/[\s,，]+/)
    .map((it) => Number.parseInt(it, 10))
    .filter((id) => Number.isFinite(id) && id > 0)
    .filter((id) => {
      if (seen.has(id)) return false
      seen.add(id)
      return true
    })
}

const handleSaveSection = async (section: GallerySiteHomeSection) => {
  sectionSaving[section.section_key] = true
  try {
    const updated = await updateHomeSection(section.section_key, {
      title: section.title,
      subtitle: section.subtitle,
      description: section.description,
      enabled: section.enabled,
      display_order: section.display_order,
      max_items: section.max_items,
      source_mode: section.source_mode,
      auto_sort: section.auto_sort,
      auto_window_days: section.auto_window_days
    })
    Object.assign(section, updated)
    notification.success('保存成功', `${updated.title} 配置已更新`)
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法更新分区配置')
  } finally {
    sectionSaving[section.section_key] = false
  }
}

const handleSaveSectionItems = async (section: GallerySiteHomeSection) => {
  sectionItemsSaving[section.section_key] = true
  try {
    const galleryIds = parseSectionIds(sectionItemDraft[section.section_key] || '')
    await replaceHomeSectionItems(section.section_key, galleryIds)
    await loadHomeSections()
    notification.success('保存成功', `${section.title} 手动编排已更新`)
  } catch (e: any) {
    notification.error('保存失败', e.message || '无法更新手动编排')
  } finally {
    sectionItemsSaving[section.section_key] = false
  }
}

onMounted(loadData)
</script>
