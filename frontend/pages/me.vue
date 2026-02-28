<template>
  <div class="space-y-4 me-workbench">
    <UCard v-if="!tokenStore.hasToken && !tgAuth.isLoggedIn" class="shadow-sm">
      <div class="text-center py-8 space-y-4">
        <div class="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
          <UIcon name="heroicons:key" class="w-7 h-7 text-white" />
        </div>
        <div>
          <p class="text-lg font-semibold text-stone-900 dark:text-white">尚未登录</p>
          <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">请先从首页完成游客登录</p>
        </div>
        <UButton color="primary" @click="navigateTo('/')">返回首页</UButton>
      </div>
    </UCard>

    <MeConsoleShell
      v-else
      v-model="activePanel"
      :title="panelTitle"
      :subtitle="panelSubtitle"
      :items="navItems"
      :is-tg-logged-in="tgAuth.isLoggedIn"
      :show-logout="true"
      @logout="handleLogout"
    >
      <MeOverviewPanel
        v-if="activePanel === 'overview'"
        :is-tg-logged-in="tgAuth.isLoggedIn"
        :has-token="tokenStore.hasToken"
        :token-count="tokenStore.vaultItems.length"
        :upload-count="tokenStore.uploadCount"
        :upload-limit="tokenStore.uploadLimit"
        :remaining-uploads="tokenStore.remainingUploads"
        :session-count="tgAuth.onlineSessionCount || tgAuth.sessions.length"
        :has-unbound-tokens="hasUnboundTokens"
        :show-session-action="publicSettings.tgAuthEnabled"
        :show-tg-action="tgEffective"
        @navigate="navigatePanel"
        @generate-token="handleQuickGenerate"
        @open-history="historyOpen = true"
      />

      <template v-else-if="activePanel === 'assets'">
        <UCard class="asset-tab-shell">
          <div class="flex flex-wrap items-center gap-2">
            <UButton
              size="xs"
              :color="assetTab === 'tokens' ? 'primary' : 'gray'"
              :variant="assetTab === 'tokens' ? 'solid' : 'soft'"
              icon="heroicons:key"
              @click="assetTab = 'tokens'"
            >
              Token
            </UButton>
            <UButton
              size="xs"
              :color="assetTab === 'uploads' ? 'primary' : 'gray'"
              :variant="assetTab === 'uploads' ? 'solid' : 'soft'"
              icon="heroicons:cloud-arrow-up"
              @click="assetTab = 'uploads'"
            >
              上传
            </UButton>
            <UButton
              size="xs"
              :color="assetTab === 'galleries' ? 'primary' : 'gray'"
              :variant="assetTab === 'galleries' ? 'solid' : 'soft'"
              icon="heroicons:photo"
              @click="assetTab = 'galleries'"
            >
              画集
            </UButton>
          </div>
        </UCard>

        <MeTokenPanel v-if="assetTab === 'tokens'" />

        <template v-else-if="assetTab === 'uploads'">
          <AlbumMyUploads :key="'uploads-' + refreshKey" @view-image="openLightbox" @navigate="() => {}" />
        </template>

        <template v-else-if="assetTab === 'galleries'">
          <AlbumGalleryList
            v-if="galleryView === 'list'"
            :key="'gallery-list-' + refreshKey"
            @navigate="handleGalleryNavigate"
          />
          <AlbumGalleryDetail
            v-else-if="galleryView === 'detail' && activeGalleryId"
            :key="'gallery-detail-' + activeGalleryId + '-' + refreshKey"
            :gallery-id="activeGalleryId"
            @navigate="handleGalleryNavigate"
            @view-image="openLightbox"
          />
        </template>
      </template>

      <MeSessionPanel v-else-if="activePanel === 'sessions'" />

      <MeTgIdentityPanel v-else-if="activePanel === 'security'" />
    </MeConsoleShell>

    <HomeUploadHistory v-model:open="historyOpen" />
    <GalleryLightbox v-model:open="lightboxOpen" v-model:index="lightboxIndex" :images="lightboxImages" />
  </div>
</template>

<script setup lang="ts">
import type { GalleryImage } from '~/composables/useGalleryApi'
import type { MeNavItem, MeNavKey } from '~/components/MeConsoleShell.vue'

const tokenStore = useTokenStore()
const tgAuth = useTgAuthStore()
const { publicSettings, tgEffective, loadSettings, logout } = useGuestAuth()
const toast = useLightToast()

const activePanel = ref<MeNavKey>('overview')
const assetTab = ref<'tokens' | 'uploads' | 'galleries'>('tokens')
const refreshKey = ref(0)
const historyOpen = ref(false)
const generatingToken = ref(false)

const galleryView = ref<'list' | 'detail'>('list')
const activeGalleryId = ref<number | null>(null)

const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxImages = ref<GalleryImage[]>([])

const hasUnboundTokens = computed(() =>
  tgAuth.isLoggedIn && tokenStore.vaultItems.some(i => !i.tokenInfo?.tg_user_id)
)

const navItems = computed<MeNavItem[]>(() => {
  const items: MeNavItem[] = [
    { key: 'overview', label: '总览', icon: 'heroicons:home-modern' },
    { key: 'assets', label: '资产中心', icon: 'heroicons:squares-2x2' },
    {
      key: 'sessions',
      label: '在线会话',
      icon: 'heroicons:signal',
      hidden: !publicSettings.value.tgAuthEnabled,
      badge: tgAuth.onlineSessionCount > 0 ? tgAuth.onlineSessionCount : undefined
    },
    {
      key: 'security',
      label: '安全中心',
      icon: 'heroicons:shield-check',
      hidden: !tgEffective.value,
      badge: hasUnboundTokens.value ? true : undefined
    },
  ]
  return items
})

const panelTitle = computed(() => {
  if (tgAuth.isLoggedIn && tgAuth.user) {
    return tgAuth.user.first_name || tgAuth.user.username || '用户工作台'
  }
  return '用户工作台'
})

const panelSubtitle = computed(() => {
  const tokenPart = `${tokenStore.vaultItems.length} 个 Token`
  const uploadPart = `${tokenStore.uploadCount} 次上传`
  const sessionPart = tgAuth.isLoggedIn ? `${tgAuth.onlineSessionCount || tgAuth.sessions.length} 台在线设备` : '未登录 TG'
  return `${tokenPart} · ${uploadPart} · ${sessionPart}`
})

const navigatePanel = (target: MeNavKey) => {
  activePanel.value = target
  if (target !== 'assets') {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
}

const handleQuickGenerate = async () => {
  generatingToken.value = true
  try {
    await tokenStore.generateToken()
    await tgAuth.checkSession()
    toast.success('Token 已生成')
    activePanel.value = 'assets'
    assetTab.value = 'tokens'
  } catch (e: any) {
    toast.error(e.message || '生成 Token 失败')
  } finally {
    generatingToken.value = false
  }
}

const handleGalleryNavigate = (view: string, galleryId?: number) => {
  if (view === 'detail' && galleryId) {
    activeGalleryId.value = galleryId
    galleryView.value = 'detail'
  } else {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
}

const openLightbox = (images: GalleryImage[], index: number) => {
  lightboxImages.value = images
  lightboxIndex.value = index
  lightboxOpen.value = true
}

const handleLogout = async () => {
  await logout()
  navigateTo('/')
}

const pruneBoundTokensIfSessionLost = () => {
  if (tgAuth.isLoggedIn) return
  if (!publicSettings.value.tgAuthEnabled) return
  const removed = tokenStore.removeBoundTokens()
  if (removed > 0) {
    toast.info(`检测到 TG 会话失效，已移除 ${removed} 个绑定 Token`)
  }
}

watch(() => tokenStore.token, (n, o) => {
  if (n === o) return
  galleryView.value = 'list'
  activeGalleryId.value = null
  refreshKey.value++
})

watch(activePanel, (panel) => {
  if (panel !== 'assets') {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
})

watch(assetTab, (tab) => {
  if (tab !== 'galleries') {
    galleryView.value = 'list'
    activeGalleryId.value = null
  }
})

watch(navItems, (items) => {
  if (!items.some(i => i.key === activePanel.value && !i.hidden)) {
    activePanel.value = 'overview'
  }
})

watch(() => tokenStore.hasToken, (has) => {
  if (!has && !tgAuth.isLoggedIn) {
    navigateTo('/')
  }
})

watch(() => tgAuth.isLoggedIn, (loggedIn) => {
  if (!loggedIn) {
    pruneBoundTokensIfSessionLost()
  }
})

onMounted(async () => {
  await tokenStore.restoreToken()
  await loadSettings()
  if (publicSettings.value.tgAuthEnabled) {
    await tgAuth.checkSession()
    if (tgAuth.isLoggedIn) {
      await tgAuth.syncTokensToVault()
      await tgAuth.fetchSessions().catch(() => {})
    } else {
      pruneBoundTokensIfSessionLost()
    }
  }
  if (!tokenStore.hasToken && !tgAuth.isLoggedIn) {
    navigateTo('/')
  }
})
</script>

<style scoped lang="scss">
.me-workbench :deep(.asset-tab-shell) {
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.94), rgba(246, 249, 252, 0.88));
}

.dark .me-workbench :deep(.asset-tab-shell) {
  background: linear-gradient(120deg, rgba(24, 24, 27, 0.92), rgba(36, 36, 42, 0.88));
}
</style>
