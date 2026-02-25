// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  ssr: false,  // 禁用SSR，生成纯静态SPA

  modules: [
    '@nuxt/ui',
    '@pinia/nuxt',
    '@vueuse/nuxt'
  ],

  // 应用配置
  app: {
    baseURL: '/',
    buildAssetsDir: '/_nuxt/',
    head: {
      title: '',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    }
  },

  // CSS 配置
  css: [
    '~/assets/css/main.scss'
  ],

  // 运行时配置
  runtimeConfig: {
    public: {
      apiBase: '',  // 空字符串，使用相对路径
      cdnDomain: process.env.NUXT_PUBLIC_CDN_DOMAIN || '',
      cdnEnabled: process.env.NUXT_PUBLIC_CDN_ENABLED === 'true'
    }
  },

  // Nitro 配置（静态生成）
  nitro: {
    preset: 'static'
  },

  // UI 配置
  ui: {
    global: true,
    icons: ['heroicons'],
    notifications: {
      // 小屏幕优化配置
      position: 'bottom-right',
      timeout: 3000  // 3秒后自动消失，避免长时间遮挡
    }
  },

  // Icon 配置
  icon: {
    serverBundle: {
      collections: ['heroicons']
    }
  },

  // 开发服务器配置
  devServer: {
    port: 3000,
    host: '0.0.0.0'
  }
})
