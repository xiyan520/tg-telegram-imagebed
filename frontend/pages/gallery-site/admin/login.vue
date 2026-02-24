<template>
  <div class="min-h-screen flex flex-col bg-stone-50 dark:bg-neutral-950">
    <!-- 背景装饰 -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute inset-0 bg-gradient-to-br from-stone-100/50 via-transparent to-amber-50/30 dark:from-neutral-900/50 dark:via-transparent dark:to-amber-950/20"></div>
    </div>

    <!-- 主内容区 -->
    <div class="flex-1 flex items-center justify-center px-4 relative z-10">
      <div class="w-full max-w-sm md:max-w-2xl">
        <!-- Logo -->
        <div class="text-center mb-8">
          <div class="inline-flex w-16 h-16 bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl items-center justify-center shadow-lg mb-4">
            <UIcon name="heroicons:cog-6-tooth" class="w-8 h-8 text-white" />
          </div>
          <h1 class="text-2xl font-bold font-serif text-stone-900 dark:text-white">画集管理后台</h1>
          <p class="text-sm text-stone-500 dark:text-stone-400 mt-2">选择登录方式</p>
        </div>

        <UCard>
          <div class="grid grid-cols-1 md:grid-cols-2">
            <!-- 左栏：主站授权登录 -->
            <div class="pr-0 md:pr-6 md:border-r md:border-stone-200 md:dark:border-stone-700">
              <div class="flex flex-col items-center text-center">
                <div class="inline-flex w-14 h-14 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl items-center justify-center shadow-md mb-4">
                  <UIcon name="heroicons:shield-check" class="w-7 h-7 text-white" />
                </div>
                <h2 class="text-lg font-semibold text-stone-900 dark:text-white mb-2">主站授权登录</h2>
                <p class="text-sm text-stone-500 dark:text-stone-400 mb-5">
                  已在主站登录管理员账号？一键授权即可进入画集管理后台
                </p>

                <p v-if="ssoFailed" class="text-sm text-amber-600 dark:text-amber-400 mb-3">
                  主站未登录或授权失败
                </p>

                <UButton
                  color="primary"
                  block
                  :loading="ssoLoading"
                  @click="handleSsoLogin"
                >
                  一键授权登录
                </UButton>
              </div>
            </div>

            <!-- 移动端分隔线 -->
            <div class="relative my-6 md:hidden">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-stone-200 dark:border-stone-700"></div>
              </div>
              <div class="relative flex justify-center">
                <span class="bg-white dark:bg-neutral-800 px-3 text-sm text-stone-500 dark:text-stone-400">或</span>
              </div>
            </div>

            <!-- 右栏：账号密码登录 -->
            <div class="pl-0 md:pl-6">
              <div class="flex flex-col items-center text-center mb-4">
                <div class="inline-flex w-10 h-10 bg-stone-100 dark:bg-neutral-800 rounded-lg items-center justify-center mb-3">
                  <UIcon name="heroicons:key" class="w-5 h-5 text-stone-600 dark:text-stone-300" />
                </div>
                <h2 class="text-lg font-semibold text-stone-900 dark:text-white">账号密码登录</h2>
              </div>

              <form @submit.prevent="handleLogin" class="space-y-4">
                <UFormGroup label="用户名">
                  <UInput
                    v-model="form.username"
                    placeholder="管理员用户名"
                    icon="heroicons:user"
                  />
                </UFormGroup>

                <UFormGroup label="密码">
                  <UInput
                    v-model="form.password"
                    type="password"
                    placeholder="管理员密码"
                    icon="heroicons:lock-closed"
                  />
                </UFormGroup>

                <p v-if="errorMsg" class="text-sm text-red-500">{{ errorMsg }}</p>

                <UButton type="submit" color="gray" block :loading="loading">
                  登录
                </UButton>
              </form>
            </div>
          </div>
        </UCard>

        <div class="text-center mt-4">
          <NuxtLink
            to="/gallery-site/"
            class="text-sm text-stone-500 dark:text-stone-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
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

const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')
const ssoLoading = ref(false)
const ssoFailed = ref(!!route.query.sso_failed)

// SSO 授权跳转
const handleSsoLogin = () => {
  ssoLoading.value = true
  const redirect = (route.query.redirect as string) || '/gallery-site/admin'
  const returnUrl = `${window.location.origin}/gallery-site/admin/login?redirect=${encodeURIComponent(redirect)}`
  window.location.href = `/api/gallery-site/sso-redirect?return_url=${encodeURIComponent(returnUrl)}`
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
      const redirect = (route.query.redirect as string) || '/gallery-site/admin'
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
    const res = await $fetch<any>('/api/admin/login', {
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
      const redirect = (route.query.redirect as string) || '/gallery-site/admin'
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
