<template>
  <div class="relative space-y-6 pb-10">
    <div class="pointer-events-none absolute -top-20 right-0 h-44 w-44 rounded-full bg-amber-200/30 blur-3xl dark:bg-amber-700/15" />
    <div class="pointer-events-none absolute top-56 -left-10 h-40 w-40 rounded-full bg-orange-200/25 blur-3xl dark:bg-orange-700/10" />

    <AdminPageHeader
      title="SEO 设置"
      eyebrow="Config"
      icon="heroicons:magnifying-glass"
      description="配置网站元信息、社交分享、抓取策略与页脚展示"
    >
      <template #actions>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadSettings"
        >
          刷新
        </UButton>
        <UButton
          color="gray"
          variant="outline"
          icon="heroicons:arrow-uturn-left"
          :disabled="!isAnyDirty"
          @click="resetSettings"
        >
          重置未保存
        </UButton>
        <UButton color="primary" icon="heroicons:check" :loading="saving" @click="saveAllSettings">
          保存全部
          <UBadge v-if="dirtyCount > 0" color="amber" variant="solid" size="xs" class="ml-1.5">
            {{ dirtyCount }}
          </UBadge>
        </UButton>
      </template>
    </AdminPageHeader>

    <div v-if="loading && !settingsLoaded" class="flex justify-center py-12">
      <div class="h-12 w-12 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
    </div>

    <template v-else>
      <div class="space-y-4">
        <AdminSeoTopNav
          class="hidden lg:block"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />
        <AdminSeoMobileNavDrawer
          class="lg:hidden"
          :items="sectionItems"
          :active-key="activeSection"
          :dirty-map="dirtyMap"
          @select="scrollToSection"
        />

        <AdminSeoSectionCard
          :id="sectionDomId('basic')"
          title="基础信息"
          description="网站名称、描述、关键词、作者与默认语言"
          icon="heroicons:globe-alt"
          :dirty="Boolean(dirtyMap.basic)"
          :saving="Boolean(sectionSaving.basic)"
          @save="saveSection('basic')"
        >
          <UCard>
            <div class="grid gap-4 lg:grid-cols-2">
              <UFormGroup label="网站名称" hint="用于标题、导航和页脚默认文案">
                <UInput v-model="form.seo_site_name" placeholder="图床 Pro" />
              </UFormGroup>
              <UFormGroup label="默认 Locale" hint="示例：zh_CN、en_US">
                <UInput v-model="form.seo_default_locale" placeholder="zh_CN" />
              </UFormGroup>
              <UFormGroup label="网站描述" hint="用于 meta description" class="lg:col-span-2">
                <UTextarea
                  v-model="form.seo_site_description"
                  :rows="3"
                  placeholder="专业的图片托管服务，基于 Telegram 云存储，支持 Cloudflare CDN 全球加速"
                />
              </UFormGroup>
              <UFormGroup label="网站关键词" hint="逗号分隔，用于 meta keywords" class="lg:col-span-2">
                <UInput v-model="form.seo_site_keywords" placeholder="图床,免费图床,Telegram,云存储,CDN 加速,图片托管" />
              </UFormGroup>
              <UFormGroup label="作者" hint="用于 meta author" class="lg:col-span-2">
                <UInput v-model="form.seo_author" placeholder="图床团队" />
              </UFormGroup>
            </div>
          </UCard>
        </AdminSeoSectionCard>

        <AdminSeoSectionCard
          :id="sectionDomId('branding')"
          title="品牌与图标"
          description="Logo、Favicon 与主题色"
          icon="heroicons:paint-brush"
          :dirty="Boolean(dirtyMap.branding)"
          :saving="Boolean(sectionSaving.branding)"
          @save="saveSection('branding')"
        >
          <UCard>
            <div class="space-y-4">
              <UFormGroup label="Logo 模式">
                <div class="flex flex-wrap gap-4">
                  <URadio v-model="form.seo_logo_mode" value="icon" label="默认图标" />
                  <URadio v-model="form.seo_logo_mode" value="custom" label="自定义图片" />
                </div>
              </UFormGroup>

              <UFormGroup v-if="form.seo_logo_mode === 'custom'" label="Logo 图片 URL">
                <UInput v-model="form.seo_logo_url" placeholder="https://example.com/logo.png" />
              </UFormGroup>

              <div
                v-if="form.seo_logo_mode === 'custom' && form.seo_logo_url"
                class="flex items-center gap-4 rounded-xl border border-stone-200 bg-stone-50/80 p-3 dark:border-neutral-700 dark:bg-neutral-800/70"
              >
                <span class="text-xs text-stone-500 dark:text-stone-400">Logo 预览</span>
                <img
                  :src="form.seo_logo_url"
                  alt="Logo 预览"
                  class="h-10 w-10 rounded-lg object-contain"
                  @error="hideBrokenImage"
                >
              </div>

              <UFormGroup label="Favicon URL" hint="留空使用默认图标">
                <UInput v-model="form.seo_favicon_url" placeholder="https://example.com/favicon.ico" />
              </UFormGroup>

              <UFormGroup label="主题色" hint="HEX 格式，例如 #f59e0b">
                <div class="flex flex-wrap items-center gap-3">
                  <UInput v-model="form.seo_theme_color" class="min-w-[220px] flex-1" placeholder="#f59e0b" />
                  <span
                    v-if="themeColorError"
                    class="text-xs text-rose-500"
                  >{{ themeColorError }}</span>
                  <span
                    v-else-if="form.seo_theme_color"
                    class="inline-flex items-center gap-2 rounded-full border border-stone-200 px-2.5 py-1 text-xs text-stone-600 dark:border-neutral-700 dark:text-stone-300"
                  >
                    <span class="h-2.5 w-2.5 rounded-full border border-stone-300 dark:border-neutral-600" :style="{ backgroundColor: form.seo_theme_color }" />
                    {{ form.seo_theme_color }}
                  </span>
                </div>
              </UFormGroup>
            </div>
          </UCard>
        </AdminSeoSectionCard>

        <AdminSeoSectionCard
          :id="sectionDomId('social')"
          title="社交与 Open Graph"
          description="Open Graph 与 Twitter Card 传播配置"
          icon="heroicons:share"
          :dirty="Boolean(dirtyMap.social)"
          :saving="Boolean(sectionSaving.social)"
          @save="saveSection('social')"
        >
          <UCard>
            <div class="grid gap-4 lg:grid-cols-2">
              <UFormGroup label="OG 标题" hint="留空自动使用网站名称">
                <UInput v-model="form.seo_og_title" :placeholder="form.seo_site_name || '图床 Pro'" />
              </UFormGroup>
              <UFormGroup label="OG 站点名称" hint="留空自动使用网站名称">
                <UInput v-model="form.seo_og_site_name" :placeholder="form.seo_site_name || '图床 Pro'" />
              </UFormGroup>
              <UFormGroup label="OG 描述" hint="留空自动使用网站描述" class="lg:col-span-2">
                <UTextarea v-model="form.seo_og_description" :rows="3" :placeholder="form.seo_site_description || '专业的图片托管服务'" />
              </UFormGroup>
              <UFormGroup label="OG 图片 URL" hint="分享卡片大图">
                <UInput v-model="form.seo_og_image" placeholder="https://example.com/og-image.png" />
              </UFormGroup>
              <UFormGroup label="OG 类型">
                <USelect
                  v-model="form.seo_og_type"
                  :options="ogTypeOptions"
                  option-attribute="label"
                  value-attribute="value"
                />
              </UFormGroup>
              <UFormGroup label="Twitter Card 类型">
                <USelect
                  v-model="form.seo_twitter_card_type"
                  :options="twitterCardTypeOptions"
                  option-attribute="label"
                  value-attribute="value"
                />
              </UFormGroup>
              <UFormGroup label="Twitter 站点账号" hint="示例：@your_site">
                <UInput v-model="form.seo_twitter_site" placeholder="@your_site" />
              </UFormGroup>
              <UFormGroup label="Twitter 作者账号" hint="示例：@your_creator">
                <UInput v-model="form.seo_twitter_creator" placeholder="@your_creator" />
              </UFormGroup>
            </div>
          </UCard>
        </AdminSeoSectionCard>

        <AdminSeoSectionCard
          :id="sectionDomId('crawler')"
          title="搜索抓取与索引"
          description="Canonical 与 robots 抓取策略"
          icon="heroicons:cpu-chip"
          :dirty="Boolean(dirtyMap.crawler)"
          :saving="Boolean(sectionSaving.crawler)"
          @save="saveSection('crawler')"
        >
          <UCard>
            <div class="space-y-4">
              <UFormGroup label="Canonical URL" hint="留空时按当前页面 URL 输出">
                <UInput v-model="form.seo_canonical_url" placeholder="https://your-domain.com" />
              </UFormGroup>
              <p v-if="canonicalUrlError" class="text-xs text-rose-500">{{ canonicalUrlError }}</p>

              <div class="grid gap-4 md:grid-cols-2">
                <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/70">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-stone-900 dark:text-white">允许被索引</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">对应 robots: index / noindex</p>
                    </div>
                    <UToggle v-model="form.seo_robots_index" />
                  </div>
                </div>
                <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 dark:border-neutral-700/80 dark:bg-neutral-800/70">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-stone-900 dark:text-white">允许跟踪链接</p>
                      <p class="text-xs text-stone-500 dark:text-stone-400">对应 robots: follow / nofollow</p>
                    </div>
                    <UToggle v-model="form.seo_robots_follow" />
                  </div>
                </div>
              </div>

              <div class="rounded-xl border border-stone-200/80 bg-stone-50/80 p-3 text-xs text-stone-500 dark:border-neutral-700/80 dark:bg-neutral-800/70 dark:text-stone-400">
                当前 robots 输出：
                <span class="font-semibold text-stone-700 dark:text-stone-200">{{ previewRobots }}</span>
              </div>
            </div>
          </UCard>
        </AdminSeoSectionCard>

        <AdminSeoSectionCard
          :id="sectionDomId('footer_preview')"
          title="页脚与综合预览"
          description="页脚文案与最终 meta 输出预览"
          icon="heroicons:eye"
          :dirty="Boolean(dirtyMap.footer_preview)"
          :saving="Boolean(sectionSaving.footer_preview)"
          @save="saveSection('footer_preview')"
        >
          <UCard>
            <div class="space-y-4">
              <UFormGroup label="页脚文字" hint="留空使用默认格式「© 年份 网站名称」">
                <UInput v-model="form.seo_footer_text" placeholder="© 2026 图床 Pro" />
              </UFormGroup>

              <AdminSeoPreviewPanel
                :title="previewTitle"
                :description="previewDescription"
                :canonical="previewCanonical"
                :robots="previewRobots"
                :locale="previewLocale"
                :footer="previewFooter"
                :card-type="previewTwitterCard"
                :og-image="form.seo_og_image"
                :theme-color="form.seo_theme_color"
              />
            </div>
          </UCard>
        </AdminSeoSectionCard>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'
import type { AdminSeoSettings, SeoDirtyMap, SeoSectionItem, SeoSectionKey } from '~/types/admin-seo'

definePageMeta({ layout: 'admin' })

const config = useRuntimeConfig()
const toast = useLightToast()
const { loadSeoSettings } = useSeoSettings()

const loading = ref(false)
const saving = ref(false)
const settingsLoaded = ref(false)

const sectionItems: SeoSectionItem[] = [
  { key: 'basic', label: '基础信息', description: '站点名称与基础元信息', icon: 'heroicons:globe-alt' },
  { key: 'branding', label: '品牌图标', description: 'Logo / Favicon / 主题色', icon: 'heroicons:paint-brush' },
  { key: 'social', label: '社交分享', description: 'OG 与 Twitter Card', icon: 'heroicons:share' },
  { key: 'crawler', label: '抓取策略', description: 'Canonical 与 robots', icon: 'heroicons:cpu-chip' },
  { key: 'footer_preview', label: '页脚预览', description: '页脚文字和最终预览', icon: 'heroicons:eye' },
]

const sectionFieldGroups: Record<SeoSectionKey, Array<keyof AdminSeoSettings>> = {
  basic: ['seo_site_name', 'seo_site_description', 'seo_site_keywords', 'seo_author', 'seo_default_locale'],
  branding: ['seo_logo_mode', 'seo_logo_url', 'seo_favicon_url', 'seo_theme_color'],
  social: [
    'seo_og_title',
    'seo_og_description',
    'seo_og_image',
    'seo_og_site_name',
    'seo_og_type',
    'seo_twitter_card_type',
    'seo_twitter_site',
    'seo_twitter_creator',
  ],
  crawler: ['seo_canonical_url', 'seo_robots_index', 'seo_robots_follow'],
  footer_preview: ['seo_footer_text'],
}

const buildDefaultForm = (): AdminSeoSettings => ({
  seo_site_name: '',
  seo_site_description: '',
  seo_site_keywords: '',
  seo_logo_mode: 'icon',
  seo_logo_url: '',
  seo_favicon_url: '',
  seo_og_title: '',
  seo_og_description: '',
  seo_og_image: '',
  seo_og_site_name: '',
  seo_og_type: 'website',
  seo_canonical_url: '',
  seo_robots_index: true,
  seo_robots_follow: true,
  seo_twitter_card_type: 'summary_large_image',
  seo_twitter_site: '',
  seo_twitter_creator: '',
  seo_author: '',
  seo_theme_color: '',
  seo_default_locale: 'zh_CN',
  seo_footer_text: '',
})

const form = ref<AdminSeoSettings>(buildDefaultForm())
const originalForm = ref<AdminSeoSettings | null>(null)

const activeSection = ref<SeoSectionKey>('basic')
const sectionSaving = ref<Partial<Record<SeoSectionKey, boolean>>>({})

const ogTypeOptions = [
  { value: 'website', label: 'website' },
  { value: 'article', label: 'article' },
  { value: 'profile', label: 'profile' },
]

const twitterCardTypeOptions = [
  { value: 'summary_large_image', label: 'summary_large_image（大图）' },
  { value: 'summary', label: 'summary（小图）' },
]

const cloneForm = (value: AdminSeoSettings): AdminSeoSettings => JSON.parse(JSON.stringify(value)) as AdminSeoSettings

const stableStringify = (value: any): string => {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  const keys = Object.keys(value).sort()
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`
}

const pick = (source: AdminSeoSettings, keys: Array<keyof AdminSeoSettings>) => {
  const out: Partial<AdminSeoSettings> = {}
  for (const key of keys) out[key] = source[key]
  return out
}

const dirtyMap = computed<SeoDirtyMap>(() => {
  const map: SeoDirtyMap = {}
  if (!originalForm.value) {
    for (const item of sectionItems) {
      map[item.key] = false
    }
    return map
  }

  for (const [sectionKey, fields] of Object.entries(sectionFieldGroups) as Array<[SeoSectionKey, Array<keyof AdminSeoSettings>]>) {
    map[sectionKey] = stableStringify(pick(form.value, fields)) !== stableStringify(pick(originalForm.value, fields))
  }

  return map
})

const dirtyCount = computed(() => Object.values(dirtyMap.value).filter(Boolean).length)
const isAnyDirty = computed(() => dirtyCount.value > 0)

const previewTitle = computed(() => form.value.seo_og_title || form.value.seo_site_name || '图床 Pro')
const previewDescription = computed(() => form.value.seo_og_description || form.value.seo_site_description || '专业的图片托管服务')
const previewCanonical = computed(() => {
  const val = form.value.seo_canonical_url.trim()
  if (val) return val
  if (import.meta.client) return window.location.origin
  return 'https://example.com'
})
const previewRobots = computed(() => `${form.value.seo_robots_index ? 'index' : 'noindex'},${form.value.seo_robots_follow ? 'follow' : 'nofollow'}`)
const previewLocale = computed(() => form.value.seo_default_locale || 'zh_CN')
const previewTwitterCard = computed(() => form.value.seo_twitter_card_type || 'summary_large_image')
const previewFooter = computed(() => {
  if (form.value.seo_footer_text.trim()) return form.value.seo_footer_text.trim()
  return `© ${new Date().getFullYear()} ${form.value.seo_site_name || '图床 Pro'}`
})

const themeColorError = computed(() => {
  const value = form.value.seo_theme_color.trim()
  if (!value) return ''
  return /^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{6})$/.test(value) ? '' : '主题色格式无效，示例：#f59e0b'
})

const canonicalUrlError = computed(() => {
  const value = form.value.seo_canonical_url.trim()
  if (!value) return ''
  if (value.startsWith('http://') || value.startsWith('https://')) return ''
  return 'Canonical URL 建议使用 http:// 或 https:// 开头'
})

const sectionDomId = (key: SeoSectionKey) => `seo-section-${key}`

const normalizeFormFromResponse = (data: any): AdminSeoSettings => ({
  ...buildDefaultForm(),
  seo_site_name: data?.seo_site_name || '',
  seo_site_description: data?.seo_site_description || '',
  seo_site_keywords: data?.seo_site_keywords || '',
  seo_logo_mode: data?.seo_logo_mode === 'custom' ? 'custom' : 'icon',
  seo_logo_url: data?.seo_logo_url || '',
  seo_favicon_url: data?.seo_favicon_url || '',
  seo_og_title: data?.seo_og_title || '',
  seo_og_description: data?.seo_og_description || '',
  seo_og_image: data?.seo_og_image || '',
  seo_og_site_name: data?.seo_og_site_name || '',
  seo_og_type: ['website', 'article', 'profile'].includes(data?.seo_og_type) ? data.seo_og_type : 'website',
  seo_canonical_url: data?.seo_canonical_url || '',
  seo_robots_index: data?.seo_robots_index !== false,
  seo_robots_follow: data?.seo_robots_follow !== false,
  seo_twitter_card_type: ['summary', 'summary_large_image'].includes(data?.seo_twitter_card_type)
    ? data.seo_twitter_card_type
    : 'summary_large_image',
  seo_twitter_site: data?.seo_twitter_site || '',
  seo_twitter_creator: data?.seo_twitter_creator || '',
  seo_author: data?.seo_author || '',
  seo_theme_color: data?.seo_theme_color || '',
  seo_default_locale: data?.seo_default_locale || 'zh_CN',
  seo_footer_text: data?.seo_footer_text || '',
})

const loadSettings = async () => {
  loading.value = true
  try {
    const res = await $fetch<any>(`${config.public.apiBase}/api/admin/system/settings`, {
      credentials: 'include',
    })

    if (res?.success && res.data) {
      form.value = normalizeFormFromResponse(res.data)
      originalForm.value = cloneForm(form.value)
      settingsLoaded.value = true
    }
  } catch (error: any) {
    toast.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

const saveSettings = async (fields?: Array<keyof AdminSeoSettings>) => {
  const body = fields && fields.length > 0 ? pick(form.value, fields) : { ...form.value }

  const res = await $fetch<any>(`${config.public.apiBase}/api/admin/system/settings`, {
    method: 'PUT',
    credentials: 'include',
    body,
  })

  if (!res?.success) {
    throw new Error(res?.error || '保存失败')
  }

  const normalized = normalizeFormFromResponse(res?.data || form.value)
  form.value = normalized

  if (!originalForm.value || !fields || fields.length === 0) {
    originalForm.value = cloneForm(normalized)
  } else {
    const merged = cloneForm(originalForm.value)
    for (const field of fields) {
      merged[field] = normalized[field]
    }
    originalForm.value = merged
  }

  await loadSeoSettings(true)
}

const saveSection = async (sectionKey: SeoSectionKey) => {
  sectionSaving.value[sectionKey] = true
  try {
    const fields = sectionFieldGroups[sectionKey]
    await saveSettings(fields)
    toast.success(`已保存「${sectionItems.find((item) => item.key === sectionKey)?.label || '分组'}」`)
  } catch (error: any) {
    toast.error(error?.message || '保存失败')
  } finally {
    sectionSaving.value[sectionKey] = false
  }
}

const saveAllSettings = async () => {
  saving.value = true
  try {
    await saveSettings()
    toast.success('SEO 设置已保存')
  } catch (error: any) {
    toast.error(error?.message || '保存设置失败')
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  if (!originalForm.value) return
  form.value = cloneForm(originalForm.value)
  toast.info('已重置未保存内容')
}

const scrollToSection = (key: SeoSectionKey) => {
  activeSection.value = key
  if (!import.meta.client) return
  const target = document.getElementById(sectionDomId(key))
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const hideBrokenImage = (event: Event) => {
  const target = event.target as HTMLImageElement | null
  if (target) {
    target.style.display = 'none'
  }
}

let sectionObserver: IntersectionObserver | null = null

const initSectionObserver = () => {
  if (!import.meta.client) return

  sectionObserver?.disconnect()
  sectionObserver = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]

    if (!visible) return

    const matched = sectionItems.find((item) => sectionDomId(item.key) === visible.target.id)
    if (matched) {
      activeSection.value = matched.key
    }
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
  await loadSettings()
  await nextTick()
  initSectionObserver()
})

onBeforeUnmount(() => {
  sectionObserver?.disconnect()
  sectionObserver = null
})
</script>
