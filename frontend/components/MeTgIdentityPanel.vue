<template>
  <UCard>
    <template #header>
      <div class="flex items-center justify-between gap-2">
        <h3 class="font-semibold text-stone-900 dark:text-white">TG 身份与绑定</h3>
        <UBadge :color="tgAuth.isLoggedIn ? 'green' : 'gray'" variant="soft" size="xs">
          {{ tgAuth.isLoggedIn ? '已登录' : '未登录' }}
        </UBadge>
      </div>
    </template>

    <div v-if="tgAuth.isLoggedIn && tgAuth.user" class="space-y-4">
      <div class="rounded-xl border border-cyan-200/80 dark:border-cyan-700/70 bg-cyan-50/70 dark:bg-cyan-900/20 p-4 flex items-center gap-3">
        <div class="w-11 h-11 rounded-full bg-cyan-500 text-white flex items-center justify-center text-lg font-bold">
          {{ (tgAuth.user.first_name || 'U')[0] }}
        </div>
        <div class="min-w-0">
          <p class="text-sm font-semibold text-stone-900 dark:text-stone-100 truncate">
            {{ tgAuth.user.first_name }}
            <span v-if="tgAuth.user.username" class="text-stone-500 font-normal">@{{ tgAuth.user.username }}</span>
          </p>
          <p class="text-xs text-stone-500 dark:text-stone-400 mt-1">
            Token 配额：{{ tgAuth.user.token_count }} / {{ tgAuth.user.max_tokens }}
          </p>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs font-medium uppercase tracking-wider text-stone-500 dark:text-stone-400">绑定中的 Token</p>
        <div v-if="boundTokenItems.length === 0" class="text-sm text-stone-400 py-4 text-center rounded-lg border border-dashed border-stone-300 dark:border-stone-700">
          当前没有绑定 Token
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="item in boundTokenItems"
            :key="item.id"
            class="rounded-lg border border-stone-200/80 dark:border-stone-700/80 p-3 flex items-center justify-between gap-3"
          >
            <div class="min-w-0">
              <code class="text-xs font-mono text-stone-600 dark:text-stone-400 truncate block">{{ maskToken(item.token) }}</code>
              <p class="text-xs text-stone-400 mt-1">
                {{ item.tokenInfo?.upload_count ?? 0 }} / {{ item.tokenInfo?.upload_limit ?? 0 }} 次上传
              </p>
            </div>
            <UButton
              size="xs"
              color="red"
              variant="soft"
              icon="heroicons:link-slash"
              :loading="unbindingTokenId === item.id"
              @click="unbindSingle(item)"
            >
              解绑
            </UButton>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <UButton color="red" variant="soft" size="sm" icon="heroicons:power" :loading="loggingOut" @click="logoutTgOnly">
          退出 TG 登录
        </UButton>
        <UButton
          v-if="boundTokenItems.length > 0"
          color="red"
          variant="outline"
          size="sm"
          icon="heroicons:trash"
          :loading="unbindingAll"
          @click="unbindAllAndLogout"
        >
          全部解绑并退出
        </UButton>
      </div>
    </div>

    <div v-else class="text-center py-8 space-y-3">
      <UIcon name="heroicons:shield-exclamation" class="w-8 h-8 text-stone-400 mx-auto" />
      <p class="text-sm text-stone-500 dark:text-stone-400">你还没有 TG 会话，先去“在线会话”里完成登录。</p>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import { maskToken } from '~/stores/token'

const toast = useLightToast()
const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const config = useRuntimeConfig()
const { logout: guestLogout } = useGuestAuth()

const unbindingTokenId = ref<string | null>(null)
const unbindingAll = ref(false)
const loggingOut = ref(false)

const boundTokenItems = computed(() =>
  tokenStore.vaultItems.filter(i => i.tokenInfo?.tg_user_id)
)

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
    await tgAuth.fetchSessions().catch(() => {})
  } catch (e: any) {
    toast.error(e.data?.error || e.message || '解绑失败')
  } finally {
    unbindingTokenId.value = null
  }
}

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
      } catch {
        // 单个失败继续处理
      }
    }
    await guestLogout()
    toast.success('已全部解绑并退出 TG')
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  } finally {
    unbindingAll.value = false
  }
}

const logoutTgOnly = async () => {
  loggingOut.value = true
  try {
    await tgAuth.logout()
    toast.success('已退出 TG 登录')
  } catch (e: any) {
    toast.error(e.message || '退出失败')
  } finally {
    loggingOut.value = false
  }
}
</script>

