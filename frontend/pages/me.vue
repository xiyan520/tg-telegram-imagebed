<template>
  <div class="space-y-4">
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
        :has-unbound-tokens="hasUnboundTokens"
        :show-tg-action="tgEffective"
        @navigate="navigatePanel"
        @generate-token="handleQuickGenerate"
        @open-history="historyOpen = true"
      />

      <MeTokenPanel v-else-if="activePanel === 'tokens'" />

      <template v-else-if="activePanel === 'uploads'">
        <AlbumMyUploads :key="'uploads-' + refreshKey" @view-image="openLightbox" @navigate="() => {}" />
      </template>

      <template v-else-if="activePanel === 'galleries'">
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

      <MeTgBindPanel v-else-if="activePanel === 'tg'" />
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
    { key: 'tokens', label: 'Token 管理', icon: 'heroicons:key' },
    { key: 'uploads', label: '我的上传', icon: 'heroicons:cloud-arrow-up' },
    { key: 'galleries', label: '画集', icon: 'heroicons:photo' },
    {
      key: 'tg',
      label: 'TG 绑定',
      icon: 'heroicons:chat-bubble-left-right',
      hidden: !tgEffective.value,
      badge: hasUnboundTokens.value ? true : undefined
    },
  ]
  return items
})

const panelTitle = computed(() => {
  if (tgAuth.isLoggedIn && tgAuth.user) {
    return tgAuth.user.first_name || tgAuth.user.username || '游客控制台'
  }
  return '游客控制台'
})

const panelSubtitle = computed(() => {
  const tokenPart = `${tokenStore.vaultItems.length} 个 Token`
  const uploadPart = `${tokenStore.uploadCount} 次上传`
  const tgPart = tgAuth.isLoggedIn ? '已绑定 TG' : '未绑定 TG'
  return `${tokenPart} · ${uploadPart} · ${tgPart}`
})

const navigatePanel = (target: MeNavKey) => {
  activePanel.value = target
  if (target === 'galleries') {
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
    activePanel.value = 'tokens'
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

watch(() => tokenStore.token, (n, o) => {
  if (n === o) return
  galleryView.value = 'list'
  activeGalleryId.value = null
  refreshKey.value++
})

watch(activePanel, (panel) => {
  if (panel !== 'galleries') {
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

onMounted(async () => {
  await tokenStore.restoreToken()
  await loadSettings()
  if (publicSettings.value.tgAuthEnabled) {
    await tgAuth.checkSession()
    if (tgAuth.isLoggedIn) {
      await tgAuth.syncTokensToVault()
    }
  }
  if (!tokenStore.hasToken && !tgAuth.isLoggedIn) {
    navigateTo('/')
  }
})
</script>
