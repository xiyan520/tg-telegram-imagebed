<template>
  <UModal v-model="modelValue" @close="cleanup">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">
            {{ phase === 'manage' ? 'Token 管理' : '游客登录' }}
          </h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="modelValue = false" />
        </div>
      </template>

      <!-- ========== 选择登录方式（TG 启用 + 不强制） ========== -->
      <div v-if="phase === 'choose'" class="grid grid-cols-2 gap-3">
        <button
          class="flex flex-col items-center gap-3 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all group"
          @click="chooseTgLogin"
        >
          <div class="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
            <UIcon name="heroicons:chat-bubble-left-right" class="w-6 h-6 text-blue-500" />
          </div>
          <div class="text-center">
            <p class="text-sm font-medium text-stone-800 dark:text-stone-200">Telegram 登录</p>
            <p class="text-xs text-stone-400 mt-1">通过 Bot 验证码登录</p>
          </div>
        </button>
        <button
          class="flex flex-col items-center gap-3 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-amber-400 dark:hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all group"
          @click="chooseTokenLogin"
        >
          <div class="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
            <UIcon name="heroicons:key" class="w-6 h-6 text-amber-500" />
          </div>
          <div class="text-center">
            <p class="text-sm font-medium text-stone-800 dark:text-stone-200">游客 Token</p>
            <p class="text-xs text-stone-400 mt-1">快速生成 Token 使用</p>
          </div>
        </button>
      </div>

      <!-- ========== 自动生成 Token ========== -->
      <div v-else-if="phase === 'generating'" class="flex flex-col items-center py-8 gap-3">
        <UIcon name="heroicons:arrow-path" class="w-8 h-8 text-primary animate-spin" />
        <p class="text-sm text-gray-500">正在生成 Token...</p>
      </div>

      <!-- ========== TG 验证码登录 ========== -->
      <template v-else-if="phase === 'login'">
        <!-- 从选择页进入时显示返回按钮 -->
        <button
          v-if="canGoBackToChoose"
          class="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 mb-3 transition-colors"
          @click="backToChoose"
        >
          <UIcon name="heroicons:arrow-left" class="w-3.5 h-3.5" />
          返回选择
        </button>

        <div v-if="loading" class="flex flex-col items-center py-8 gap-3">
          <UIcon name="heroicons:arrow-path" class="w-8 h-8 text-primary animate-spin" />
          <p class="text-sm text-gray-500">正在生成验证码...</p>
        </div>

        <div v-else-if="loginCode && loginStatus === 'pending'" class="space-y-5">
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
                  <li>等待自动登录完成</li>
                </ol>
              </div>
            </div>
          </div>
          <UButton
            v-if="botUsername"
            :to="`https://t.me/${botUsername}`"
            target="_blank"
            color="primary"
            block
            size="lg"
            icon="heroicons:paper-airplane"
          >
            打开 Telegram Bot
          </UButton>
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
      </template>

      <!-- ========== 成功（短暂过渡） ========== -->
      <div v-else-if="phase === 'success'" class="flex flex-col items-center py-8 gap-3">
        <UIcon name="heroicons:check-circle" class="w-12 h-12 text-green-500" />
        <p class="text-base font-medium text-green-600">登录成功！</p>
      </div>

      <!-- ========== 错误（非登录阶段） ========== -->
      <div v-else-if="phase === 'error'" class="flex flex-col items-center py-8 gap-4">
        <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-400" />
        <p class="text-sm text-red-500">{{ errorMsg || '操作失败' }}</p>
        <UButton color="primary" @click="handleOpen">重试</UButton>
      </div>

      <!-- ========== 管理阶段 ========== -->
      <template v-else-if="phase === 'manage'">
        <div class="space-y-5">
          <!-- TG 用户信息栏 -->
          <div v-if="tgAuth.isLoggedIn && tgAuth.user" class="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
            <div class="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
              {{ (tgAuth.user.first_name || 'U')[0] }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-stone-800 dark:text-stone-200 truncate">
                {{ tgAuth.user.first_name }}
                <span v-if="tgAuth.user.username" class="text-stone-400 dark:text-stone-500 font-normal">@{{ tgAuth.user.username }}</span>
              </p>
              <p class="text-xs text-stone-500 dark:text-stone-400">
                Token 额度：{{ tgAuth.user.token_count }} / {{ tgAuth.user.max_tokens }}
              </p>
            </div>
          </div>

          <!-- 无 Token 且可创建：分栏入口 -->
          <div v-if="tokenStore.vaultItems.length === 0 && !showAddInput" class="grid grid-cols-2 gap-3">
            <button
              class="flex flex-col items-center gap-3 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-amber-400 dark:hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-all group"
              :disabled="generating"
              @click="handleGenerate"
            >
              <div class="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <UIcon v-if="generating" name="heroicons:arrow-path" class="w-6 h-6 text-amber-500 animate-spin" />
                <UIcon v-else name="heroicons:plus" class="w-6 h-6 text-amber-500" />
              </div>
              <div class="text-center">
                <p class="text-sm font-medium text-stone-800 dark:text-stone-200">生成 Token</p>
                <p class="text-xs text-stone-400 mt-1">自动生成新的上传凭证</p>
              </div>
            </button>
            <button
              class="flex flex-col items-center gap-3 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-green-400 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all group"
              @click="showAddInput = true"
            >
              <div class="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center group-hover:scale-110 transition-transform">
                <UIcon name="heroicons:key" class="w-6 h-6 text-green-500" />
              </div>
              <div class="text-center">
                <p class="text-sm font-medium text-stone-800 dark:text-stone-200">输入 Token</p>
                <p class="text-xs text-stone-400 mt-1">使用已有的 Token 登录</p>
              </div>
            </button>
          </div>

          <!-- 无 Token 时：输入 Token 表单 -->
          <div v-if="tokenStore.vaultItems.length === 0 && showAddInput" class="space-y-3">
            <button
              class="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
              @click="showAddInput = false"
            >
              <UIcon name="heroicons:arrow-left" class="w-3.5 h-3.5" />
              返回
            </button>
            <div class="flex gap-2">
              <UInput v-model="addTokenInput" placeholder="粘贴 Token" size="sm" class="flex-1" @keyup.enter="verifyAndAdd" />
              <UButton size="sm" color="primary" :loading="verifying" @click="verifyAndAdd">登录</UButton>
            </div>
            <p class="text-xs text-stone-400">输入后将验证 Token 有效性</p>
          </div>

          <!-- 有 Token 时：Token 列表 -->
          <template v-if="tokenStore.vaultItems.length > 0">
            <div>
              <p class="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2">
                {{ tokenStore.vaultItems.length > 1 ? 'Token 列表' : '当前 Token' }}
              </p>
              <div class="space-y-2 max-h-48 overflow-y-auto">
                <div
                  v-for="item in tokenStore.vaultItems"
                  :key="item.id"
                  class="flex items-center gap-2 p-2.5 rounded-lg border transition-all cursor-pointer"
                  :class="item.id === tokenStore.activeVaultId
                    ? 'border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
                  @click="selectToken(item.id)"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-mono truncate text-stone-700 dark:text-stone-300">
                      {{ revealedTokenId === item.id ? item.token : maskToken(item.token) }}
                    </p>
                    <p class="text-xs text-stone-400">
                      {{ item.tokenInfo?.upload_count ?? '?' }} 次上传
                      <span v-if="item.albumName" class="ml-1">· {{ item.albumName }}</span>
                    </p>
                  </div>
                  <div class="flex items-center gap-1 flex-shrink-0">
                    <UBadge v-if="item.id === tokenStore.activeVaultId" size="xs" color="amber" variant="soft">当前</UBadge>
                    <UButton
                      :icon="revealedTokenId === item.id ? 'heroicons:eye-slash' : 'heroicons:eye'"
                      size="2xs" color="gray" variant="ghost"
                      @click.stop="toggleRevealToken(item.id)"
                    />
                    <UButton
                      icon="heroicons:trash" size="2xs" color="red" variant="ghost"
                      @click.stop="removeToken(item.id)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </template>

      <!-- 底部 -->
      <template #footer>
        <div class="flex items-center" :class="phase === 'manage' ? 'justify-between' : 'justify-end'">
          <UButton
            v-if="phase === 'manage'"
            color="red"
            variant="ghost"
            size="sm"
            icon="heroicons:arrow-right-start-on-rectangle"
            @click="handleLogout"
          >
            登出
          </UButton>
          <UButton color="gray" variant="ghost" @click="modelValue = false">关闭</UButton>
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
const { publicSettings, logout: guestLogout } = useGuestAuth()
const emit = defineEmits<{ 'login-success': [] }>()

const modelValue = defineModel<boolean>({ default: false })
const router = useRouter()

// 视图阶段
const phase = ref<'choose' | 'generating' | 'login' | 'success' | 'error' | 'manage'>('generating')

// TG 登录相关
const loading = ref(false)
const loginCode = ref('')
const botUsername = ref('')
const loginStatus = ref<'pending' | 'ok' | 'expired'>('pending')
const errorMsg = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

// 管理阶段相关
const generating = ref(false)
const showAddInput = ref(false)
const addTokenInput = ref('')
const verifying = ref(false)
const bindingTokenId = ref<string | null>(null)
const revealedTokenId = ref<string | null>(null)

// 是否可以返回选择页
const canGoBackToChoose = ref(false)

// ========== 弹窗打开时的入口逻辑 ==========
const handleOpen = async () => {
  errorMsg.value = ''
  canGoBackToChoose.value = false

  // 已有 Token → 直接跳转控制台
  if (tokenStore.hasToken) {
    modelValue.value = false
    router.push('/me')
    return
  }

  if (!publicSettings.value.tgAuthEnabled) {
    // TG 未启用 → 直接生成 Token
    await autoGenerateToken()
    return
  }

  if (publicSettings.value.tgAuthRequired) {
    // TG 启用 + 强制要求 TG 登录
    if (tgAuth.isLoggedIn) {
      await autoGenerateToken()
    } else {
      phase.value = 'login'
      startLogin()
    }
    return
  }

  // TG 启用 + 不强制 → 显示选择页（TG 登录 / 游客 Token）
  if (tgAuth.isLoggedIn) {
    // 已经 TG 登录了，直接生成
    await autoGenerateToken()
  } else {
    phase.value = 'choose'
  }
}

// ========== 选择页操作 ==========
const chooseTgLogin = () => {
  canGoBackToChoose.value = true
  phase.value = 'login'
  startLogin()
}

const chooseTokenLogin = () => {
  phase.value = 'manage'
}

// 管理阶段已登录后跳转
const goToConsole = () => {
  modelValue.value = false
  router.push('/me')
}

const backToChoose = () => {
  cleanupLogin()
  phase.value = 'choose'
}

// ========== 自动生成 Token ==========
const autoGenerateToken = async () => {
  phase.value = 'generating'
  try {
    await tokenStore.generateToken()
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
    toast.success('Token 已生成')
    emit('login-success')
    modelValue.value = false
    router.push('/me')
  } catch (e: any) {
    errorMsg.value = e.message || '生成 Token 失败'
    phase.value = 'error'
  }
}

// ========== TG 验证码登录逻辑 ==========
const startLogin = async () => {
  cleanupLogin()
  loading.value = true
  errorMsg.value = ''
  loginStatus.value = 'pending'
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
        toast.success('登录成功')
        // TG 登录成功后：已有 Token 直接跳转，否则自动生成
        if (tokenStore.hasToken) {
          modelValue.value = false
          router.push('/me')
        } else {
          await autoGenerateToken()
        }
      } else if (res.status === 'expired') {
        stopPolling()
      }
    } catch {
      // 轮询失败静默忽略
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const cleanupLogin = () => {
  stopPolling()
  loginCode.value = ''
  botUsername.value = ''
  loginStatus.value = 'pending'
  errorMsg.value = ''
}

// ========== 管理阶段操作 ==========
const selectToken = async (id: string) => {
  try {
    await tokenStore.setActiveTokenById(id, { verify: true })
  } catch (e: any) {
    toast.error(e.message || '切换 Token 失败')
  }
}

const removeToken = async (id: string) => {
  if (!window.confirm('删除后该 Token 关联的上传记录将解除绑定，且无法恢复。确定删除？')) return
  try {
    await tokenStore.deleteTokenFromServer(id)
    toast.success('Token 已删除')
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
  } catch (e: any) {
    toast.error(e.message || '删除失败')
  }
  if (!tokenStore.hasToken && tokenStore.vaultItems.length === 0) {
    modelValue.value = false
  }
}

const handleGenerate = async () => {
  generating.value = true
  try {
    await tokenStore.generateToken()
    if (tgAuth.isLoggedIn) tgAuth.checkSession()
    toast.success('新 Token 已生成')
    emit('login-success')
    modelValue.value = false
    router.push('/me')
  } catch (e: any) {
    toast.error(e.message || '生成 Token 失败')
  } finally {
    generating.value = false
  }
}

const verifyAndAdd = async () => {
  const t = addTokenInput.value.trim()
  if (!t) return
  verifying.value = true
  try {
    await tokenStore.addTokenToVault(t, { makeActive: true, verify: true })
    toast.success('Token 已添加')
    addTokenInput.value = ''
    showAddInput.value = false
    emit('login-success')
    modelValue.value = false
    router.push('/me')
  } catch (e: any) {
    toast.error(e.message || 'Token 无效')
  } finally {
    verifying.value = false
  }
}

const toggleRevealToken = (id: string) => {
  revealedTokenId.value = revealedTokenId.value === id ? null : id
}

const bindTokenToTg = async (item: any) => {
  bindingTokenId.value = item.id
  try {
    const config = useRuntimeConfig()
    await $fetch(`${config.public.apiBase}/api/auth/token/bind`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${item.token}` },
      credentials: 'include',
    })
    // 绑定成功后刷新 tokenInfo
    if (item.tokenInfo) {
      item.tokenInfo.tg_user_id = true
    }
    toast.success('绑定成功')
    tgAuth.checkSession()
  } catch (e: any) {
    toast.error(e.data?.error || e.message || '绑定失败')
  } finally {
    bindingTokenId.value = null
  }
}

const handleLogout = async () => {
  await guestLogout()
  modelValue.value = false
}

// ========== 弹窗生命周期 ==========
const cleanup = () => {
  cleanupLogin()
  showAddInput.value = false
  addTokenInput.value = ''
  revealedTokenId.value = null
}

watch(modelValue, (open) => {
  if (open) {
    handleOpen()
  } else {
    cleanup()
  }
})
</script>
