<template>
  <div class="min-h-screen bg-stone-50 dark:bg-neutral-950">
    <div class="pointer-events-none fixed inset-0 overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-stone-100/65 via-transparent to-amber-50/40 dark:from-neutral-900/60 dark:to-amber-950/20" />
      <div class="absolute -left-24 top-0 h-64 w-64 rounded-full bg-amber-300/20 blur-3xl dark:bg-amber-700/10" />
      <div class="absolute right-0 top-1/3 h-72 w-72 rounded-full bg-orange-300/20 blur-3xl dark:bg-orange-700/10" />
    </div>

    <div class="relative z-10 flex min-h-screen items-center justify-center px-4 py-10">
      <div class="w-full max-w-3xl">
        <div class="mb-8 text-center">
          <div class="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500 shadow-lg">
            <UIcon name="heroicons:cog-6-tooth" class="h-8 w-8 text-white" />
          </div>
          <h1 class="text-2xl font-bold font-serif text-stone-900 dark:text-white sm:text-3xl">画集管理后台</h1>
          <p class="mt-2 text-sm text-stone-500 dark:text-stone-400">选择登录方式进入管理控制台</p>
        </div>

        <div class="rounded-3xl border border-stone-200/70 bg-white/90 p-5 shadow-sm backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/80 sm:p-7">
          <div class="grid grid-cols-1 gap-7 md:grid-cols-2 md:gap-8">
            <section class="space-y-4 md:border-r md:border-stone-200 md:pr-8 md:dark:border-stone-700">
              <div class="flex flex-col items-center text-center">
                <div class="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 shadow-md">
                  <UIcon name="heroicons:shield-check" class="h-7 w-7 text-white" />
                </div>
                <h2 class="text-lg font-semibold text-stone-900 dark:text-white">主站授权登录</h2>
                <p class="mt-2 text-sm text-stone-500 dark:text-stone-400">已在主站登录管理员账号？一键授权即可进入画集后台。</p>
                <p v-if="ssoFailed" class="mt-3 text-sm text-amber-600 dark:text-amber-400">主站未登录或授权失败</p>
                <UButton color="primary" block class="mt-5" :loading="ssoLoading" @click="handleSsoLogin">
                  一键授权登录
                </UButton>
              </div>
            </section>

            <section class="space-y-4">
              <div class="flex flex-col items-center text-center">
                <div class="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100 dark:bg-neutral-800">
                  <UIcon name="heroicons:key" class="h-5 w-5 text-stone-600 dark:text-stone-300" />
                </div>
                <h2 class="text-lg font-semibold text-stone-900 dark:text-white">账号密码登录</h2>
              </div>

              <form @submit.prevent="handleLogin" class="space-y-4">
                <UFormGroup label="用户名">
                  <UInput v-model="form.username" placeholder="管理员用户名" icon="heroicons:user" />
                </UFormGroup>
                <UFormGroup label="密码">
                  <UInput v-model="form.password" type="password" placeholder="管理员密码" icon="heroicons:lock-closed" />
                </UFormGroup>
                <p v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</p>
                <UButton type="submit" color="gray" block :loading="loading">登录</UButton>
              </form>
            </section>
          </div>
        </div>

        <div class="mt-5 text-center">
          <NuxtLink
            to="/gallery-site/"
            class="text-sm text-stone-500 transition-colors hover:text-amber-600 dark:text-stone-400 dark:hover:text-amber-400"
          >
            ← 返回画集首页
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const router = useRouter()
const route = useRoute()
const runtimeConfig = useRuntimeConfig()
const apiBase = computed(() => (runtimeConfig.public.apiBase || '').replace(/\/$/, ''))

const resolveApiPath = (path: string) => {
  const base = apiBase.value
  if (!base) return path
  if (base.endsWith('/api') && path.startsWith('/api/')) {
    return `${base}${path.slice(4)}`
  }
  return `${base}${path}`
}

const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')
const ssoLoading = ref(false)
const ssoFailed = ref(!!route.query.sso_failed)

const resolveRedirectPath = () => {
  const raw = (route.query.redirect as string) || '/gallery-site/admin'
  return raw.startsWith('/') ? raw : '/gallery-site/admin'
}

// SSO 授权跳转
const handleSsoLogin = () => {
  ssoLoading.value = true
  const redirect = resolveRedirectPath()
  // 后端 /api/gallery-site/sso-redirect 期望 return_url 为相对路径
  const returnPath = `/gallery-site/admin/login?redirect=${encodeURIComponent(redirect)}`
  const ssoPath = resolveApiPath('/api/gallery-site/sso-redirect')
  window.location.href = `${ssoPath}?return_url=${encodeURIComponent(returnPath)}`
}

// 检查认证状态和 SSO token
onMounted(async () => {
  // 清除 URL 中的 sso_failed 参数
  if (route.query.sso_failed) {
    const query = { ...route.query }
    delete query.sso_failed
    router.replace({ path: route.path, query })
  }

  try {
    const { checkAuth } = useGallerySiteAdmin()
    const info = await checkAuth()
    if (info.authenticated) {
      router.replace('/gallery-site/admin')
      return
    }
  } catch { /* 未认证 */ }

  // 检查 URL 中的 SSO token
  const authToken = route.query.auth_token as string | undefined
  if (authToken) {
    loading.value = true
    try {
      const { authWithToken, checkAuth } = useGallerySiteAdmin()
      await authWithToken(authToken)
      const info = await checkAuth()
      useState<string>('gallery-site-admin-username', () => info.username || '').value = info.username || ''
      sessionStorage.removeItem('gallery-sso-attempted')
      const redirect = resolveRedirectPath()
      router.replace(redirect)
      return
    } catch {
      errorMsg.value = 'SSO 认证失败，请手动登录'
    } finally {
      loading.value = false
    }
  }
})

const handleLogin = async () => {
  errorMsg.value = ''
  if (!form.value.username || !form.value.password) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await $fetch<any>(resolveApiPath('/api/admin/login'), {
      method: 'POST',
      credentials: 'include',
      body: {
        username: form.value.username,
        password: form.value.password,
      }
    })
    if (res?.success) {
      useState<string>('gallery-site-admin-username', () => res.data?.username || '').value = res.data?.username || ''
      sessionStorage.removeItem('gallery-sso-attempted')
      const redirect = resolveRedirectPath()
      await navigateTo(redirect, { replace: true })
    } else {
      errorMsg.value = res?.message || '登录失败'
    }
  } catch (e: any) {
    const data = e?.data || e?.response?._data
    if (data?.locked) {
      errorMsg.value = `登录尝试过多，请 ${data.retry_after || 300} 秒后重试`
    } else {
      errorMsg.value = data?.message || '登录失败，请检查用户名和密码'
    }
  } finally {
    loading.value = false
  }
}
</script>
