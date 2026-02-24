/**
 * SEO 设置全局 composable
 * 使用 useState 实现跨组件共享，从公共 API 加载 SEO 配置
 */
export const useSeoSettings = () => {
  const config = useRuntimeConfig()

  const seoSettings = useState('seoSettings', () => ({
    siteName: '',
    siteDescription: '',
    siteKeywords: '',
    logoMode: 'icon' as 'icon' | 'custom',
    logoUrl: '',
    faviconUrl: '',
    ogTitle: '',
    ogDescription: '',
    ogImage: '',
    footerText: '',
    loaded: false,
  }))

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

  // 加载 SEO 设置（幂等）
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
        seoSettings.value.footerText = res.data.seo_footer_text || ''
        seoSettings.value.loaded = true
      }
    } catch {
      /* 静默失败，使用默认值 */
    }
  }

  return { seoSettings, displayName, displayDescription, displayKeywords, loadSeoSettings }
}
