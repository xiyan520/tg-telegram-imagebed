<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold text-stone-900 dark:text-white">Telegram 绑定</h3>
    </template>

    <!-- 已登录 TG -->
    <div v-if="tgAuth.isLoggedIn && tgAuth.user" class="space-y-4">
      <div class="flex items-center gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
        <div class="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-xl flex-shrink-0">
          {{ (tgAuth.user.first_name || 'U')[0] }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-stone-800 dark:text-stone-200 truncate">
            {{ tgAuth.user.first_name }}
            <span v-if="tgAuth.user.username" class="text-stone-400 font-normal">@{{ tgAuth.user.username }}</span>
          </p>
          <p class="text-sm text-stone-500 dark:text-stone-400">
            Token 额度：{{ tgAuth.user.token_count }} / {{ tgAuth.user.max_tokens }}
          </p>
        </div>
        <UBadge color="green" variant="soft">已绑定</UBadge>
      </div>

      <!-- Token 绑定状态 -->
      <div v-if="publicSettings.tgBindEnabled" class="space-y-2">
        <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider">Token 绑定状态</p>
        <div class="space-y-2">
          <div
            v-for="item in tokenStore.vaultItems"
            :key="item.id"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div class="flex items-center gap-2 min-w-0">
              <code class="text-xs font-mono text-stone-600 dark:text-stone-400 truncate">{{ maskToken(item.token) }}</code>
              <UBadge v-if="item.tokenInfo?.tg_user_id" size="xs" color="blue" variant="soft">已绑定</UBadge>
              <UBadge v-else size="xs" color="gray" variant="soft">未绑定</UBadge>
            </div>
            <UButton
              v-if="!item.tokenInfo?.tg_user_id"
              size="xs" color="blue" variant="soft"
              icon="heroicons:link"
              :loading="bindingTokenId === item.id"
              @click="bindTokenToTg(item)"
            >
              绑定
            </UButton>
          </div>
        </div>
      </div>
      <!-- 解绑提示 -->
      <div class="p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
        <p class="text-xs text-stone-400">
          解除绑定将取消 Token 与 TG 账号的关联，Token 本身保留可用。
        </p>
      </div>
    </div>

    <!-- 未登录 TG -->
    <div v-else class="space-y-5">
      <div v-if="!loginStarted" class="text-center py-6 space-y-4">
        <div class="w-14 h-14 mx-auto bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center">
          <UIcon name="heroicons:chat-bubble-left-right" class="w-7 h-7 text-blue-500" />
        </div>
        <div>
          <p class="text-stone-700 dark:text-stone-300 font-medium">绑定 Telegram 账号</p>
          <p class="text-sm text-stone-400 mt-1">绑定后可管理 Token 额度和自动关联上传</p>
        </div>
        <UButton color="primary" icon="heroicons:paper-airplane" @click="startLogin">
          开始绑定
        </UButton>
      </div>

      <div v-else>
        <div v-if="loading" class="flex flex-col items-center py-8 gap-3">
          <UIcon name="heroicons:arrow-path" class="w-8 h-8 text-primary animate-spin" />
          <p class="text-sm text-gray-500">正在生成验证码...</p>
        </div>

        <div v-else-if="loginCode && loginStatus === 'pending'" class="space-y-4">
          <div class="flex flex-col items-center gap-2">
            <p class="text-sm text-gray-500">请将以下验证码发送给 Bot</p>
            <div class="text-4xl font-mono font-bold tracking-[0.3em] text-primary select-all py-3">
              {{ loginCode }}
            </div>
          </div>
          <div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
            <div class="flex items-start gap-3">
              <UIcon name="heroicons:chat-bubble-left-right" class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div class="text-sm text-blue-700 dark:text-blue-300 space-y-2">
                <p class="font-medium">操作步骤</p>
                <ol class="list-decimal list-inside space-y-1">
                  <li>点击下方按钮打开 Bot</li>
                  <li>将上方 6 位验证码发送给 Bot</li>
                  <li>等待自动绑定完成</li>
                </ol>
              </div>
            </div>
          </div>
          <UButton
            v-if="botUsername"
            :to="`https://t.me/${botUsername}`"
            target="_blank" color="primary" block size="lg" icon="heroicons:paper-airplane"
          >
            打开 Telegram Bot
          </UButton>
          <button class="text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors" @click="cancelLogin">
            取消
          </button>
        </div>

        <div v-else-if="loginStatus === 'expired'" class="flex flex-col items-center py-8 gap-4">
          <UIcon name="heroicons:clock" class="w-12 h-12 text-orange-400" />
          <p class="text-sm text-gray-500">验证码已过期</p>
          <UButton color="primary" @click="startLogin">重新获取</UButton>
        </div>

        <div v-else-if="errorMsg" class="flex flex-col items-center py-8 gap-4">
          <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-400" />
          <p class="text-sm text-red-500">{{ errorMsg }}</p>
          <UButton color="primary" @click="startLogin">重试</UButton>
        </div>
      </div>
    </div>

    <!-- 底部：解绑按钮 -->
    <template v-if="tgAuth.isLoggedIn" #footer>
      <UButton
        color="red" variant="ghost" size="sm"
        icon="heroicons:arrow-right-start-on-rectangle"
        @click="openUnbindModal"
      >
        解除 TG 绑定
      </UButton>
    </template>
  </UCard>

  <!-- 解绑弹窗 -->
  <UModal v-model="showUnbindModal">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-red-600 dark:text-red-400">解除 TG 绑定</h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="showUnbindModal = false" />
        </div>
      </template>
      <!-- 绑定的 Token 列表 -->
      <div class="space-y-4">
        <p class="text-sm text-stone-500 dark:text-stone-400">
          选择要解绑的 Token，或解绑全部并退出 TG 登录。
        </p>

        <div v-if="boundTokenItems.length === 0" class="text-center py-4 text-sm text-stone-400">
          没有已绑定的 Token
        </div>

        <div v-else class="space-y-2 max-h-60 overflow-y-auto">
          <div
            v-for="item in boundTokenItems"
            :key="item.id"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div class="min-w-0 flex-1">
              <code class="text-xs font-mono text-stone-600 dark:text-stone-400 truncate block">{{ maskToken(item.token) }}</code>
              <p class="text-xs text-stone-400 mt-0.5">
                {{ item.tokenInfo?.upload_count ?? '?' }} / {{ item.tokenInfo?.upload_limit ?? '?' }} 次上传
                <span v-if="item.albumName"> · {{ item.albumName }}</span>
              </p>
            </div>
            <UButton
              size="xs" color="red" variant="soft"
              icon="heroicons:link-slash"
              :loading="unbindingTokenId === item.id"
              @click="unbindSingle(item)"
            >
              解绑
            </UButton>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex items-center justify-between">
          <UButton
            v-if="boundTokenItems.length > 0"
            color="red" variant="solid" size="sm"
            icon="heroicons:trash"
            :loading="unbindingAll"
            @click="unbindAllAndLogout"
          >
            全部解绑并退出
          </UButton>
          <UButton
            v-else
            color="red" variant="solid" size="sm"
            icon="heroicons:arrow-right-start-on-rectangle"
            :loading="unbindingAll"
            @click="justLogout"
          >
            退出 TG 登录
          </UButton>
          <UButton color="gray" variant="ghost" size="sm" @click="showUnbindModal = false">取消</UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
import { maskToken } from '~/stores/token'

const toast = useLightToast()
const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const config = useRuntimeConfig()
const { publicSettings, logout: guestLogout } = useGuestAuth()

// TG 登录相关
const loginStarted = ref(false)
const loading = ref(false)
const loginCode = ref('')
const botUsername = ref('')
const loginStatus = ref<'pending' | 'ok' | 'expired'>('pending')
const errorMsg = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

// 绑定相关
const bindingTokenId = ref<string | null>(null)

// 解绑弹窗
const showUnbindModal = ref(false)
const unbindingTokenId = ref<string | null>(null)
const unbindingAll = ref(false)

// 已绑定 TG 的 Token 列表
const boundTokenItems = computed(() =>
  tokenStore.vaultItems.filter(i => i.tokenInfo?.tg_user_id)
)
// PLACEHOLDER_METHODS

const openUnbindModal = () => {
  showUnbindModal.value = true
}

// ========== TG 登录流程 ==========
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
    startPolling()
  } catch (e: any) {
    errorMsg.value = e.message || '生成验证码失败'
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!loginCode.value) return
    try {
      const res = await tgAuth.pollCodeStatus(loginCode.value)
      loginStatus.value = res.status
      if (res.status === 'ok') {
        stopPolling()
        loginStarted.value = false
        toast.success('TG 绑定成功')
      } else if (res.status === 'expired') {
        stopPolling()
      }
    } catch { /* 静默 */ }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

const cancelLogin = () => {
  stopPolling()
  loginStarted.value = false
  loginCode.value = ''
  errorMsg.value = ''
}
// ========== 绑定 ==========
const bindTokenToTg = async (item: any) => {
  bindingTokenId.value = item.id
  try {
    await $fetch(`${config.public.apiBase}/api/auth/token/bind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${item.token}` },
      credentials: 'include',
    })
    if (item.tokenInfo) item.tokenInfo.tg_user_id = true
    toast.success('绑定成功')
    tgAuth.checkSession()
  } catch (e: any) {
    toast.error(e.data?.error || e.message || '绑定失败')
  } finally {
    bindingTokenId.value = null
  }
}

// ========== 解绑单个 Token ==========
const unbindSingle = async (item: any) => {
  unbindingTokenId.value = item.id
  try {
    await $fetch(`${config.public.apiBase}/api/auth/token/unbind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${item.token}` },
      credentials: 'include',
    })
    if (item.tokenInfo) item.tokenInfo.tg_user_id = null
    toast.success('已解绑')
    await tgAuth.checkSession()
  } catch (e: any) {
    toast.error(e.data?.error || e.message || '解绑失败')
  } finally {
    unbindingTokenId.value = null
  }
}

// ========== 全部解绑并退出 ==========
const unbindAllAndLogout = async () => {
  unbindingAll.value = true
  try {
    const items = [...boundTokenItems.value]
    for (const item of items) {
      try {
        await $fetch(`${config.public.apiBase}/api/auth/token/unbind`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${item.token}` },
          credentials: 'include',
        })
        if (item.tokenInfo) item.tokenInfo.tg_user_id = null
      } catch { /* 单个失败继续 */ }
    }
    // 退出 TG 登录并清空本地 Token
    await guestLogout()
    showUnbindModal.value = false
    toast.success('已全部解绑并退出 TG')
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  } finally {
    unbindingAll.value = false
  }
}

// ========== 仅退出 TG 登录（无绑定 Token 时） ==========
const justLogout = async () => {
  unbindingAll.value = true
  try {
    await guestLogout()
    showUnbindModal.value = false
    toast.success('已退出 TG 登录')
  } catch (e: any) {
    toast.error(e.message || '退出失败')
  } finally {
    unbindingAll.value = false
  }
}

onUnmounted(() => { stopPolling() })
</script>
