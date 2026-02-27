<template>
  <UModal v-model="modelValue" @close="cleanup">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">
            {{ phase === 'login' ? 'Telegram 登录' : '游客登录' }}
          </h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="modelValue = false" />
        </div>
      </template>

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
            <p class="text-xs text-stone-400 mt-1">生成或输入 Token 登录</p>
          </div>
        </button>
      </div>

      <div v-else-if="phase === 'generating'" class="flex flex-col items-center py-8 gap-3">
        <UIcon name="heroicons:arrow-path" class="w-8 h-8 text-primary animate-spin" />
        <p class="text-sm text-gray-500">正在生成 Token...</p>
      </div>

      <template v-else-if="phase === 'login'">
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
          <div class="flex flex-col items-center gap-3">
            <p class="text-sm text-stone-500 dark:text-stone-400">请将验证码发送给 Bot</p>
            <div class="flex gap-2">
              <div
                v-for="(char, idx) in loginCode.split('')"
                :key="idx"
                class="w-11 h-14 flex items-center justify-center rounded-lg border-2 border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 text-2xl font-mono font-bold text-amber-700 dark:text-amber-300"
              >
                {{ char }}
              </div>
            </div>
            <UButton
              size="sm"
              color="gray"
              variant="soft"
              icon="heroicons:clipboard-document"
              @click="copyCode"
            >
              复制验证码
            </UButton>
          </div>

          <div class="flex items-center justify-center gap-4 py-3">
            <div class="flex flex-col items-center gap-1">
              <div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <UIcon name="heroicons:clipboard-document" class="w-5 h-5 text-blue-500" />
              </div>
              <span class="text-xs text-stone-400">复制</span>
            </div>
            <UIcon name="heroicons:arrow-right" class="w-4 h-4 text-stone-300" />
            <div class="flex flex-col items-center gap-1">
              <div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <UIcon name="heroicons:paper-airplane" class="w-5 h-5 text-blue-500" />
              </div>
              <span class="text-xs text-stone-400">发送</span>
            </div>
            <UIcon name="heroicons:arrow-right" class="w-4 h-4 text-stone-300" />
            <div class="flex flex-col items-center gap-1">
              <div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-5 h-5 text-blue-500" />
              </div>
              <span class="text-xs text-stone-400">完成</span>
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

      <div v-else-if="phase === 'manage'" class="space-y-4">
        <button
          v-if="canGoBackToChoose"
          class="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300 transition-colors"
          @click="backToChoose"
        >
          <UIcon name="heroicons:arrow-left" class="w-3.5 h-3.5" />
          返回选择
        </button>

        <div class="grid grid-cols-2 gap-3">
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

        <div v-if="showAddInput" class="space-y-3">
          <div class="flex gap-2">
            <UInput v-model="addTokenInput" placeholder="粘贴 Token" size="sm" class="flex-1" @keyup.enter="verifyAndAdd" />
            <UButton size="sm" color="primary" :loading="verifying" @click="verifyAndAdd">登录</UButton>
          </div>
          <p class="text-xs text-stone-400">输入后将验证 Token 有效性</p>
        </div>
      </div>

      <div v-else-if="phase === 'success'" class="flex flex-col items-center py-6 gap-4">
        <div class="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
          <UIcon name="heroicons:check-circle" class="w-10 h-10 text-green-500" />
        </div>
        <p class="text-base font-medium text-green-600 dark:text-green-400">登录成功！</p>
        <div v-if="generatedToken" class="w-full space-y-2">
          <p class="text-xs text-stone-400 text-center">你的 Token（请妥善保管）</p>
          <div class="flex items-center gap-2 p-3 bg-stone-50 dark:bg-neutral-800 rounded-lg">
            <code class="flex-1 text-xs font-mono text-stone-600 dark:text-stone-400 truncate select-all">{{ generatedToken }}</code>
            <UButton
              size="2xs"
              color="gray"
              variant="soft"
              icon="heroicons:clipboard-document"
              @click="copyGeneratedToken"
            />
          </div>
        </div>
        <UButton color="primary" @click="goToConsole">进入控制台</UButton>
      </div>

      <div v-else-if="phase === 'error'" class="flex flex-col items-center py-8 gap-4">
        <UIcon name="heroicons:exclamation-triangle" class="w-12 h-12 text-red-400" />
        <p class="text-sm text-red-500">{{ errorMsg || '操作失败' }}</p>
        <UButton color="primary" @click="handleOpen">重试</UButton>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const toast = useLightToast()
const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const { publicSettings, loadSettings } = useGuestAuth()
const emit = defineEmits<{ 'login-success': [] }>()

const modelValue = defineModel<boolean>({ default: false })
const router = useRouter()

const phase = ref<'choose' | 'generating' | 'login' | 'manage' | 'success' | 'error'>('generating')

const loading = ref(false)
const loginCode = ref('')
const botUsername = ref('')
const loginStatus = ref<'pending' | 'ok' | 'expired'>('pending')
const errorMsg = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const canGoBackToChoose = ref(false)
const generatedToken = ref('')
const generating = ref(false)
const showAddInput = ref(false)
const addTokenInput = ref('')
const verifying = ref(false)

const goToConsole = () => {
  modelValue.value = false
  router.push('/me')
}

const handleOpen = async () => {
  errorMsg.value = ''
  canGoBackToChoose.value = false
  await loadSettings()

  if (tokenStore.hasToken) {
    goToConsole()
    return
  }

  if (!publicSettings.value.tgAuthEnabled) {
    await autoGenerateToken()
    return
  }

  if (publicSettings.value.tgAuthRequired) {
    if (tgAuth.isLoggedIn) {
      await autoGenerateToken()
    } else {
      phase.value = 'login'
      await startLogin()
    }
    return
  }

  if (tgAuth.isLoggedIn) {
    await autoGenerateToken()
  } else {
    phase.value = 'choose'
  }
}

const chooseTgLogin = () => {
  canGoBackToChoose.value = true
  phase.value = 'login'
  startLogin()
}

const chooseTokenLogin = () => {
  canGoBackToChoose.value = true
  phase.value = 'manage'
  showAddInput.value = false
}

const backToChoose = () => {
  cleanupLogin()
  phase.value = 'choose'
}

const autoGenerateToken = async () => {
  phase.value = 'generating'
  try {
    const result = await tokenStore.generateToken()
    await tgAuth.checkSession()
    generatedToken.value = result.token
    phase.value = 'success'
    emit('login-success')
    setTimeout(() => {
      if (modelValue.value) goToConsole()
    }, 2000)
  } catch (e: any) {
    errorMsg.value = e.message || '生成 Token 失败'
    phase.value = 'error'
  }
}

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
        await tgAuth.syncTokensToVault()
        if (tokenStore.hasToken) {
          goToConsole()
        } else {
          await autoGenerateToken()
        }
      } else if (res.status === 'expired') {
        stopPolling()
      }
    } catch {
      // polling retry
    }
  }, 3000)
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

const handleGenerate = async () => {
  generating.value = true
  try {
    await tokenStore.generateToken()
    await tgAuth.checkSession()
    toast.success('Token 已生成')
    emit('login-success')
    goToConsole()
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
    emit('login-success')
    addTokenInput.value = ''
    showAddInput.value = false
    goToConsole()
  } catch (e: any) {
    toast.error(e.message || 'Token 无效')
  } finally {
    verifying.value = false
  }
}

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(loginCode.value)
    toast.success('已复制')
  } catch {
    toast.error('复制失败')
  }
}

const copyGeneratedToken = async () => {
  try {
    await navigator.clipboard.writeText(generatedToken.value)
    toast.success('Token 已复制')
  } catch {
    toast.error('复制失败')
  }
}

const cleanup = () => {
  cleanupLogin()
  showAddInput.value = false
  addTokenInput.value = ''
}

watch(modelValue, (open) => {
  if (open) {
    handleOpen()
  } else {
    cleanup()
  }
})
</script>
