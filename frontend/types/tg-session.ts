export interface TgSessionItem {
  session_id: string
  device_id: string
  device_name: string
  device_label?: string
  os_name?: string
  browser_name?: string
  browser_version?: string
  platform: string
  ip_address: string
  user_agent: string
  created_at: string
  last_seen_at: string
  expires_at: string
  is_current: boolean
}

export interface TgSessionListData {
  sessions: TgSessionItem[]
  current_session_id?: string
  count: number
}
