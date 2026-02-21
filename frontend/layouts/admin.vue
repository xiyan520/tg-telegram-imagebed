<template>
  <AdminShell @open-settings="panelOpen = true">
    <slot />
  </AdminShell>

  <!-- 用户中心侧滑面板 -->
  <USlideover v-model="panelOpen" :ui="{ width: 'max-w-lg' }">
    <div class="flex flex-col h-full bg-white dark:bg-neutral-900">
      <!-- 头部 -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-stone-200 dark:border-neutral-700">
        <h2 class="text-lg font-semibold text-stone-900 dark:text-white">用户中心</h2>
        <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="panelOpen = false" />
      </div>

      <!-- 可滚动内容 -->
      <div class="flex-1 overflow-y-auto">
        <!-- 账户信息 -->
        <div class="px-5 py-4 border-b border-stone-100 dark:border-neutral-800">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-full flex items-center justify-center">
              <UIcon name="heroicons:user" class="w-6 h-6 text-white" />
            </div>
            <div class="flex-1">
              <p class="font-semibold text-stone-900 dark:text-white">{{ authStore.username }}</p>
              <p class="text-xs text-stone-500 dark:text-stone-400">管理员</p>
            </div>
            <UButton color="red" variant="soft" size="sm" @click="handleLogout">
              <template #leading><UIcon name="heroicons:arrow-right-on-rectangle" /></template>
              退出登录
            </UButton>
          </div>
        </div>

        <!-- Tab 切换 -->
        <div class="px-5 pt-3">
          <div class="flex gap-1 bg-stone-100 dark:bg-neutral-800 rounded-lg p-1">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              :class="activeTab === tab.key
                ? 'bg-white dark:bg-neutral-700 text-stone-900 dark:text-white shadow-sm'
                : 'text-stone-500 dark:text-stone-400 hover:text-stone-700 dark:hover:text-stone-300'"
              @click="activeTab = tab.key"
            >
              <UIcon :name="tab.icon" class="w-4 h-4" />
              <span class="hidden sm:inline">{{ tab.label }}</span>
            </button>
          </div>
        </div>

        <!-- Tab 内容 -->
        <div class="px-5 py-4">

          <!-- 修改凭据 -->
          <div v-if="activeTab === 'credentials'" class="space-y-4">
            <UFormGroup label="新用户名">
              <UInput v-model="settingsForm.username" placeholder="留空则不修改" />
            </UFormGroup>
            <UFormGroup label="新密码">
              <UInput v-model="settingsForm.password" type="password" placeholder="留空则不修改" />
              <template #hint>
                <span class="text-xs text-stone-500">至少 8 个字符，包含字母和数字</span>
              </template>
            </UFormGroup>
            <UFormGroup label="确认密码">
              <UInput v-model="settingsForm.confirmPassword" type="password" placeholder="再次输入新密码" />
            </UFormGroup>
            <UButton color="primary" block :loading="saving" @click="handleUpdateSettings">
              保存修改
            </UButton>
          </div>

          <!-- 活跃 Session -->
          <div v-else-if="activeTab === 'sessions'" class="space-y-3">
            <div class="flex items-center justify-between mb-1">
              <p class="text-sm text-stone-500 dark:text-stone-400">当前在线的管理会话</p>
              <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="xs" :loading="sessionsLoading" @click="loadSessions" />
            </div>
            <div v-if="sessionsLoading && sessions.length === 0" class="flex justify-center py-8">
              <div class="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else-if="sessions.length === 0" class="text-center py-8 text-stone-400 dark:text-stone-500 text-sm">
              暂无活跃会话
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="(s, i) in sessions"
                :key="i"
                class="flex items-center gap-3 p-3 rounded-lg border transition-colors"
                :class="s.is_current
                  ? 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20'
                  : 'border-stone-200 dark:border-neutral-700 bg-white dark:bg-neutral-800'"
              >
                <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                     :class="s.is_current ? 'bg-amber-500' : 'bg-stone-300 dark:bg-neutral-600'">
                  <UIcon name="heroicons:computer-desktop" class="w-4 h-4 text-white" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-stone-700 dark:text-stone-300">{{ s.ip }}</span>
                    <UBadge v-if="s.is_current" color="amber" variant="subtle" size="xs">当前</UBadge>
                  </div>
                  <p class="text-xs text-stone-400 dark:text-stone-500 mt-0.5">
                    登录 {{ s.login_time }} · 活跃 {{ s.last_active }}
                  </p>
                </div>
                <UButton
                  v-if="!s.is_current"
                  icon="heroicons:x-mark"
                  color="red"
                  variant="ghost"
                  size="xs"
                  @click="kickSession(s.token_prefix)"
                />
              </div>
            </div>
          </div>

          <!-- 安全日志 -->
          <div v-else-if="activeTab === 'logs'" class="space-y-3">
            <div class="flex items-center justify-between mb-1">
              <USelect
                v-model="logFilter"
                :options="logFilterOptions"
                option-attribute="label"
                value-attribute="value"
                size="xs"
                class="w-36"
              />
              <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="xs" :loading="logsLoading" @click="loadLogs" />
            </div>
            <div v-if="logsLoading && logs.length === 0" class="flex justify-center py-8">
              <div class="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else-if="filteredLogs.length === 0" class="text-center py-8 text-stone-400 dark:text-stone-500 text-sm">
              暂无日志记录
            </div>
            <div v-else class="space-y-1">
              <div
                v-for="(log, i) in paginatedLogs"
                :key="i"
                class="flex items-start gap-3 py-2.5 px-3 rounded-lg hover:bg-stone-50 dark:hover:bg-neutral-800/50 transition-colors"
              >
                <div class="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5"
                     :class="logMeta(log.type).bgClass">
                  <UIcon :name="logMeta(log.type).icon" class="w-3.5 h-3.5 text-white" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <UBadge :color="logMeta(log.type).color" variant="subtle" size="xs">{{ logMeta(log.type).label }}</UBadge>
                    <span v-if="log.username" class="text-xs font-medium text-stone-600 dark:text-stone-400">{{ log.username }}</span>
                  </div>
                  <div class="flex items-center gap-2 mt-1 text-xs text-stone-400 dark:text-stone-500">
                    <span>{{ log.ip }}</span>
                    <span>{{ log.time }}</span>
                  </div>
                </div>
              </div>
              <!-- 加载更多 -->
              <div v-if="filteredLogs.length > logsPageSize * logsPage" class="pt-2">
                <UButton color="gray" variant="ghost" size="xs" block @click="logsPage++">
                  加载更多（还有 {{ filteredLogs.length - logsPageSize * logsPage }} 条）
                </UButton>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </USlideover>
</template>

<script setup lang="ts">
const authStore = useAuthStore()
const notification = useNotification()
const runtimeConfig = useRuntimeConfig()

// ---- 面板状态 ----
const panelOpen = ref(false)
const activeTab = ref('credentials')

const tabs = [
  { key: 'credentials', label: '修改凭据', icon: 'heroicons:key' },
  { key: 'sessions', label: '在线会话', icon: 'heroicons:computer-desktop' },
  { key: 'logs', label: '安全日志', icon: 'heroicons:shield-check' },
]

// 切换 Tab 时自动加载数据
watch(activeTab, (tab) => {
  if (tab === 'sessions') loadSessions()
  if (tab === 'logs') loadLogs()
})

// 打开面板时重置
watch(panelOpen, (open) => {
  if (open) {
    settingsForm.value = { username: '', password: '', confirmPassword: '' }
    if (activeTab.value === 'sessions') loadSessions()
    if (activeTab.value === 'logs') loadLogs()
  }
})

// ---- 退出登录 ----
const handleLogout = async () => {
  panelOpen.value = false
  await authStore.logout()
  navigateTo('/admin')
}

// ---- 修改凭据 ----
const saving = ref(false)
const settingsForm = ref({ username: '', password: '', confirmPassword: '' })

const handleUpdateSettings = async () => {
  if (settingsForm.value.password && settingsForm.value.password !== settingsForm.value.confirmPassword) {
    notification.error('错误', '两次输入的密码不一致')
    return
  }
  saving.value = true
  try {
    await authStore.updateSettings(settingsForm.value)
    notification.success('成功', '设置已更新')
    settingsForm.value = { username: '', password: '', confirmPassword: '' }
  } catch (error: any) {
    notification.error('更新失败', error.message || '更新设置失败')
  } finally {
    saving.value = false
  }
}

// ---- 活跃 Session ----
const sessionsLoading = ref(false)
const sessions = ref<any[]>([])

const loadSessions = async () => {
  sessionsLoading.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/active-sessions`, {
      credentials: 'include'
    })
    if (res.success) sessions.value = res.data || []
  } catch { /* 静默 */ } finally {
    sessionsLoading.value = false
  }
}

const kickSession = async (tokenPrefix: string) => {
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/kick-session`, {
      method: 'POST',
      credentials: 'include',
      body: { token_prefix: tokenPrefix.replace(/\.+$/, '') }
    })
    if (res.success) {
      notification.success('已踢出', '会话已终止')
      loadSessions()
    }
  } catch {
    notification.error('操作失败', '无法踢出该会话')
  }
}

// ---- 安全日志 ----
const logsLoading = ref(false)
const logs = ref<any[]>([])
const logFilter = ref('all')
const logsPage = ref(1)
const logsPageSize = 30

const logFilterOptions = [
  { value: 'all', label: '全部事件' },
  { value: 'login_success', label: '登录成功' },
  { value: 'login_failed', label: '登录失败' },
  { value: 'login_locked', label: '登录锁定' },
  { value: 'logout', label: '主动登出' },
  { value: 'session_kicked', label: 'Session 踢出' },
  { value: 'password_changed', label: '密码修改' },
]

watch(logFilter, () => { logsPage.value = 1 })

const logMeta = (type: string) => {
  const map: Record<string, { label: string; icon: string; color: string; bgClass: string }> = {
    login_success:    { label: '登录成功', icon: 'heroicons:check-circle',              color: 'green',  bgClass: 'bg-gradient-to-br from-green-500 to-emerald-600' },
    login_failed:     { label: '登录失败', icon: 'heroicons:x-circle',                  color: 'red',    bgClass: 'bg-gradient-to-br from-red-500 to-rose-600' },
    login_locked:     { label: '登录锁定', icon: 'heroicons:lock-closed',               color: 'orange', bgClass: 'bg-gradient-to-br from-orange-500 to-amber-600' },
    logout:           { label: '主动登出', icon: 'heroicons:arrow-right-on-rectangle',  color: 'gray',   bgClass: 'bg-gradient-to-br from-stone-400 to-stone-500' },
    session_kicked:   { label: '会话踢出', icon: 'heroicons:user-minus',                color: 'amber',  bgClass: 'bg-gradient-to-br from-amber-500 to-yellow-600' },
    password_changed: { label: '密码修改', icon: 'heroicons:key',                       color: 'blue',   bgClass: 'bg-gradient-to-br from-blue-500 to-indigo-600' },
  }
  return map[type] || { label: type, icon: 'heroicons:information-circle', color: 'gray', bgClass: 'bg-gradient-to-br from-stone-400 to-stone-500' }
}

const filteredLogs = computed(() => {
  if (logFilter.value === 'all') return logs.value
  return logs.value.filter(l => l.type === logFilter.value)
})

const paginatedLogs = computed(() => filteredLogs.value.slice(0, logsPageSize * logsPage.value))

const loadLogs = async () => {
  logsLoading.value = true
  try {
    const res = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/security-log`, {
      credentials: 'include'
    })
    if (res.success) logs.value = res.data || []
  } catch { /* 静默 */ } finally {
    logsLoading.value = false
  }
}
</script>
