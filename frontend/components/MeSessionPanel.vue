<template>
  <div class="space-y-4">
    <UCard class="session-hero-card">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3 min-w-0">
          <div class="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 text-white flex items-center justify-center shadow-sm">
            <UIcon name="heroicons:signal" class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <p class="text-base font-semibold text-stone-900 dark:text-white">在线会话</p>
            <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">
              管理当前 TG 登录设备，支持逐条下线异常终端
            </p>
          </div>
        </div>
        <UButton
          v-if="tgAuth.isLoggedIn"
          size="xs"
          color="gray"
          variant="soft"
          icon="heroicons:arrow-path"
          :loading="refreshing"
          @click="refreshSessions"
        >
          刷新
        </UButton>
      </div>
    </UCard>

    <UCard v-if="!tgAuth.isLoggedIn" class="session-login-card">
      <div v-if="!loginStarted" class="text-center py-6 space-y-4">
        <div class="w-14 h-14 mx-auto rounded-2xl bg-cyan-50 dark:bg-cyan-900/25 flex items-center justify-center">
          <UIcon name="heroicons:chat-bubble-left-right" class="w-7 h-7 text-cyan-500" />
        </div>
        <div>
          <p class="text-stone-800 dark:text-stone-200 font-semibold">使用 Telegram 登录会话中心</p>
          <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">登录后可查看设备、管理在线状态并同步 Token</p>
        </div>
        <UButton color="primary" icon="heroicons:paper-airplane" @click="startLogin">开始登录</UButton>
      </div>

      <div v-else class="space-y-4">
        <div v-if="loading" class="py-8 text-center space-y-2">
          <UIcon name="heroicons:arrow-path" class="w-7 h-7 text-cyan-500 mx-auto animate-spin" />
          <p class="text-sm text-stone-500">正在生成验证码...</p>
        </div>

        <div v-else-if="loginCode && loginStatus === 'pending'" class="space-y-4">
          <div class="text-center space-y-3">
            <p class="text-sm text-stone-500 dark:text-stone-400">把下面验证码发给 Bot 完成登录</p>
            <div class="flex justify-center gap-2">
              <div
                v-for="(char, idx) in loginCode.split('')"
                :key="idx"
                class="w-10 h-12 rounded-lg border border-cyan-300/80 dark:border-cyan-600/70 bg-cyan-50/80 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-200 flex items-center justify-center text-lg font-mono font-bold"
              >
                {{ char }}
              </div>
            </div>
            <UButton size="sm" color="gray" variant="soft" icon="heroicons:clipboard-document" @click="copyCode">
              复制验证码
            </UButton>
          </div>
          <UButton
            v-if="botUsername"
            :to="`https://t.me/${botUsername}`"
            target="_blank"
            color="primary"
            block
            icon="heroicons:paper-airplane"
          >
            打开 Telegram Bot
          </UButton>
          <div class="text-center">
            <UButton color="gray" variant="ghost" size="xs" @click="cancelLogin">取消</UButton>
          </div>
        </div>

        <div v-else-if="loginStatus === 'expired'" class="py-8 text-center space-y-3">
          <UIcon name="heroicons:clock" class="w-9 h-9 text-orange-400 mx-auto" />
          <p class="text-sm text-stone-500">验证码已过期</p>
          <UButton color="primary" size="sm" @click="startLogin">重新获取</UButton>
        </div>

        <div v-else-if="errorMsg" class="py-8 text-center space-y-3">
          <UIcon name="heroicons:exclamation-triangle" class="w-9 h-9 text-red-400 mx-auto" />
          <p class="text-sm text-red-500">{{ errorMsg }}</p>
          <UButton color="primary" size="sm" @click="startLogin">重试</UButton>
        </div>
      </div>
    </UCard>

    <template v-else>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <UCard class="session-stat-card">
          <p class="text-xs text-stone-500 dark:text-stone-400">在线设备</p>
          <p class="text-xl font-semibold text-stone-900 dark:text-white mt-1">{{ tgAuth.onlineSessionCount || tgAuth.sessions.length }}</p>
        </UCard>
        <UCard class="session-stat-card">
          <p class="text-xs text-stone-500 dark:text-stone-400">当前会话</p>
          <p class="text-sm font-semibold text-cyan-600 dark:text-cyan-300 mt-1 truncate">
            {{ currentSessionLabel }}
          </p>
        </UCard>
        <UCard class="session-stat-card">
          <p class="text-xs text-stone-500 dark:text-stone-400">身份状态</p>
          <p class="text-sm font-semibold text-emerald-600 dark:text-emerald-300 mt-1">TG 已登录</p>
        </UCard>
      </div>

      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-semibold text-stone-900 dark:text-white">设备列表</h3>
            <UBadge color="gray" variant="soft">{{ tgAuth.sessions.length }} 台设备</UBadge>
          </div>
        </template>

        <div v-if="tgAuth.sessions.length === 0" class="py-8 text-center text-sm text-stone-400">
          暂无在线会话
        </div>

        <div v-else class="space-y-2.5">
          <div
            v-for="session in tgAuth.sessions"
            :key="session.session_id"
            class="rounded-xl border p-3.5 transition-colors"
            :class="session.is_current
              ? 'border-cyan-300/80 dark:border-cyan-700/80 bg-cyan-50/70 dark:bg-cyan-900/20'
              : 'border-stone-200/80 dark:border-stone-700/80 bg-white/80 dark:bg-neutral-900/50 hover:border-stone-300 dark:hover:border-stone-600'"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 space-y-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="text-sm font-semibold text-stone-900 dark:text-stone-100">
                    {{ sessionDisplayLabel(session) }}
                  </p>
                  <UBadge v-if="session.is_current" size="xs" color="blue" variant="soft">当前设备</UBadge>
                  <UBadge v-else size="xs" color="gray" variant="soft">{{ platformLabel(session.platform) }}</UBadge>
                </div>
                <p class="text-xs text-stone-500 dark:text-stone-400">IP: {{ session.ip_address || '未知' }}</p>
                <p class="text-xs text-stone-500 dark:text-stone-400">
                  最近活跃：{{ formatTime(session.last_seen_at) }} · 过期：{{ formatTime(session.expires_at) }}
                </p>
              </div>
              <UButton
                v-if="!session.is_current"
                size="xs"
                color="red"
                variant="soft"
                icon="heroicons:power"
                :loading="revokingSessionId === session.session_id"
                @click="openRevokeModal(session)"
              >
                下线
              </UButton>
            </div>
          </div>
        </div>
      </UCard>
    </template>

    <UModal v-model="revokeModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-base font-semibold text-red-600 dark:text-red-400">确认下线会话</h3>
        </template>
        <div class="space-y-3 text-sm text-stone-600 dark:text-stone-300">
          <p>下线后该设备需要重新登录才能继续访问。</p>
          <p v-if="pendingSession">目标设备：<span class="font-medium">{{ sessionDisplayLabel(pendingSession) }}</span></p>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="revokeModalOpen = false">取消</UButton>
            <UButton color="red" :loading="revokingSessionId !== ''" @click="confirmRevoke">确认下线</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { TgSessionItem } from '~/types/tg-session'
import { parseUserAgentToLabel } from '~/utils/deviceFingerprint'

const tgAuth = useTgAuthStore()
const toast = useLightToast()

const loginStarted = ref(false)
const loading = ref(false)
const loginCode = ref('')
const botUsername = ref('')
const loginStatus = ref<'pending' | 'ok' | 'expired'>('pending')
const errorMsg = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null
let heartbeatTimer: ReturnType<typeof setInterval> | null = null

const refreshing = ref(false)
const revokeModalOpen = ref(false)
const pendingSession = ref<TgSessionItem | null>(null)
const revokingSessionId = ref('')

const currentSessionLabel = computed(() => {
  const current = tgAuth.sessions.find(s => s.is_current)
  if (!current) return '当前浏览器'
  return sessionDisplayLabel(current)
})

const sessionDisplayLabel = (session: Partial<TgSessionItem> | null | undefined) => {
  if (!session) return 'Unknown Device'
  const explicit = String(session.device_label || session.device_name || '').trim()
  if (explicit) return explicit
  const uaLabel = parseUserAgentToLabel(session.user_agent || '')
  if (uaLabel) return uaLabel
  return platformLabel(session.platform)
}

const platformLabel = (platform?: string) => {
  const p = String(platform || '').toLowerCase()
  if (p === 'ios') return 'iOS'
  if (p === 'android') return 'Android'
  if (p === 'desktop') return 'Desktop'
  if (p === 'web') return 'Web'
  return 'Unknown'
}

const formatTime = (val?: string) => {
  if (!val) return '未知'
  try { return new Date(val).toLocaleString('zh-CN') } catch { return val }
}

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(loginCode.value)
    toast.success('验证码已复制')
  } catch {
    toast.error('复制失败')
  }
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

const startHeartbeat = () => {
  stopHeartbeat()
  heartbeatTimer = setInterval(async () => {
    if (!tgAuth.isLoggedIn) return
    try {
      await tgAuth.heartbeat()
    } catch {
      // 心跳失败不弹错，避免干扰
    }
  }, 30000)
}

const refreshSessions = async () => {
  refreshing.value = true
  try {
    await tgAuth.fetchSessions()
  } catch (e: any) {
    toast.error(e.message || '会话刷新失败')
  } finally {
    refreshing.value = false
  }
}

const startLogin = async () => {
  loginStarted.value = true
  loading.value = true
  errorMsg.value = ''
  loginStatus.value = 'pending'
  loginCode.value = ''
  try {
    const data = await tgAuth.generateWebCode()
    loginCode.value = data.code
    botUsername.value = data.bot_username
    stopPolling()
    pollTimer = setInterval(async () => {
      if (!loginCode.value) return
      try {
        const res = await tgAuth.pollCodeStatus(loginCode.value)
        loginStatus.value = res.status
        if (res.status === 'ok') {
          stopPolling()
          loginStarted.value = false
          await tgAuth.syncTokensToVault()
          await tgAuth.fetchSessions()
          startHeartbeat()
          toast.success('登录成功，在线会话已同步')
        } else if (res.status === 'expired') {
          stopPolling()
        }
      } catch {
        // 轮询过程中网络抖动可忽略
      }
    }, 3000)
  } catch (e: any) {
    errorMsg.value = e.message || '生成验证码失败'
  } finally {
    loading.value = false
  }
}

const cancelLogin = () => {
  stopPolling()
  loginStarted.value = false
  loginCode.value = ''
  errorMsg.value = ''
}

const openRevokeModal = (session: TgSessionItem) => {
  pendingSession.value = session
  revokeModalOpen.value = true
}

const confirmRevoke = async () => {
  if (!pendingSession.value) return
  revokingSessionId.value = pendingSession.value.session_id
  try {
    await tgAuth.revokeSession(pendingSession.value.session_id)
    toast.success('会话已下线')
    revokeModalOpen.value = false
    pendingSession.value = null
    await tgAuth.fetchSessions()
  } catch (e: any) {
    toast.error(e.message || '下线失败')
  } finally {
    revokingSessionId.value = ''
  }
}

watch(() => tgAuth.isLoggedIn, async (logged) => {
  if (logged) {
    await tgAuth.fetchSessions().catch(() => {})
    startHeartbeat()
  } else {
    stopHeartbeat()
  }
}, { immediate: true })

onUnmounted(() => {
  stopPolling()
  stopHeartbeat()
})
</script>

<style scoped lang="scss">
.session-hero-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(246, 250, 255, 0.88));
}

.dark .session-hero-card {
  background: linear-gradient(135deg, rgba(23, 23, 23, 0.9), rgba(14, 40, 52, 0.45));
}

.session-login-card {
  border: 1px solid rgba(34, 211, 238, 0.2);
}

.session-stat-card {
  backdrop-filter: blur(6px);
}
</style>
