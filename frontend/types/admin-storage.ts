export type StorageSectionKey = 'overview' | 'backends' | 'policy' | 'danger_upload'

export interface StorageSectionItem {
  key: StorageSectionKey
  label: string
  description: string
  icon: string
}

export type StorageDirtyMap = Partial<Record<StorageSectionKey, boolean>>

export type StorageDriverType = 'telegram' | 'local' | 's3' | 'rclone'

export type StorageWizardStepKey = 'basic' | 'driver' | 'advanced' | 'confirm'

export interface StorageBackendForm {
  name: string
  driver: StorageDriverType
  bot_token: string
  chat_id: string
  root_dir: string
  endpoint: string
  bucket: string
  access_key: string
  secret_key: string
  region: string
  public_url_prefix: string
  path_style: boolean
  remote: string
  base_path: string
  rclone_bin: string
  config_path: string
  use_as_bot: boolean
}

export interface StorageGroupUploadForm {
  admin_only: boolean
  admin_ids: string
  tg_bound_only: boolean
  reply: boolean
  delete_delay: number
}

export interface StoragePrivateUploadForm {
  enabled: boolean
  mode: 'open' | 'tg_bound' | 'admin_only'
  admin_ids: string
}
