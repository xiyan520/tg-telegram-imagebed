import type { GalleryImage } from '~/composables/useGalleryApi'

export interface SharedGalleryMeta {
  id?: number
  name: string
  description?: string
  image_count: number
  access_mode?: string
  cover_image?: string
  cover_url?: string
  layout_mode?: 'masonry' | 'grid' | 'justified'
  theme_color?: string
  show_image_info?: boolean
  allow_download?: boolean
  sort_order?: 'newest' | 'oldest' | 'filename'
  nsfw_warning?: boolean
  custom_header_text?: string
}

export interface SharedGalleryData {
  gallery: SharedGalleryMeta
  images: GalleryImage[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

export interface SharedGalleryAdapter {
  key: string
  fetchPage: (page: number, limit: number) => Promise<SharedGalleryData>
  unlockPassword: (password: string) => Promise<void>
  getNsfwStorageKey: () => string
  getBackLink: () => string | undefined
  getErrorBackLink: () => string
  getErrorBackLabel: () => string
  getFooterLink: () => string
  getFooterLabel: () => string
  getFooterIcon: () => string
  getLoginMode: () => 'token' | 'both'
  getLoginShareToken: () => string | undefined
  getCanonicalPath: () => string
  getSharePath: () => string
}

interface GalleryApiClient {
  getSharedGallery: (shareToken: string, page?: number, limit?: number) => Promise<SharedGalleryData>
  unlockGallery: (shareToken: string, password: string) => Promise<boolean>
  getShareAllGallery: (shareAllToken: string, galleryId: number, page?: number, limit?: number) => Promise<SharedGalleryData>
  unlockShareAllGallery: (shareAllToken: string, galleryId: number, password: string) => Promise<boolean>
}

interface SingleShareAdapterOptions {
  api: GalleryApiClient
  shareToken: string
  fromGalleries?: string
  isGalleryMode: boolean
  gallerySiteName: string
  displayName: string
}

interface ShareAllAdapterOptions {
  api: GalleryApiClient
  shareAllToken: string
  galleryId: number
  displayName: string
}

export const createSingleShareAdapter = (options: SingleShareAdapterOptions): SharedGalleryAdapter => {
  const year = new Date().getFullYear()
  return {
    key: `single:${options.shareToken}:${options.fromGalleries || ''}`,
    fetchPage: (page, limit) => options.api.getSharedGallery(options.shareToken, page, limit),
    unlockPassword: async (password: string) => {
      await options.api.unlockGallery(options.shareToken, password)
    },
    getNsfwStorageKey: () => `nsfw_confirmed_${options.shareToken}`,
    getBackLink: () => (options.fromGalleries ? `/galleries/${options.fromGalleries}` : undefined),
    getErrorBackLink: () => (options.isGalleryMode ? '/gallery-site/' : '/'),
    getErrorBackLabel: () => (options.isGalleryMode ? '返回画集首页' : '返回首页'),
    getFooterLink: () => (options.isGalleryMode ? '/gallery-site/' : '/'),
    getFooterLabel: () => (options.isGalleryMode ? `© ${year} ${options.gallerySiteName}` : `Powered by ${options.displayName}`),
    getFooterIcon: () => (options.isGalleryMode ? 'heroicons:photo' : 'heroicons:cloud-arrow-up'),
    getLoginMode: () => 'token',
    getLoginShareToken: () => options.shareToken,
    getCanonicalPath: () => `/g/${options.shareToken}`,
    getSharePath: () => `/g/${options.shareToken}`
  }
}

export const createShareAllGalleryAdapter = (options: ShareAllAdapterOptions): SharedGalleryAdapter => {
  return {
    key: `share-all:${options.shareAllToken}:${options.galleryId}`,
    fetchPage: async (page, limit) => {
      if (!Number.isFinite(options.galleryId) || options.galleryId <= 0) {
        throw new Error('无效的画集 ID')
      }
      return options.api.getShareAllGallery(options.shareAllToken, options.galleryId, page, limit)
    },
    unlockPassword: async (password: string) => {
      if (!Number.isFinite(options.galleryId) || options.galleryId <= 0) {
        throw new Error('无效的画集 ID')
      }
      await options.api.unlockShareAllGallery(options.shareAllToken, options.galleryId, password)
    },
    getNsfwStorageKey: () => `nsfw_confirmed_${options.shareAllToken}_${options.galleryId}`,
    getBackLink: () => `/galleries/${options.shareAllToken}`,
    getErrorBackLink: () => `/galleries/${options.shareAllToken}`,
    getErrorBackLabel: () => '返回画集列表',
    getFooterLink: () => '/',
    getFooterLabel: () => `Powered by ${options.displayName}`,
    getFooterIcon: () => 'heroicons:cloud-arrow-up',
    getLoginMode: () => 'token',
    getLoginShareToken: () => undefined,
    getCanonicalPath: () => `/galleries/${options.shareAllToken}/${options.galleryId}`,
    getSharePath: () => `/galleries/${options.shareAllToken}/${options.galleryId}`
  }
}
