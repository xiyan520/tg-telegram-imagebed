export type SeoSectionKey =
  | 'basic'
  | 'branding'
  | 'social'
  | 'crawler'
  | 'footer_preview'

export interface SeoSectionItem {
  key: SeoSectionKey
  label: string
  description: string
  icon: string
}

export type SeoDirtyMap = Partial<Record<SeoSectionKey, boolean>>

export interface AdminSeoSettings {
  seo_site_name: string
  seo_site_description: string
  seo_site_keywords: string
  seo_logo_mode: 'icon' | 'custom'
  seo_logo_url: string
  seo_favicon_url: string
  seo_og_title: string
  seo_og_description: string
  seo_og_image: string
  seo_og_site_name: string
  seo_og_type: 'website' | 'article' | 'profile'
  seo_canonical_url: string
  seo_robots_index: boolean
  seo_robots_follow: boolean
  seo_twitter_card_type: 'summary' | 'summary_large_image'
  seo_twitter_site: string
  seo_twitter_creator: string
  seo_author: string
  seo_theme_color: string
  seo_default_locale: string
  seo_footer_text: string
}
