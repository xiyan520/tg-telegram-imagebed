export type SettingsSectionKey =
  | 'domains'
  | 'cdn'
  | 'guest_policy'
  | 'token_limits'
  | 'upload_limits'
  | 'bot'
  | 'tg_auth'
  | 'proxy_and_tokens'
  | 'about_update'

export interface SettingsSectionItem {
  key: SettingsSectionKey
  label: string
  description: string
  icon: string
}

export type SettingsDirtyMap = Partial<Record<SettingsSectionKey, boolean>>

export interface DomainPolicyForm {
  guest: string
  token: string
  group: string
  admin_default: string
}

export interface AdminSystemSettings {
  guest_upload_policy: string
  guest_token_generation_enabled: boolean
  guest_existing_tokens_policy: string
  guest_token_max_upload_limit: number
  guest_token_max_expires_days: number
  max_file_size_mb: number
  daily_upload_limit: number
  cdn_enabled: boolean
  cloudflare_cdn_domain: string
  cloudflare_api_token: string
  cloudflare_api_token_set: boolean
  cloudflare_zone_id: string
  cloudflare_cache_level: string
  cloudflare_browser_ttl: number
  cloudflare_edge_ttl: number
  enable_smart_routing: boolean
  fallback_to_origin: boolean
  enable_cache_warming: boolean
  cache_warming_delay: number
  cdn_monitor_enabled: boolean
  cdn_redirect_enabled: boolean
  cdn_redirect_max_count: number
  cdn_redirect_delay: number
  bot_caption_filename_enabled: boolean
  bot_inline_buttons_enabled: boolean
  bot_user_delete_enabled: boolean
  bot_myuploads_enabled: boolean
  bot_myuploads_page_size: number
  bot_reply_link_formats: string
  bot_reply_template: string
  bot_reply_show_size: boolean
  bot_reply_show_filename: boolean
  proxy_url: string
  proxy_url_set: boolean
  proxy_env_set: boolean
  allowed_extensions: string
  tg_auth_enabled: boolean
  bot_token_configured: boolean
  tg_auth_required_for_token: boolean
  tg_bind_token_enabled: boolean
  tg_max_tokens_per_user: number
  tg_login_code_expire_minutes: number
  tg_session_expire_days: number
  max_guest_tokens_per_ip: number
  image_domain_restriction_enabled: boolean
  app_update_source: string
  app_update_release_repo: string
  app_update_release_asset_name: string
  app_update_release_sha_name: string
  app_update_repo_url: string
  app_update_branch: string
  app_update_last_status: string
  app_update_last_error: string
  app_update_last_version: string
  app_update_last_commit: string
  app_update_last_run_at: string
  app_update_last_duration_ms: number
}
