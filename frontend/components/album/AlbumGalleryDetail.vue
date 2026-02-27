<template>
  <div class="space-y-4">
    <section class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 dark:border-neutral-700/80 dark:bg-neutral-900/85">
      <div class="flex flex-wrap items-center gap-3">
        <button
          class="h-9 w-9 rounded-xl border border-stone-200 bg-white text-stone-500 transition-colors hover:bg-stone-50 hover:text-stone-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-stone-300 dark:hover:bg-neutral-700 dark:hover:text-white"
          @click="$emit('navigate', 'list')"
        >
          <UIcon name="heroicons:arrow-left" class="mx-auto h-4 w-4" />
        </button>
        <div class="min-w-0 flex-1">
          <h2 class="truncate text-lg font-bold text-stone-900 dark:text-white">
            {{ gallery?.name || '画集详情' }}
          </h2>
          <p class="truncate text-xs text-stone-500 dark:text-stone-400">
            {{ gallery?.image_count || 0 }} 张图片 · 更新于 {{ formatDateTime(gallery?.updated_at) }}
          </p>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <UButton
            size="sm"
            color="gray"
            variant="soft"
            icon="heroicons:arrow-path"
            :loading="loading || settingsSaving"
            @click="loadDetail"
          >
            刷新
          </UButton>
          <UButton
            size="sm"
            color="gray"
            variant="soft"
            icon="heroicons:cog-6-tooth"
            @click="openSettings"
          >
            设置
          </UButton>
          <UButton
            size="sm"
            color="red"
            variant="soft"
            icon="heroicons:trash"
            @click="showDelete = true"
          >
            删除
          </UButton>
        </div>
      </div>
    </section>

    <div class="space-y-4">
      <section class="rounded-2xl border border-stone-200/80 bg-white/90 p-3 dark:border-neutral-700/80 dark:bg-neutral-900/85">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <UBadge :color="gallery?.share_enabled ? 'green' : 'gray'" variant="soft">
              {{ gallery?.share_enabled ? '分享已开启' : '分享未开启' }}
            </UBadge>
            <UBadge :color="settingsForm.mode === 'token' ? 'amber' : settingsForm.mode === 'password' ? 'amber' : 'blue'" variant="soft">
              {{ settingsForm.mode === 'token' ? 'Token 访问' : settingsForm.mode === 'password' ? '密码访问' : '公开访问' }}
            </UBadge>
          </div>
          <div class="flex items-center gap-2">
            <UButton
              size="xs"
              color="amber"
              variant="soft"
              icon="heroicons:sparkles"
              :disabled="images.length === 0"
              @click="openCoverRecommend"
            >
              推荐封面
            </UButton>
            <UButton
              size="xs"
              color="gray"
              variant="soft"
              :icon="gallery?.share_enabled ? 'heroicons:link-slash' : 'heroicons:link'"
              :loading="shareLoading"
              @click="toggleShare"
            >
              {{ gallery?.share_enabled ? '关闭分享' : '开启分享' }}
            </UButton>
          </div>
        </div>
      </section>

      <AlbumActionBar
        :selected-count="selectedIds.length"
        :total-count="images.length"
        :select-all="selectAll"
        :show-remove="true"
        :show-add-images="true"
        :loading="loading"
        @toggle-select-all="toggleSelectAll"
        @remove="confirmRemove"
        @copy-links="copySelectedLinks"
        @add-images="showAddImages = true"
        @refresh="loadDetail"
      />

      <AlbumImageGrid
        :images="images"
        :selected-ids="selectedIds"
        :loading="loading"
        :show-selection="true"
        :show-cover-badge="true"
        :cover-image-id="gallery?.cover_image"
        @toggle-select="toggleSelect"
        @view-image="handleViewImage"
        @set-cover="handleSetCover"
      />

      <div v-if="totalPages > 1" class="flex justify-center">
        <UPagination v-model="currentPage" :total="totalImages" :page-count="pageSize" @update:model-value="loadImages" />
      </div>
    </div>

    <UModal v-model="showSettings" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">画集设置</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="showSettings = false" />
          </div>
        </template>

        <div class="space-y-6">
          <div class="space-y-4">
            <h4 class="text-sm font-semibold uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">展示设置</h4>
            <UFormGroup label="画集标题" required>
              <UInput v-model="settingsForm.name" :maxlength="100" placeholder="请输入画集标题" />
            </UFormGroup>
            <UFormGroup label="画集描述">
              <UTextarea v-model="settingsForm.description" :rows="2" :maxlength="500" />
            </UFormGroup>
            <UFormGroup label="首页卡片副标题">
              <UInput v-model="settingsForm.cardSubtitle" :maxlength="120" placeholder="例如：编辑推荐 · 近期精选" />
            </UFormGroup>
            <div class="grid grid-cols-2 gap-2">
              <UFormGroup label="布局模式">
                <USelect v-model="settingsForm.layoutMode" :options="layoutModeOptions" value-attribute="value" option-attribute="label" />
              </UFormGroup>
              <UFormGroup label="图片排序">
                <USelect v-model="settingsForm.sortOrder" :options="sortOrderOptions" value-attribute="value" option-attribute="label" />
              </UFormGroup>
            </div>
            <UFormGroup label="主题色">
              <UInput v-model="settingsForm.themeColor" placeholder="#f59e0b" />
            </UFormGroup>
            <UFormGroup label="自定义头部文案">
              <UInput v-model="settingsForm.customHeaderText" :maxlength="200" placeholder="展示在分享页标题下方" />
            </UFormGroup>
            <div class="grid grid-cols-2 gap-2">
              <UCheckbox v-model="settingsForm.showImageInfo" label="显示图片信息" />
              <UCheckbox v-model="settingsForm.allowDownload" label="允许下载图片" />
              <UCheckbox v-model="settingsForm.nsfwWarning" label="启用 NSFW 提示" />
              <UCheckbox v-model="settingsForm.homepageExposeEnabled" label="允许首页曝光" />
            </div>
          </div>

          <div class="space-y-4 border-t border-stone-200 pt-4 dark:border-neutral-700">
            <h4 class="text-sm font-semibold uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">访问控制</h4>
            <UFormGroup label="访问模式">
              <USelect v-model="settingsForm.mode" :options="accessModeOptions" value-attribute="value" option-attribute="label" />
            </UFormGroup>
            <UFormGroup v-if="settingsForm.mode === 'password'" label="访问密码">
              <UInput
                v-model="settingsForm.password"
                type="password"
                :placeholder="gallery?.has_password ? '留空保持原密码' : '请输入访问密码'"
              />
            </UFormGroup>
            <UCheckbox v-model="settingsForm.hideFromShareAll" label="在全部分享中隐藏此画集" />
            <div v-if="settingsForm.mode === 'token'" class="space-y-2 rounded-xl border border-stone-200 bg-stone-50 p-2.5 dark:border-neutral-700 dark:bg-neutral-800/70">
              <p class="text-xs font-medium text-stone-600 dark:text-stone-300">Token 授权列表</p>
              <div class="flex gap-2">
                <UInput v-model="newToken" class="flex-1" placeholder="输入完整 Token" :disabled="addingToken" />
                <UButton size="xs" color="primary" :loading="addingToken" :disabled="!newToken.trim()" @click="handleAddToken">
                  添加
                </UButton>
              </div>
              <div v-if="loadingTokenAccess" class="flex justify-center py-2">
                <div class="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              </div>
              <div v-else-if="tokenAccessList.length === 0" class="rounded-lg bg-white/80 px-2 py-2 text-xs text-stone-500 dark:bg-neutral-900/60 dark:text-stone-400">
                暂无授权 Token
              </div>
              <div v-else class="max-h-40 space-y-1 overflow-y-auto">
                <div
                  v-for="item in tokenAccessList"
                  :key="`${item.token}-${item.created_at || ''}`"
                  class="flex items-center gap-2 rounded-lg bg-white/90 px-2 py-1.5 dark:bg-neutral-900/70"
                >
                  <code class="min-w-0 flex-1 truncate text-xs text-stone-600 dark:text-stone-300">{{ item.token_masked }}</code>
                  <UButton
                    size="xs"
                    color="red"
                    variant="ghost"
                    icon="heroicons:trash"
                    :loading="revokingToken === item.token"
                    @click="handleRevokeToken(item.token)"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-4 border-t border-stone-200 pt-4 dark:border-neutral-700">
            <h4 class="text-sm font-semibold uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">分享管理</h4>
            <p class="text-xs text-stone-500 dark:text-stone-400">开启后可通过单独链接访问该画集。</p>
            <div v-if="gallery?.share_enabled && gallery?.share_url" class="space-y-2 rounded-xl border border-green-200 bg-green-50 p-2.5 dark:border-green-800/60 dark:bg-green-900/15">
              <UInput :model-value="gallery.share_url" readonly />
              <UButton size="xs" color="green" variant="soft" icon="heroicons:clipboard-document" @click="copyShareUrl">
                复制分享链接
              </UButton>
            </div>
            <UButton
              block
              size="sm"
              :color="gallery?.share_enabled ? 'red' : 'primary'"
              :variant="gallery?.share_enabled ? 'soft' : 'solid'"
              :icon="gallery?.share_enabled ? 'heroicons:link-slash' : 'heroicons:link'"
              :loading="shareLoading"
              @click="toggleShare"
            >
              {{ gallery?.share_enabled ? '关闭分享' : '开启分享' }}
            </UButton>
          </div>

          <div class="space-y-4 border-t border-stone-200 pt-4 dark:border-neutral-700">
            <h4 class="text-sm font-semibold uppercase tracking-[0.16em] text-stone-500 dark:text-stone-400">SEO 与运营</h4>
            <div class="grid grid-cols-2 gap-2">
              <UFormGroup label="精选权重">
                <UInput v-model.number="settingsForm.editorPickWeight" type="number" :min="0" :max="1000" />
              </UFormGroup>
              <UFormGroup label="OG 图图片 ID">
                <UInput v-model="settingsForm.ogImageEncryptedId" placeholder="留空使用封面图" />
              </UFormGroup>
            </div>
            <UFormGroup label="SEO 标题">
              <UInput v-model="settingsForm.seoTitle" :maxlength="120" placeholder="留空使用画集标题" />
            </UFormGroup>
            <UFormGroup label="SEO 描述">
              <UTextarea v-model="settingsForm.seoDescription" :rows="2" :maxlength="300" placeholder="留空使用画集描述" />
            </UFormGroup>
            <UFormGroup label="SEO 关键词">
              <UInput v-model="settingsForm.seoKeywords" :maxlength="300" placeholder="如：插画,摄影,二次元" />
            </UFormGroup>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="showSettings = false">取消</UButton>
            <UButton
              size="md"
              color="primary"
              icon="heroicons:check"
              :loading="settingsSaving"
              @click="saveSettings"
            >
              保存设置
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="showDelete">
      <UCard>
        <template #header><h3 class="text-lg font-semibold text-red-600">删除画集</h3></template>
        <p class="text-sm text-stone-700 dark:text-stone-300">确定要删除画集「{{ gallery?.name }}」吗？此操作不可撤销，画集中的图片不会被删除。</p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="showDelete = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="handleDelete">确认删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="showAddImages" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">添加图片到画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="showAddImages = false" />
          </div>
        </template>
        <div v-if="uploadsLoading" class="flex justify-center py-8">
          <div class="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
        </div>
        <div v-else-if="uploadsList.length === 0" class="py-8 text-center text-gray-500">
          暂无可添加的图片
        </div>
        <div v-else class="grid max-h-80 grid-cols-3 gap-2 overflow-y-auto md:grid-cols-4 lg:grid-cols-5">
          <div
            v-for="img in uploadsList"
            :key="img.encrypted_id"
            class="relative aspect-square cursor-pointer overflow-hidden rounded-lg border-2"
            :class="addImageIds.includes(img.encrypted_id) ? 'border-amber-500 ring-2 ring-amber-500/50' : 'border-gray-200 dark:border-gray-700'"
            @click="toggleAddImage(img.encrypted_id)"
          >
            <img :src="img.image_url" :alt="img.original_filename" class="h-full w-full object-cover" loading="lazy" />
            <div v-if="addImageIds.includes(img.encrypted_id)" class="absolute left-1 top-1">
              <div class="flex h-5 w-5 items-center justify-center rounded bg-amber-500">
                <UIcon name="heroicons:check" class="h-3.5 w-3.5 text-white" />
              </div>
            </div>
          </div>
        </div>
        <div v-if="uploadsHasMore" class="mt-2 flex justify-center">
          <UButton size="sm" color="gray" variant="soft" :loading="uploadsLoadingMore" @click="loadMoreUploads">
            加载更多
          </UButton>
        </div>
        <template #footer>
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-500">已选 {{ addImageIds.length }} 张</span>
            <div class="flex gap-2">
              <UButton color="gray" variant="ghost" @click="showAddImages = false">取消</UButton>
              <UButton color="primary" :loading="addingImages" :disabled="addImageIds.length === 0" @click="handleAddImages">
                添加
              </UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="coverRecommendOpen" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">推荐封面</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="coverRecommendOpen = false" />
          </div>
        </template>
        <div v-if="recommendedCovers.length === 0" class="py-8 text-center text-stone-500">
          暂无推荐结果
        </div>
        <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div
            v-for="(img, i) in recommendedCovers"
            :key="img.encrypted_id"
            class="relative aspect-square cursor-pointer overflow-hidden rounded-xl border-2 transition-all hover:border-amber-500"
            :class="img.encrypted_id === gallery?.cover_image ? 'border-green-500 ring-2 ring-green-500' : 'border-stone-200 dark:border-neutral-700'"
            @click="handleSetCover(img.encrypted_id)"
          >
            <img :src="img.image_url" :alt="img.original_filename" class="h-full w-full object-cover" loading="lazy" />
            <div class="absolute left-1 top-1">
              <UBadge color="amber" variant="solid" size="xs">{{ i + 1 }}</UBadge>
            </div>
            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-1.5">
              <p class="truncate text-xs text-white">{{ img.original_filename }}</p>
            </div>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { Gallery, GalleryImage, GalleryTokenAccessItem } from '~/composables/useGalleryApi'
import { useCoverRecommend } from '~/composables/useCoverRecommend'

const props = defineProps<{ galleryId: number }>()
const emit = defineEmits<{
  (e: 'navigate', view: string): void
  (e: 'view-image', images: GalleryImage[], index: number): void
}>()

const toast = useLightToast()
const { copy: clipboardCopy } = useClipboardCopy()
const galleryApi = useGalleryApi()
const store = useTokenStore()
const config = useRuntimeConfig()
const baseURL = config.public.apiBase
const { recommend } = useCoverRecommend()

const gallery = ref<Gallery | null>(null)
const loading = ref(false)
const images = ref<GalleryImage[]>([])
const totalImages = ref(0)
const currentPage = ref(1)
const pageSize = 50
const totalPages = computed(() => Math.max(1, Math.ceil(totalImages.value / pageSize)))

const selectedIds = ref<string[]>([])
const selectAll = computed(() => images.value.length > 0 && selectedIds.value.length === images.value.length)

const showSettings = ref(false)
const showDelete = ref(false)
const deleting = ref(false)
const showAddImages = ref(false)

const shareLoading = ref(false)
const settingsSaving = ref(false)

const settingsForm = ref({
  name: '',
  description: '',
  mode: 'public' as 'public' | 'password' | 'token',
  password: '',
  hideFromShareAll: false,
  cardSubtitle: '',
  layoutMode: 'masonry' as 'masonry' | 'grid' | 'justified',
  sortOrder: 'newest' as 'newest' | 'oldest' | 'filename',
  themeColor: '',
  showImageInfo: true,
  allowDownload: true,
  nsfwWarning: false,
  homepageExposeEnabled: true,
  customHeaderText: '',
  editorPickWeight: 0,
  seoTitle: '',
  seoDescription: '',
  seoKeywords: '',
  ogImageEncryptedId: ''
})

const accessModeOptions = [
  { value: 'public', label: '公开访问' },
  { value: 'password', label: '密码保护' },
  { value: 'token', label: 'Token 授权' }
]
const layoutModeOptions = [
  { value: 'masonry', label: '瀑布流' },
  { value: 'grid', label: '网格' },
  { value: 'justified', label: '对齐布局' }
]
const sortOrderOptions = [
  { value: 'newest', label: '最新优先' },
  { value: 'oldest', label: '最早优先' },
  { value: 'filename', label: '文件名排序' }
]

const tokenAccessList = ref<GalleryTokenAccessItem[]>([])
const loadingTokenAccess = ref(false)
const newToken = ref('')
const addingToken = ref(false)
const revokingToken = ref('')

const coverRecommendOpen = ref(false)
const recommendedCovers = computed(() => recommend(images.value, 6))

const uploadsLoading = ref(false)
const uploadsLoadingMore = ref(false)
const uploadsList = ref<GalleryImage[]>([])
const addImageIds = ref<string[]>([])
const addingImages = ref(false)
const uploadsPage = ref(1)
const uploadsHasMore = ref(false)
const UPLOADS_PAGE_SIZE = 50

const formatDateTime = (value?: string) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const syncFormFromGallery = () => {
  const g = gallery.value
  if (!g) return
  settingsForm.value = {
    name: g.name || '',
    description: g.description || '',
    mode: (g.access_mode as 'public' | 'password' | 'token') || 'public',
    password: '',
    hideFromShareAll: Boolean(g.hide_from_share_all),
    cardSubtitle: g.card_subtitle || '',
    layoutMode: g.layout_mode || 'masonry',
    sortOrder: g.sort_order || 'newest',
    themeColor: g.theme_color || '',
    showImageInfo: Boolean(g.show_image_info ?? true),
    allowDownload: Boolean(g.allow_download ?? true),
    nsfwWarning: Boolean(g.nsfw_warning ?? false),
    homepageExposeEnabled: Boolean(g.homepage_expose_enabled ?? true),
    customHeaderText: g.custom_header_text || '',
    editorPickWeight: Number(g.editor_pick_weight ?? 0),
    seoTitle: g.seo_title || '',
    seoDescription: g.seo_description || '',
    seoKeywords: g.seo_keywords || '',
    ogImageEncryptedId: g.og_image_encrypted_id || ''
  }
}

const loadGalleryInfo = async () => {
  try {
    gallery.value = await galleryApi.getGallery(props.galleryId)
    syncFormFromGallery()
    if (settingsForm.value.mode === 'token') {
      await loadTokenAccess()
    } else {
      tokenAccessList.value = []
    }
  } catch (e: any) {
    toast.error('加载画集失败', e.message || '未知错误')
  }
}

const loadImages = async () => {
  loading.value = true
  selectedIds.value = []
  try {
    const data = await galleryApi.getGalleryImages(props.galleryId, currentPage.value, pageSize)
    images.value = data.items
    totalImages.value = data.total
  } catch (e: any) {
    toast.error('加载图片失败', e.message || '未知错误')
  } finally {
    loading.value = false
  }
}

const loadDetail = async () => {
  await Promise.all([loadGalleryInfo(), loadImages()])
}

const openSettings = async () => {
  showSettings.value = true
  if (settingsForm.value.mode === 'token') {
    await loadTokenAccess()
  }
}

const saveSettings = async () => {
  const name = settingsForm.value.name.trim()
  if (!name) {
    toast.error('保存失败', '画集标题不能为空')
    return
  }
  if (settingsForm.value.mode === 'password' && !settingsForm.value.password.trim() && !gallery.value?.has_password) {
    toast.error('保存失败', '密码模式下请设置访问密码')
    return
  }

  settingsSaving.value = true
  try {
    const accessPayload: {
      access_mode: 'public' | 'password' | 'token'
      hide_from_share_all: boolean
      password?: string
    } = {
      access_mode: settingsForm.value.mode,
      hide_from_share_all: settingsForm.value.hideFromShareAll
    }
    if (settingsForm.value.mode === 'password' && settingsForm.value.password.trim()) {
      accessPayload.password = settingsForm.value.password.trim()
    }

    gallery.value = await galleryApi.updateAccess(props.galleryId, accessPayload)
    gallery.value = await galleryApi.updateGallery(props.galleryId, {
      name,
      description: settingsForm.value.description.trim(),
      card_subtitle: settingsForm.value.cardSubtitle.trim(),
      layout_mode: settingsForm.value.layoutMode,
      sort_order: settingsForm.value.sortOrder,
      theme_color: settingsForm.value.themeColor.trim(),
      show_image_info: settingsForm.value.showImageInfo,
      allow_download: settingsForm.value.allowDownload,
      nsfw_warning: settingsForm.value.nsfwWarning,
      homepage_expose_enabled: settingsForm.value.homepageExposeEnabled,
      custom_header_text: settingsForm.value.customHeaderText.trim(),
      editor_pick_weight: settingsForm.value.editorPickWeight,
      seo_title: settingsForm.value.seoTitle.trim(),
      seo_description: settingsForm.value.seoDescription.trim(),
      seo_keywords: settingsForm.value.seoKeywords.trim(),
      og_image_encrypted_id: settingsForm.value.ogImageEncryptedId.trim() || null
    })

    syncFormFromGallery()
    if (settingsForm.value.mode === 'token') {
      await loadTokenAccess()
    }
    showSettings.value = false
    toast.success('保存成功')
  } catch (e: any) {
    toast.error('保存失败', e.message || '未知错误')
  } finally {
    settingsSaving.value = false
  }
}

const loadTokenAccess = async () => {
  if (settingsForm.value.mode !== 'token') return
  loadingTokenAccess.value = true
  try {
    tokenAccessList.value = await galleryApi.getTokenAccess(props.galleryId)
  } catch (e: any) {
    toast.error('加载授权列表失败', e.message || '未知错误')
  } finally {
    loadingTokenAccess.value = false
  }
}

const handleAddToken = async () => {
  const token = newToken.value.trim()
  if (!token) return
  addingToken.value = true
  try {
    await galleryApi.addTokenAccess(props.galleryId, token)
    newToken.value = ''
    await loadTokenAccess()
    toast.success('授权成功')
  } catch (e: any) {
    toast.error('授权失败', e.message || '未知错误')
  } finally {
    addingToken.value = false
  }
}

const handleRevokeToken = async (token: string) => {
  revokingToken.value = token
  try {
    await galleryApi.removeTokenAccess(props.galleryId, token)
    await loadTokenAccess()
    toast.success('已撤销授权')
  } catch (e: any) {
    toast.error('撤销失败', e.message || '未知错误')
  } finally {
    revokingToken.value = ''
  }
}

const toggleShare = async () => {
  if (!gallery.value || shareLoading.value) return
  shareLoading.value = true
  try {
    if (gallery.value.share_enabled) {
      await galleryApi.disableShare(props.galleryId)
      toast.success('分享已关闭')
    } else {
      await galleryApi.enableShare(props.galleryId)
      toast.success('分享已开启')
    }
    await loadGalleryInfo()
  } catch (e: any) {
    toast.error('操作失败', e.message || '未知错误')
  } finally {
    shareLoading.value = false
  }
}

const copyShareUrl = () => {
  const url = gallery.value?.share_url
  if (!url) return
  clipboardCopy(url, '链接已复制')
}

const handleDelete = async () => {
  deleting.value = true
  try {
    await galleryApi.deleteGallery(props.galleryId)
    toast.success('画集已删除')
    emit('navigate', 'list')
  } catch (e: any) {
    toast.error('删除失败', e.message || '未知错误')
  } finally {
    deleting.value = false
  }
}

const toggleSelect = (id: string) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

const toggleSelectAll = () => {
  if (selectAll.value) selectedIds.value = []
  else selectedIds.value = images.value.map(img => img.encrypted_id)
}

const confirmRemove = async () => {
  if (selectedIds.value.length === 0) return
  if (!confirm(`确定要从画集中移除 ${selectedIds.value.length} 张图片吗？`)) return
  try {
    const removed = await galleryApi.removeImagesFromGallery(props.galleryId, selectedIds.value)
    toast.success(`已移除 ${removed} 张图片`)
    await loadDetail()
  } catch (e: any) {
    toast.error('移除失败', e.message || '未知错误')
  }
}

const copySelectedLinks = () => {
  if (selectedIds.value.length === 0) return
  const links = images.value
    .filter(img => selectedIds.value.includes(img.encrypted_id))
    .map(img => img.image_url)
    .join('\n')
  clipboardCopy(links, `已复制 ${selectedIds.value.length} 个链接`)
}

const handleSetCover = async (encryptedId: string) => {
  try {
    gallery.value = await galleryApi.setCover(props.galleryId, encryptedId)
    syncFormFromGallery()
    toast.success('封面已设置')
  } catch (e: any) {
    toast.error('设置封面失败', e.message || '未知错误')
  }
}

const openCoverRecommend = () => {
  coverRecommendOpen.value = true
}

const handleViewImage = (imgs: GalleryImage[], idx: number) => {
  emit('view-image', imgs, idx)
}

const toggleAddImage = (id: string) => {
  const idx = addImageIds.value.indexOf(id)
  if (idx >= 0) addImageIds.value.splice(idx, 1)
  else addImageIds.value.push(id)
}

watch(showAddImages, async (v) => {
  if (!v) return
  uploadsLoading.value = true
  addImageIds.value = []
  uploadsList.value = []
  uploadsPage.value = 1
  uploadsHasMore.value = false
  try {
    const data = await store.getUploads(1, UPLOADS_PAGE_SIZE)
    const existingIds = new Set(images.value.map(img => img.encrypted_id))
    uploadsList.value = (data.uploads || [])
      .map((item: any) => ({
        encrypted_id: item.encrypted_id || item.file_id,
        original_filename: item.original_filename,
        file_size: item.file_size || 0,
        created_at: item.created_at,
        cdn_cached: item.cdn_cached || false,
        mime_type: item.mime_type || '',
        image_url: item.image_url || `${baseURL}/image/${item.encrypted_id || item.file_id}`,
        added_at: item.created_at
      } as GalleryImage))
      .filter(img => !existingIds.has(img.encrypted_id))
    uploadsHasMore.value = (data.uploads || []).length >= UPLOADS_PAGE_SIZE
  } catch {
    toast.error('加载上传记录失败')
  } finally {
    uploadsLoading.value = false
  }
})

const loadMoreUploads = async () => {
  if (uploadsLoadingMore.value || !uploadsHasMore.value) return
  uploadsLoadingMore.value = true
  try {
    const nextPage = uploadsPage.value + 1
    const data = await store.getUploads(nextPage, UPLOADS_PAGE_SIZE)
    const existingIds = new Set(images.value.map(img => img.encrypted_id))
    const newItems = (data.uploads || [])
      .map((item: any) => ({
        encrypted_id: item.encrypted_id || item.file_id,
        original_filename: item.original_filename,
        file_size: item.file_size || 0,
        created_at: item.created_at,
        cdn_cached: item.cdn_cached || false,
        mime_type: item.mime_type || '',
        image_url: item.image_url || `${baseURL}/image/${item.encrypted_id || item.file_id}`,
        added_at: item.created_at
      } as GalleryImage))
      .filter(img => !existingIds.has(img.encrypted_id))
    uploadsList.value.push(...newItems)
    uploadsPage.value = nextPage
    uploadsHasMore.value = (data.uploads || []).length >= UPLOADS_PAGE_SIZE
  } catch {
    toast.error('加载更多失败')
  } finally {
    uploadsLoadingMore.value = false
  }
}

const handleAddImages = async () => {
  if (addImageIds.value.length === 0) return
  addingImages.value = true
  try {
    const result = await galleryApi.addImagesToGallery(props.galleryId, addImageIds.value)
    if (result.added > 0) {
      toast.success(`已添加 ${result.added} 张图片${result.skipped ? `，${result.skipped} 张已存在` : ''}`)
    } else if (result.skipped > 0) {
      toast.info('所选图片均已在画集中')
    } else {
      toast.warning('未能添加任何图片')
    }
    showAddImages.value = false
    await loadDetail()
  } catch (e: any) {
    toast.error('添加失败', e.message || '未知错误')
  } finally {
    addingImages.value = false
  }
}

watch(currentPage, loadImages)
watch(() => settingsForm.value.mode, (mode) => {
  if (mode === 'token') {
    void loadTokenAccess()
  } else {
    tokenAccessList.value = []
    newToken.value = ''
  }
})

onMounted(loadDetail)

defineExpose({ refresh: loadDetail })
</script>
