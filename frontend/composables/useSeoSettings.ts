/**
 * SEO 设置全局 composable
 * 使用 useState 实现跨组件共享，从公共 API 加载 SEO 配置
 * 支持 localStorage 缓存，消除刷新时的标题闪烁
 */

const SEO_CACHE_KEY = 'seo_settings_cache'

/** 从 localStorage 恢复缓存 */
function _readCache() {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem(SEO_CACHE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return null
}

/** 写入 localStorage 缓存 */
function _writeCache(data: Record<string, any>) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(SEO_CACHE_KEY, JSON.stringify(data))
  } catch { /* ignore */ }
}

export const useSeoSettings = () => {
  const config = useRuntimeConfig()

  const seoSettings = useState('seoSettings', () => {
    // 优先从 localStorage 恢复，避免刷新时标题闪烁
    const cached = _readCache()
    return {
      siteName: cached?.siteName || '',
      siteDescription: cached?.siteDescription || '',
      siteKeywords: cached?.siteKeywords || '',
      logoMode: (cached?.logoMode || 'icon') as 'icon' | 'custom',
      logoUrl: cached?.logoUrl || '',
      faviconUrl: cached?.faviconUrl || '',
      ogTitle: cached?.ogTitle || '',
      ogDescription: cached?.ogDescription || '',
      ogImage: cached?.ogImage || '',
      ogSiteName: cached?.ogSiteName || '',
      ogType: (cached?.ogType || 'website') as 'website' | 'article' | 'profile',
      canonicalUrl: cached?.canonicalUrl || '',
      robotsIndex: cached?.robotsIndex !== false,
      robotsFollow: cached?.robotsFollow !== false,
      twitterCardType: (cached?.twitterCardType || 'summary_large_image') as 'summary' | 'summary_large_image',
      twitterSite: cached?.twitterSite || '',
      twitterCreator: cached?.twitterCreator || '',
      author: cached?.author || '',
      themeColor: cached?.themeColor || '',
      defaultLocale: cached?.defaultLocale || 'zh_CN',
      footerText: cached?.footerText || '',
      loaded: false,
    }
  })

  // 计算属性：带默认值的站名
  const displayName = computed(() => seoSettings.value.siteName || '图床 Pro')

  // 计算属性：带默认值的描述
  const displayDescription = computed(() =>
    seoSettings.value.siteDescription || '专业的图片托管服务，基于Telegram云存储，支持Cloudflare CDN全球加速'
  )

  // 计算属性：带默认值的关键词
  const displayKeywords = computed(() =>
    seoSettings.value.siteKeywords || '图床,免费图床,Telegram,云存储,CDN加速,图片托管'
  )

  // 加载 SEO 设置（幂等），成功后写入 localStorage 缓存
  const loadSeoSettings = async (force = false) => {
    if (seoSettings.value.loaded && !force) return
    try {
      const res = await $fetch<any>(`${config.public.apiBase}/api/public/settings`)
      if (res.success && res.data) {
        seoSettings.value.siteName = res.data.seo_site_name || ''
        seoSettings.value.siteDescription = res.data.seo_site_description || ''
        seoSettings.value.siteKeywords = res.data.seo_site_keywords || ''
        seoSettings.value.logoMode = res.data.seo_logo_mode || 'icon'
        seoSettings.value.logoUrl = res.data.seo_logo_url || ''
        seoSettings.value.faviconUrl = res.data.seo_favicon_url || ''
        seoSettings.value.ogTitle = res.data.seo_og_title || ''
        seoSettings.value.ogDescription = res.data.seo_og_description || ''
        seoSettings.value.ogImage = res.data.seo_og_image || ''
        seoSettings.value.ogSiteName = res.data.seo_og_site_name || ''
        seoSettings.value.ogType = res.data.seo_og_type || 'website'
        seoSettings.value.canonicalUrl = res.data.seo_canonical_url || ''
        seoSettings.value.robotsIndex = res.data.seo_robots_index !== false
        seoSettings.value.robotsFollow = res.data.seo_robots_follow !== false
        seoSettings.value.twitterCardType = res.data.seo_twitter_card_type || 'summary_large_image'
        seoSettings.value.twitterSite = res.data.seo_twitter_site || ''
        seoSettings.value.twitterCreator = res.data.seo_twitter_creator || ''
        seoSettings.value.author = res.data.seo_author || ''
        seoSettings.value.themeColor = res.data.seo_theme_color || ''
        seoSettings.value.defaultLocale = res.data.seo_default_locale || 'zh_CN'
        seoSettings.value.footerText = res.data.seo_footer_text || ''
        seoSettings.value.loaded = true
        // 缓存到 localStorage，下次刷新可立即使用
        _writeCache({
          siteName: seoSettings.value.siteName,
          siteDescription: seoSettings.value.siteDescription,
          siteKeywords: seoSettings.value.siteKeywords,
          logoMode: seoSettings.value.logoMode,
          logoUrl: seoSettings.value.logoUrl,
          faviconUrl: seoSettings.value.faviconUrl,
          ogTitle: seoSettings.value.ogTitle,
          ogDescription: seoSettings.value.ogDescription,
          ogImage: seoSettings.value.ogImage,
          ogSiteName: seoSettings.value.ogSiteName,
          ogType: seoSettings.value.ogType,
          canonicalUrl: seoSettings.value.canonicalUrl,
          robotsIndex: seoSettings.value.robotsIndex,
          robotsFollow: seoSettings.value.robotsFollow,
          twitterCardType: seoSettings.value.twitterCardType,
          twitterSite: seoSettings.value.twitterSite,
          twitterCreator: seoSettings.value.twitterCreator,
          author: seoSettings.value.author,
          themeColor: seoSettings.value.themeColor,
          defaultLocale: seoSettings.value.defaultLocale,
          footerText: seoSettings.value.footerText,
        })
      }
    } catch {
      /* 静默失败，使用缓存或默认值 */
    }
  }

  return { seoSettings, displayName, displayDescription, displayKeywords, loadSeoSettings }
}
