import type { SiteModeInfo } from '~/composables/useGallerySite'

/**
 * 画集域名检测全局中间件
 * - 画集域名：非 /gallery-site/* 和 /image/* 路径重定向到 /gallery-site/
 * - 非画集域名：/gallery-site/* 路径正常访问（不再阻止）
 * - 缓存检测结果到 useState 避免重复请求
 */
export default defineNuxtRouteMiddleware(async (to) => {
  // 仅在客户端执行（ssr: false）
  if (!import.meta.client) return

  // 获取缓存的站点模式
  const siteMode = useState<SiteModeInfo | null>('gallery-site-mode', () => null)
  const siteModeChecked = useState<boolean>('gallery-site-mode-checked', () => false)

  // 首次访问时检测站点模式
  if (!siteModeChecked.value) {
    try {
      const { getSiteMode } = useGallerySiteApi()
      siteMode.value = await getSiteMode()
    } catch (e) {
      console.error('站点模式检测失败:', e)
      siteMode.value = { mode: 'default' }
    }
    siteModeChecked.value = true
  }

  const isGalleryMode = siteMode.value?.mode === 'gallery'
  const path = to.path

  if (isGalleryMode) {
    // 画集域名：允许 /gallery-site/*、/g/*（分享画集）、/image/*、/_nuxt/*、/api/* 路径
    const allowedPrefixes = ['/gallery-site', '/g/', '/image/', '/_nuxt/', '/api/']
    const isAllowed = allowedPrefixes.some(p => path.startsWith(p))
    if (!isAllowed) {
      return navigateTo('/gallery-site/', { replace: true })
    }
  }
  // 非画集域名：不阻止 /gallery-site/* 访问，画集页面在主站域名下也可用
})
