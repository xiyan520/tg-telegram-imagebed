export type AnnouncementSectionKey = 'status' | 'editor' | 'templates' | 'publish'

export interface AnnouncementSectionItem {
  key: AnnouncementSectionKey
  label: string
  description: string
  icon: string
}

export type AnnouncementDirtyMap = Partial<Record<AnnouncementSectionKey, boolean>>

export interface AnnouncementState {
  id: number
  enabled: boolean
  content: string
  created_at: string | null
  updated_at: string | null
}

export interface AnnouncementPayload {
  enabled: boolean
  content: string
}

export interface AnnouncementTemplate {
  name: string
  description: string
  content: string
}
