<template>
  <div class="pb-14 sm:pb-20">
    <HeroPanel
      :site-name="siteName"
      :site-description="siteDescription"
      :stats="stats"
      :primary="heroPrimary"
      :loading="loading"
    />

    <div class="mx-auto mt-10 max-w-7xl space-y-12 px-4 sm:mt-14 sm:space-y-16 sm:px-6 lg:px-8">
      <section class="space-y-5">
        <SectionHeader
          :eyebrow="featuredEyebrow"
          :title="featuredTitle"
          :description="featuredDescription"
          action-to="/gallery-site/galleries"
          action-label="查看全部画集"
        />
        <FeaturedRail :items="featuredRailItems" :loading="loading" />
      </section>

      <section v-if="loading || categoryBuckets.length > 0" class="space-y-5">
        <SectionHeader
          eyebrow="Curated Sections"
          title="分区浏览"
          description="按更新节奏、内容体量和策展推荐拆分，浏览效率和沉浸感两边都不掉。"
        />
        <CategoryShowcase :buckets="categoryBuckets" :loading="loading" />
      </section>

      <section v-if="showRecentStrip" class="space-y-5">
        <SectionHeader
          eyebrow="Latest Activity"
          title="最近更新"
          description="横向时间条带，随手滑一滑就能看到近期新增内容。"
        />
        <RecentStrip :items="recentItems" :loading="loading" />
      </section>

      <section v-if="loadError && !hasContent" class="rounded-2xl border border-red-200 bg-red-50 p-6 text-center dark:border-red-900/40 dark:bg-red-950/20">
        <UIcon name="heroicons:exclamation-circle" class="mx-auto h-9 w-9 text-red-500" />
        <p class="mt-3 text-sm text-red-700 dark:text-red-300">首页数据暂时加载失败，请稍后刷新重试。</p>
      </section>

      <section v-else-if="!loading && !hasContent" class="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-8 text-center dark:border-stone-700 dark:bg-neutral-900/70">
        <UIcon name="heroicons:photo" class="mx-auto h-12 w-12 text-stone-300 dark:text-stone-600" />
        <p class="mt-3 text-stone-500 dark:text-stone-400">当前还没有公开画集内容。</p>
        <NuxtLink
          to="/gallery-site/galleries"
          class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-amber-600 transition-colors hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
        >
          前往画集列表
          <UIcon name="heroicons:arrow-right" class="h-4 w-4" />
        </NuxtLink>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GalleryHomePayload, GallerySiteItem, GallerySiteStats } from '~/composables/useGallerySite'
import CategoryShowcase from '~/components/gallery-site/home/CategoryShowcase.vue'
import FeaturedRail from '~/components/gallery-site/home/FeaturedRail.vue'
import HeroPanel from '~/components/gallery-site/home/HeroPanel.vue'
import RecentStrip from '~/components/gallery-site/home/RecentStrip.vue'
import SectionHeader from '~/components/gallery-site/home/SectionHeader.vue'

interface HomeBucket {
  id: string
  title: string
  description: string
  items: GallerySiteItem[]
}

definePageMeta({ layout: 'gallery-site' })

const { getHomeConfig, getFeatured, getStats, getGalleries } = useGallerySiteApi()

const siteMode = useState<{ mode: string; site_name?: string; site_description?: string } | null>('gallery-site-mode', () => null)
const siteName = computed(() => siteMode.value?.site_name || '画集')
const siteDescription = computed(() => siteMode.value?.site_description || '精选图片画集')

const loading = ref(true)
const loadError = ref<string | null>(null)
const homePayload = ref<GalleryHomePayload | null>(null)
const featured = ref<GallerySiteItem[]>([])
const galleries = ref<GallerySiteItem[]>([])
const stats = ref<GallerySiteStats | null>(null)

const mergeUniqueById = (...groups: GallerySiteItem[][]) => {
  const map = new Map<number, GallerySiteItem>()
  for (const item of groups.flat()) {
    if (!map.has(item.id)) map.set(item.id, item)
  }
  return Array.from(map.values())
}

const sortByUpdatedDesc = (items: GallerySiteItem[]) => {
  return [...items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
}

const hasContent = computed(() => {
  if (homePayload.value) {
    return homePayload.value.sections.some((section) => section.items?.length) || homePayload.value.recent_items.length > 0
  }
  return featured.value.length > 0 || galleries.value.length > 0
})
const mergedItems = computed(() => mergeUniqueById(featured.value, galleries.value))
const featuredSection = computed(() => {
  if (!homePayload.value) return null
  return homePayload.value.sections.find((section) => section.section_key === 'featured') || homePayload.value.sections[0] || null
})
const heroPrimary = computed(() => homePayload.value?.hero || featured.value[0] || galleries.value[0] || null)
const showRecentStrip = computed(() => homePayload.value?.config.enable_recent_strip ?? true)
const featuredTitle = computed(() => featuredSection.value?.title || '编辑精选')
const featuredEyebrow = computed(() => featuredSection.value?.subtitle || 'Editors Pick')
const featuredDescription = computed(() => featuredSection.value?.description || '先看最有代表性的画集，快速建立站点内容风格。')

const featuredRailItems = computed(() => {
  if (featuredSection.value?.items?.length) {
    return featuredSection.value.items.slice(0, Math.max(1, homePayload.value?.config.desktop_items_per_section || 8))
  }
  const source = featured.value.length ? featured.value : galleries.value
  return mergeUniqueById(source).slice(0, 6)
})

const recentItems = computed(() => {
  if (homePayload.value) {
    return homePayload.value.recent_items.slice(0, Math.max(6, homePayload.value.config.desktop_items_per_section))
  }
  return sortByUpdatedDesc(mergedItems.value).slice(0, 8)
})

const categoryBuckets = computed<HomeBucket[]>(() => {
  if (homePayload.value) {
    return homePayload.value.sections
      .filter((section) => section.section_key !== 'featured')
      .map((section) => ({
        id: section.section_key,
        title: section.title,
        description: section.description || section.subtitle || '',
        items: section.items || []
      }))
      .filter((bucket) => bucket.items.length > 0)
  }

  const merged = mergedItems.value
  const curated = featuredRailItems.value.slice(0, 4)
  const latest = sortByUpdatedDesc(merged).slice(0, 4)
  const highVolume = [...merged].sort((a, b) => b.image_count - a.image_count).slice(0, 4)

  return [
    {
      id: 'curated',
      title: '策展精选',
      description: '挑一组最具代表性的画集，快速进入内容氛围。',
      items: curated
    },
    {
      id: 'latest',
      title: '最近更新',
      description: '优先查看最近活跃画集，追新内容不掉队。',
      items: latest
    },
    {
      id: 'high-volume',
      title: '高内容量',
      description: '每组都更耐看，适合深度浏览。',
      items: highVolume
    }
  ].filter((bucket) => bucket.items.length > 0)
})

onMounted(async () => {
  const [homeResult, statsResult] = await Promise.allSettled([
    getHomeConfig(),
    getStats()
  ])

  if (homeResult.status === 'fulfilled') {
    homePayload.value = homeResult.value
  } else {
    console.error('加载首页编排失败，回退旧逻辑:', homeResult.reason)
  }

  if (statsResult.status === 'fulfilled') {
    stats.value = statsResult.value
  } else {
    console.error('加载统计数据失败:', statsResult.reason)
  }

  let fallbackRejected = 0
  if (!homePayload.value) {
    const [featuredResult, galleriesResult] = await Promise.allSettled([
      getFeatured(6),
      getGalleries(1, 20)
    ])

    if (featuredResult.status === 'fulfilled') {
      featured.value = featuredResult.value
    } else {
      fallbackRejected++
      console.error('加载精选画集失败:', featuredResult.reason)
    }

    if (galleriesResult.status === 'fulfilled') {
      galleries.value = galleriesResult.value.items
    } else {
      fallbackRejected++
      console.error('加载画集列表失败:', galleriesResult.reason)
    }
  }

  if (!homePayload.value && fallbackRejected >= 2 && statsResult.status === 'rejected') {
    loadError.value = 'all-failed'
  }

  loading.value = false
})
</script>
