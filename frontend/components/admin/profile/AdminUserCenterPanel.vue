<template>
  <USlideover :model-value="props.open" :ui="{ width: 'sm:max-w-3xl' }" @update:model-value="emit('update:open', $event)">
    <div class="relative flex h-full flex-col overflow-hidden bg-white dark:bg-neutral-950">
      <div class="pointer-events-none absolute inset-0">
        <div class="absolute -right-12 -top-14 h-44 w-44 rounded-full bg-amber-400/20 blur-2xl dark:bg-amber-500/10" />
        <div class="absolute -left-10 bottom-6 h-40 w-40 rounded-full bg-sky-400/15 blur-2xl dark:bg-sky-500/10" />
        <div class="absolute inset-0 opacity-[0.08] [background-size:18px_18px] [background-image:linear-gradient(to_right,rgba(120,113,108,0.45)_1px,transparent_1px),linear-gradient(to_bottom,rgba(120,113,108,0.45)_1px,transparent_1px)] dark:opacity-[0.05]" />
      </div>

      <div class="relative z-10 flex h-full flex-col">
        <header class="border-b border-stone-200/80 px-4 pb-4 pt-4 dark:border-neutral-800">
          <div class="rounded-2xl border border-amber-200/50 bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 p-[1px] shadow-sm shadow-amber-500/15 dark:border-amber-500/40">
            <div class="rounded-[15px] bg-white/95 px-4 py-3 backdrop-blur dark:bg-neutral-900/90">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 text-white">
                      <UIcon name="heroicons:shield-check" class="h-5 w-5" />
                    </div>
                    <div class="min-w-0">
                      <p class="truncate text-base font-semibold text-stone-900 dark:text-stone-100">管理员用户中心</p>
                      <p class="truncate text-xs text-stone-500 dark:text-stone-400">在线会话、账号凭据与安全日志统一管理</p>
                    </div>
                  </div>
                  <div class="mt-3 flex flex-wrap items-center gap-2">
                    <UBadge color="gray" variant="soft">{{ authStore.username || 'Admin' }}</UBadge>
                    <UBadge color="emerald" variant="soft">状态正常</UBadge>
                    <UBadge color="amber" variant="soft">在线 {{ sessions.length }} 台设备</UBadge>
                  </div>
                </div>
                <div class="flex items-center gap-1">
                  <UButton size="xs" color="red" variant="soft" icon="heroicons:arrow-right-on-rectangle" @click="handleLogout">
                    退出
                  </UButton>
                  <UButton size="xs" color="gray" variant="ghost" icon="heroicons:x-mark" @click="closePanel" />
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-1.5 rounded-xl bg-stone-100/80 p-1 dark:bg-neutral-900/70">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="group flex min-h-10 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold transition-colors sm:text-sm"
              :class="activeTab === tab.key
                ? 'bg-white text-stone-900 shadow-sm dark:bg-neutral-800 dark:text-stone-100'
                : 'text-stone-500 hover:bg-white/60 hover:text-stone-700 dark:text-stone-400 dark:hover:bg-neutral-800/60 dark:hover:text-stone-200'"
              @click="activeTab = tab.key"
            >
              <UIcon :name="tab.icon" class="h-4 w-4" />
              <span>{{ tab.label }}</span>
            </button>
          </div>
        </header>

        <div class="relative z-10 flex-1 overflow-y-auto px-4 py-4">
          <div v-if="activeTab === 'credentials'" class="space-y-4">
            <UCard class="panel-card">
              <template #header>
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-sm font-semibold text-stone-900 dark:text-stone-100">更新管理员凭据</p>
                    <p class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">用户名与密码可以分开修改，留空字段将保持不变</p>
                  </div>
                  <UBadge color="blue" variant="soft">账号安全</UBadge>
                </div>
              </template>

              <div class="space-y-3.5">
                <UFormGroup label="新用户名">
                  <UInput v-model="settingsForm.username" placeholder="留空则不修改" autocomplete="username" />
                </UFormGroup>

                <UFormGroup label="新密码">
                  <UInput v-model="settingsForm.password" type="password" placeholder="留空则不修改" autocomplete="new-password" />
                  <template #hint>
                    <span class="text-xs text-stone-500 dark:text-stone-400">建议至少 8 位，包含字母和数字</span>
                  </template>
                </UFormGroup>

                <UFormGroup label="确认密码">
                  <UInput v-model="settingsForm.confirmPassword" type="password" placeholder="再次输入新密码" autocomplete="new-password" />
                </UFormGroup>
              </div>

              <template #footer>
                <div class="flex items-center justify-between gap-2">
                  <div class="text-xs text-stone-500 dark:text-stone-400">
                    密码强度：<span class="font-medium">{{ passwordStrength.label }}</span>
                  </div>
                  <UButton color="primary" :loading="saving" @click="handleUpdateSettings">
                    保存修改
                  </UButton>
                </div>
              </template>
            </UCard>
          </div>

          <div v-else-if="activeTab === 'sessions'" class="space-y-4">
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <UCard class="panel-card">
                <p class="text-xs text-stone-500 dark:text-stone-400">在线会话</p>
                <p class="mt-1 text-xl font-semibold text-stone-900 dark:text-stone-100">{{ sessions.length }}</p>
              </UCard>
              <UCard class="panel-card">
                <p class="text-xs text-stone-500 dark:text-stone-400">当前设备</p>
                <p class="mt-1 truncate text-sm font-semibold text-amber-600 dark:text-amber-300">{{ currentSessionLabel }}</p>
              </UCard>
              <UCard class="panel-card">
                <p class="text-xs text-stone-500 dark:text-stone-400">最近同步</p>
                <p class="mt-1 text-sm font-semibold text-stone-700 dark:text-stone-200">{{ heartbeatAtLabel }}</p>
              </UCard>
            </div>

            <UCard class="panel-card">
              <template #header>
                <div class="flex items-center justify-between gap-2">
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-stone-900 dark:text-stone-100">在线会话列表</p>
                    <p class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">会话按活跃时间排序，支持逐台下线异常设备</p>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <UBadge color="gray" variant="soft">{{ sessions.length }} 台</UBadge>
                    <UButton
                      color="gray"
                      variant="ghost"
                      size="xs"
                      icon="heroicons:arrow-path"
                      :loading="sessionsLoading"
                      @click="loadSessions()"
                    >
                      刷新
                    </UButton>
                  </div>
                </div>
              </template>

              <div v-if="sessionsLoading && sessions.length === 0" class="py-8 text-center">
                <UIcon name="heroicons:arrow-path" class="mx-auto h-6 w-6 animate-spin text-amber-500" />
                <p class="mt-2 text-xs text-stone-500 dark:text-stone-400">正在同步在线会话...</p>
              </div>

              <div v-else-if="sessions.length === 0" class="py-8 text-center text-sm text-stone-400 dark:text-stone-500">
                暂无活跃会话记录
              </div>

              <div v-else class="space-y-2.5">
                <div
                  v-for="session in sessions"
                  :key="session.session_id"
                  class="session-row rounded-xl border p-3 transition-colors"
                  :class="session.is_current
                    ? 'border-amber-300/90 bg-amber-50/75 dark:border-amber-600/70 dark:bg-amber-900/20'
                    : 'border-stone-200/80 bg-white/85 hover:border-stone-300 dark:border-neutral-700/80 dark:bg-neutral-900/60 dark:hover:border-neutral-600'"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0 space-y-1.5">
                      <div class="flex flex-wrap items-center gap-2">
                        <div class="flex h-8 w-8 items-center justify-center rounded-lg text-white" :class="platformBadge(session.platform).bg">
                          <UIcon :name="platformBadge(session.platform).icon" class="h-4 w-4" />
                        </div>
                        <p class="truncate text-sm font-semibold text-stone-900 dark:text-stone-100">
                          {{ sessionDisplayLabel(session) }}
                        </p>
                        <UBadge v-if="session.is_current" color="amber" variant="soft" size="xs">当前设备</UBadge>
                        <UBadge v-else color="gray" variant="soft" size="xs">{{ platformLabel(session.platform) }}</UBadge>
                        <UBadge v-if="session.remember_me" color="emerald" variant="soft" size="xs">记住我</UBadge>
                      </div>

                      <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
                        <span>IP：{{ session.ip_address || '未知' }}</span>
                        <span>登录：{{ session.login_time || '未知' }}</span>
                        <span>活跃：{{ session.last_active || '未知' }}</span>
                      </div>

                      <p v-if="session.user_agent" class="truncate text-xs text-stone-400 dark:text-stone-500">
                        UA：{{ session.user_agent }}
                      </p>
                    </div>

                    <UButton
                      v-if="!session.is_current"
                      size="xs"
                      color="red"
                      variant="soft"
                      icon="heroicons:power"
                      :loading="revoking && revokingSession?.session_id === session.session_id"
                      @click="openRevokeModal(session)"
                    >
                      下线
                    </UButton>
                  </div>
                </div>
              </div>
            </UCard>
          </div>

          <div v-else class="space-y-3">
            <UCard class="panel-card">
              <template #header>
                <div class="flex items-center justify-between gap-2">
                  <div>
                    <p class="text-sm font-semibold text-stone-900 dark:text-stone-100">安全审计日志</p>
                    <p class="mt-0.5 text-xs text-stone-500 dark:text-stone-400">登录事件、会话变更和凭据操作都会记录在这里</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <USelect
                      v-model="logFilter"
                      :options="logFilterOptions"
                      option-attribute="label"
                      value-attribute="value"
                      size="xs"
                      class="w-36"
                    />
                    <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="xs" :loading="logsLoading" @click="loadLogs()" />
                  </div>
                </div>
              </template>

              <div v-if="logsLoading && logs.length === 0" class="py-8 text-center">
                <UIcon name="heroicons:arrow-path" class="mx-auto h-6 w-6 animate-spin text-sky-500" />
                <p class="mt-2 text-xs text-stone-500 dark:text-stone-400">正在加载日志...</p>
              </div>

              <div v-else-if="filteredLogs.length === 0" class="py-8 text-center text-sm text-stone-400 dark:text-stone-500">
                暂无日志记录
              </div>

              <div v-else class="space-y-1.5">
                <div
                  v-for="(log, idx) in paginatedLogs"
                  :key="`${log.time}-${idx}`"
                  class="rounded-lg border border-transparent px-3 py-2.5 transition-colors hover:border-stone-200 hover:bg-stone-50/70 dark:hover:border-neutral-700 dark:hover:bg-neutral-900/70"
                >
                  <div class="flex items-start gap-3">
                    <div class="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-white" :class="logMeta(log.type).bgClass">
                      <UIcon :name="logMeta(log.type).icon" class="h-3.5 w-3.5" />
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="flex flex-wrap items-center gap-1.5">
                        <UBadge :color="logMeta(log.type).color" variant="soft" size="xs">{{ logMeta(log.type).label }}</UBadge>
                        <span v-if="log.username" class="text-xs font-medium text-stone-600 dark:text-stone-300">{{ log.username }}</span>
                      </div>
                      <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-stone-500 dark:text-stone-400">
                        <span>{{ log.ip || '-' }}</span>
                        <span>{{ log.time || '-' }}</span>
                      </div>
                      <p v-if="log.detail" class="mt-1 truncate text-xs text-stone-400 dark:text-stone-500">
                        {{ log.detail }}
                      </p>
                    </div>
                  </div>
                </div>

                <div v-if="filteredLogs.length > logsPageSize * logsPage" class="pt-2">
                  <UButton color="gray" variant="ghost" size="xs" block @click="logsPage += 1">
                    加载更多（剩余 {{ filteredLogs.length - logsPageSize * logsPage }} 条）
                  </UButton>
                </div>
              </div>
            </UCard>
          </div>
        </div>
      </div>
    </div>
  </USlideover>

  <UModal v-model="revokeModalOpen">
    <UCard>
      <template #header>
        <h3 class="text-base font-semibold text-red-600 dark:text-red-400">确认下线会话</h3>
      </template>
      <div class="space-y-3 text-sm text-stone-600 dark:text-stone-300">
        <p>下线后该设备需要重新登录才能继续访问后台。</p>
        <p v-if="revokingSession">
          目标设备：<span class="font-semibold">{{ sessionDisplayLabel(revokingSession) }}</span>
        </p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="revokeModalOpen = false">取消</UButton>
          <UButton color="red" :loading="revoking" @click="confirmRevokeSession">确认下线</UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import { getClientDeviceFingerprint, parseUserAgentToLabel } from '~/utils/deviceFingerprint'

type UserCenterTab = 'credentials' | 'sessions' | 'logs'

interface SettingsForm {
  username: string
  password: string
  confirmPassword: string
}

interface AdminSessionItem {
  session_id: string
  token_prefix: string
  ip_address: string
  device_name: string
  device_label?: string
  os_name?: string
  browser_name?: string
  browser_version?: string
  platform: string
  user_agent: string
  device_id: string
  login_time: string
  last_active: string
  is_current: boolean
  remember_me: boolean
}

interface AdminSessionPayload {
  sessions: AdminSessionItem[]
  count: number
  current_session_id?: string
}

interface AdminSecurityLogItem {
  type: string
  ip: string
  username?: string
  detail?: string
  time: string
}

interface ApiResult<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

const ADMIN_DEVICE_ID_KEY = 'tgib_admin_device_id'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [boolean]
}>()

const authStore = useAuthStore()
const runtimeConfig = useRuntimeConfig()
const notification = useNotification()

const tabs: { key: UserCenterTab; label: string; icon: string }[] = [
  { key: 'credentials', label: '凭据', icon: 'heroicons:key' },
  { key: 'sessions', label: '会话', icon: 'heroicons:computer-desktop' },
  { key: 'logs', label: '日志', icon: 'heroicons:shield-check' }
]

const activeTab = ref<UserCenterTab>('credentials')

const saving = ref(false)
const settingsForm = ref<SettingsForm>({ username: '', password: '', confirmPassword: '' })

const sessionsLoading = ref(false)
const sessions = ref<AdminSessionItem[]>([])
const heartbeatAt = ref<number | null>(null)
const heartbeatTimer = ref<ReturnType<typeof setInterval> | null>(null)

const revokeModalOpen = ref(false)
const revoking = ref(false)
const revokingSession = ref<AdminSessionItem | null>(null)

const logsLoading = ref(false)
const logs = ref<AdminSecurityLogItem[]>([])
const logFilter = ref('all')
const logsPage = ref(1)
const logsPageSize = 30

const logFilterOptions = [
  { value: 'all', label: '全部事件' },
  { value: 'login_success', label: '登录成功' },
  { value: 'login_failed', label: '登录失败' },
  { value: 'login_locked', label: '登录锁定' },
  { value: 'logout', label: '主动登出' },
  { value: 'session_kicked', label: '会话踢出' },
  { value: 'password_changed', label: '密码修改' }
]

const passwordStrength = computed(() => {
  const pwd = settingsForm.value.password || ''
  if (!pwd) return { label: '未设置', score: 0 }
  let score = 0
  if (pwd.length >= 8) score += 1
  if (/[a-z]/i.test(pwd)) score += 1
  if (/\d/.test(pwd)) score += 1
  if (/[^a-zA-Z0-9]/.test(pwd)) score += 1
  if (score <= 1) return { label: '弱', score }
  if (score <= 3) return { label: '中', score }
  return { label: '强', score }
})

const currentSessionLabel = computed(() => {
  const current = sessions.value.find(item => item.is_current)
  if (!current) return '当前浏览器'
  return sessionDisplayLabel(current)
})

const heartbeatAtLabel = computed(() => {
  if (!heartbeatAt.value) return '未同步'
  return new Date(heartbeatAt.value).toLocaleTimeString('zh-CN', { hour12: false })
})

const filteredLogs = computed(() => {
  if (logFilter.value === 'all') return logs.value
  return logs.value.filter(item => item.type === logFilter.value)
})

const paginatedLogs = computed(() => filteredLogs.value.slice(0, logsPageSize * logsPage.value))

const closePanel = () => emit('update:open', false)

const resetCredentialsForm = () => {
  settingsForm.value = { username: '', password: '', confirmPassword: '' }
}

const platformLabel = (platform?: string) => {
  const p = String(platform || '').toLowerCase()
  if (p === 'ios') return 'iOS'
  if (p === 'android') return 'Android'
  if (p === 'desktop') return 'Desktop'
  if (p === 'web') return 'Web'
  return 'Unknown'
}

const sessionDisplayLabel = (session: Partial<AdminSessionItem> | null | undefined) => {
  if (!session) return 'Unknown Device'
  const explicit = String(session.device_label || session.device_name || '').trim()
  if (explicit) return explicit
  const uaLabel = parseUserAgentToLabel(session.user_agent || '')
  if (uaLabel) return uaLabel
  return platformLabel(session.platform)
}

const platformBadge = (platform?: string) => {
  const p = String(platform || '').toLowerCase()
  if (p === 'ios') return { icon: 'heroicons:device-phone-mobile', bg: 'bg-gradient-to-br from-indigo-500 to-blue-600' }
  if (p === 'android') return { icon: 'heroicons:device-phone-mobile', bg: 'bg-gradient-to-br from-emerald-500 to-green-600' }
  if (p === 'desktop') return { icon: 'heroicons:computer-desktop', bg: 'bg-gradient-to-br from-amber-500 to-orange-600' }
  return { icon: 'heroicons:globe-alt', bg: 'bg-gradient-to-br from-slate-500 to-slate-600' }
}

const logMeta = (type: string) => {
  const map: Record<string, { label: string; icon: string; color: string; bgClass: string }> = {
    login_success: { label: '登录成功', icon: 'heroicons:check-circle', color: 'green', bgClass: 'bg-gradient-to-br from-green-500 to-emerald-600' },
    login_failed: { label: '登录失败', icon: 'heroicons:x-circle', color: 'red', bgClass: 'bg-gradient-to-br from-red-500 to-rose-600' },
    login_locked: { label: '登录锁定', icon: 'heroicons:lock-closed', color: 'orange', bgClass: 'bg-gradient-to-br from-orange-500 to-amber-600' },
    logout: { label: '主动登出', icon: 'heroicons:arrow-right-on-rectangle', color: 'gray', bgClass: 'bg-gradient-to-br from-stone-400 to-stone-500' },
    session_kicked: { label: '会话踢出', icon: 'heroicons:user-minus', color: 'amber', bgClass: 'bg-gradient-to-br from-amber-500 to-yellow-600' },
    password_changed: { label: '密码修改', icon: 'heroicons:key', color: 'blue', bgClass: 'bg-gradient-to-br from-blue-500 to-indigo-600' }
  }
  return map[type] || { label: type, icon: 'heroicons:information-circle', color: 'gray', bgClass: 'bg-gradient-to-br from-stone-400 to-stone-500' }
}

const buildDeviceHeaders = () => {
  const fp = getClientDeviceFingerprint({
    deviceIdKey: ADMIN_DEVICE_ID_KEY,
    deviceIdPrefix: 'admin'
  })
  return fp.headers
}

const normalizeSessionItem = (raw: Partial<AdminSessionItem> & Record<string, any>): AdminSessionItem => ({
  session_id: String(raw.session_id || ''),
  token_prefix: String(raw.token_prefix || ''),
  ip_address: String(raw.ip_address || raw.ip || ''),
  device_name: String(raw.device_name || ''),
  device_label: String(raw.device_label || ''),
  os_name: String(raw.os_name || ''),
  browser_name: String(raw.browser_name || ''),
  browser_version: String(raw.browser_version || ''),
  platform: String(raw.platform || ''),
  user_agent: String(raw.user_agent || ''),
  device_id: String(raw.device_id || ''),
  login_time: String(raw.login_time || ''),
  last_active: String(raw.last_active || ''),
  is_current: Boolean(raw.is_current),
  remember_me: Boolean(raw.remember_me)
})

const buildCurrentSessionFallback = (): AdminSessionItem => {
  const fp = getClientDeviceFingerprint({
    deviceIdKey: ADMIN_DEVICE_ID_KEY,
    deviceIdPrefix: 'admin'
  })
  const now = new Date().toLocaleString('zh-CN', { hour12: false })
  const deviceId = fp.deviceId || ''
  const platform = fp.platform || 'web'
  const deviceName = fp.deviceLabel || `${platformLabel(platform)} · Browser`
  return {
    session_id: deviceId ? `current-${deviceId.slice(0, 12)}` : 'current-browser',
    token_prefix: 'current',
    ip_address: '',
    device_name: deviceName,
    device_label: fp.deviceLabel,
    os_name: fp.osName,
    browser_name: fp.browserName,
    browser_version: fp.browserVersion,
    platform,
    user_agent: import.meta.client ? (navigator.userAgent || '') : '',
    device_id: deviceId,
    login_time: '',
    last_active: now,
    is_current: true,
    remember_me: false
  }
}

const ensureCurrentSession = (items: AdminSessionItem[]) => {
  if (items.some(item => item.is_current)) return items
  return [buildCurrentSessionFallback(), ...items]
}

const startHeartbeat = () => {
  stopHeartbeat()
  void heartbeatSession()
  heartbeatTimer.value = setInterval(() => {
    void heartbeatSession(true)
  }, 30000)
}

const stopHeartbeat = () => {
  if (heartbeatTimer.value) {
    clearInterval(heartbeatTimer.value)
    heartbeatTimer.value = null
  }
}

const heartbeatSession = async (silent = false) => {
  try {
    await $fetch<ApiResult<{ server_time: number }>>(`${runtimeConfig.public.apiBase}/api/admin/session-heartbeat`, {
      method: 'POST',
      credentials: 'include',
      headers: buildDeviceHeaders()
    })
    heartbeatAt.value = Date.now()
    if (activeTab.value === 'sessions') {
      await loadSessions({ silent: true })
    }
  } catch (error: any) {
    if (!silent) {
      notification.error('会话同步失败', error?.data?.error || error?.message || '无法刷新在线会话状态')
    }
  }
}

const loadSessions = async ({ silent = false }: { silent?: boolean } = {}) => {
  if (!silent) sessionsLoading.value = true
  try {
    const res = await $fetch<ApiResult<AdminSessionPayload | AdminSessionItem[]>>(`${runtimeConfig.public.apiBase}/api/admin/active-sessions`, {
      credentials: 'include'
    })
    if (!res.success) throw new Error(res.error || res.message || '获取在线会话失败')
    const payload = res.data
    let parsed: AdminSessionItem[] = []
    if (Array.isArray(payload)) {
      parsed = payload.map(item => normalizeSessionItem(item))
    } else {
      parsed = (payload?.sessions || []).map(item => normalizeSessionItem(item))
    }
    sessions.value = ensureCurrentSession(parsed)
    heartbeatAt.value = Date.now()
  } catch (error: any) {
    if (!silent) {
      notification.error('加载失败', error?.data?.error || error?.message || '无法加载在线会话')
    }
  } finally {
    if (!silent) sessionsLoading.value = false
  }
}

const revokeSession = async (sessionId: string) => {
  try {
    return await $fetch<ApiResult<{ kicked: number }>>(`${runtimeConfig.public.apiBase}/api/admin/revoke-session`, {
      method: 'POST',
      credentials: 'include',
      body: { session_id: sessionId }
    })
  } catch (error: any) {
    const status = error?.statusCode || error?.status || error?.response?.status
    if (status === 404) {
      return await $fetch<ApiResult<{ kicked: number }>>(`${runtimeConfig.public.apiBase}/api/admin/kick-session`, {
        method: 'POST',
        credentials: 'include',
        body: { session_id: sessionId }
      })
    }
    throw error
  }
}

const openRevokeModal = (session: AdminSessionItem) => {
  revokingSession.value = session
  revokeModalOpen.value = true
}

const confirmRevokeSession = async () => {
  if (!revokingSession.value || !revokingSession.value.session_id) return
  revoking.value = true
  try {
    const res = await revokeSession(revokingSession.value.session_id)
    if (!res.success) throw new Error(res.error || res.message || '无法下线会话')
    notification.success('下线成功', '目标会话已终止')
    revokeModalOpen.value = false
    revokingSession.value = null
    await loadSessions({ silent: true })
  } catch (error: any) {
    notification.error('下线失败', error?.data?.error || error?.message || '无法下线该会话')
  } finally {
    revoking.value = false
  }
}

const loadLogs = async ({ silent = false }: { silent?: boolean } = {}) => {
  logsLoading.value = true
  try {
    const res = await $fetch<ApiResult<AdminSecurityLogItem[]>>(`${runtimeConfig.public.apiBase}/api/admin/security-log`, {
      credentials: 'include'
    })
    if (!res.success) throw new Error(res.error || res.message || '获取日志失败')
    logs.value = Array.isArray(res.data) ? res.data : []
    logsPage.value = 1
  } catch (error: any) {
    if (!silent) {
      notification.error('加载失败', error?.data?.error || error?.message || '无法加载安全日志')
    }
  } finally {
    logsLoading.value = false
  }
}

const handleUpdateSettings = async () => {
  if (settingsForm.value.password && settingsForm.value.password !== settingsForm.value.confirmPassword) {
    notification.error('错误', '两次输入的密码不一致')
    return
  }

  saving.value = true
  try {
    await authStore.updateSettings(settingsForm.value)
    notification.success('保存成功', '管理员凭据已更新')
    resetCredentialsForm()
  } catch (error: any) {
    notification.error('保存失败', error?.data?.error || error?.message || '无法更新管理员凭据')
  } finally {
    saving.value = false
  }
}

const handleLogout = async () => {
  closePanel()
  await authStore.logout()
  navigateTo('/admin')
}

watch(logFilter, () => {
  logsPage.value = 1
})

watch(() => props.open, (open) => {
  if (!open) {
    stopHeartbeat()
    revokeModalOpen.value = false
    revokingSession.value = null
    return
  }

  resetCredentialsForm()
  if (activeTab.value === 'sessions') {
    void loadSessions()
    startHeartbeat()
  } else {
    stopHeartbeat()
  }
  if (activeTab.value === 'logs') {
    void loadLogs()
  }
}, { immediate: true })

watch(activeTab, (tab) => {
  if (!props.open) return

  if (tab === 'sessions') {
    void loadSessions()
    startHeartbeat()
  } else {
    stopHeartbeat()
  }

  if (tab === 'logs') {
    void loadLogs()
  }
})

onUnmounted(() => {
  stopHeartbeat()
})
</script>

<style scoped lang="scss">
.panel-card {
  border: 1px solid rgba(214, 211, 209, 0.65);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.94), rgba(250, 250, 249, 0.78));
}

.dark .panel-card {
  border-color: rgba(64, 64, 64, 0.7);
  background: linear-gradient(160deg, rgba(23, 23, 23, 0.86), rgba(12, 18, 24, 0.7));
}

.session-row {
  backdrop-filter: blur(6px);
}
</style>
