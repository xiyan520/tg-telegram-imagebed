<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3">
        <UButton icon="heroicons:arrow-left" color="gray" variant="ghost" to="/gallery-site/admin/galleries" />
        <div>
          <h1 class="text-2xl font-bold text-stone-900 dark:text-white">{{ gallery?.name || '画集详情' }}</h1>
          <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
            {{ gallery?.image_count || 0 }} 张图片 · 创建于 {{ formatDate(gallery?.created_at) }}
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          icon="heroicons:share"
          :color="gallery?.share_enabled ? 'green' : 'gray'"
          variant="outline"
          @click="shareOpen = true"
        >
          {{ gallery?.share_enabled ? '已分享' : '分享' }}
        </UButton>
        <UButton icon="heroicons:cog-6-tooth" color="gray" variant="outline" @click="openSettings">
          设置
        </UButton>
        <UButton icon="heroicons:trash" color="red" variant="outline" @click="deleteOpen = true">
          删除
        </UButton>
      </div>
    </div>

    <!-- 操作栏 -->
    <UCard>
      <div class="flex flex-col md:flex-row md:items-center gap-4">
        <div class="flex items-center gap-3">
          <UCheckbox v-model="selectAll" @change="handleSelectAll">
            <template #label><span class="text-sm font-medium">全选</span></template>
          </UCheckbox>
          <UButton color="red" variant="soft" size="sm" :disabled="selectedImages.length === 0" @click="removeSelected">
            <template #leading><UIcon name="heroicons:trash" /></template>
            移除选中 ({{ selectedImages.length }})
          </UButton>
        </div>
        <div class="flex items-center gap-2 md:ml-auto">
          <UButton icon="heroicons:sparkles" color="amber" variant="soft" size="sm" :disabled="images.length === 0" @click="openCoverRecommend">
            推荐封面
          </UButton>
          <UButton icon="heroicons:plus" color="primary" size="sm" @click="openAddModal">
            添加图片
          </UButton>
          <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="sm" :loading="loading" @click="loadImages" />
        </div>
      </div>
    </UCard>

    <!-- 图片网格 -->
    <UCard>
      <div v-if="loading" class="flex flex-col justify-center items-center py-16">
        <div class="w-16 h-16 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-stone-600 dark:text-stone-400">加载中...</p>
      </div>

      <div v-else-if="images.length === 0" class="text-center py-16">
        <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <UIcon name="heroicons:photo" class="w-10 h-10 text-stone-400" />
        </div>
        <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无图片</p>
        <p class="text-sm text-stone-600 dark:text-stone-400">点击"添加图片"将图片添加到画集</p>
      </div>

      <div v-else class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div
          v-for="(image, idx) in images"
          :key="image.encrypted_id"
          class="relative group aspect-square rounded-xl overflow-hidden border-2 transition-all hover:shadow-lg cursor-pointer"
          :class="[
            selectedImages.includes(image.encrypted_id)
              ? 'border-amber-500 ring-2 ring-amber-500 ring-offset-2'
              : image.encrypted_id === gallery?.cover_image
                ? 'border-green-500 ring-2 ring-green-500 ring-offset-2'
                : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
          ]"
          @click="openLightbox(idx)"
        >
          <img :src="getImageSrc(image)" :alt="image.original_filename" loading="lazy" class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300" />
          <!-- 封面标记 -->
          <div v-if="image.encrypted_id === gallery?.cover_image" class="absolute top-2 right-2 z-10">
            <div class="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full shadow-lg flex items-center gap-1">
              <UIcon name="heroicons:star-solid" class="w-3 h-3" /><span>封面</span>
            </div>
          </div>
          <!-- 选择框 -->
          <div class="absolute top-2 left-2 z-10" @click.stop>
            <div class="bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
              <UCheckbox :model-value="selectedImages.includes(image.encrypted_id)" @change="toggleSelection(image.encrypted_id)" />
            </div>
          </div>
          <!-- 设为封面按钮 -->
          <div v-if="image.encrypted_id !== gallery?.cover_image" class="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
            <UButton icon="heroicons:star" color="white" variant="solid" size="xs" :loading="settingCover === image.encrypted_id" @click.stop="setCoverImage(image.encrypted_id)">
              设为封面
            </UButton>
          </div>
          <div class="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <p class="text-white text-xs truncate">{{ image.original_filename }}</p>
          </div>
        </div>
      </div>

      <template v-if="totalPages > 1" #footer>
        <div class="flex justify-center pt-4">
          <div class="flex items-center gap-2">
            <UButton icon="heroicons:chevron-left" color="gray" variant="ghost" size="sm" :disabled="page <= 1" @click="page--" />
            <span class="text-sm text-stone-500">{{ page }} / {{ totalPages }}</span>
            <UButton icon="heroicons:chevron-right" color="gray" variant="ghost" size="sm" :disabled="page >= totalPages" @click="page++" />
          </div>
        </div>
      </template>
    </UCard>

    <!-- 设置模态框 -->
    <UModal v-model="settingsOpen" :prevent-close="addTokenOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">访问控制设置</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="settingsOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="访问模式">
            <USelect v-model="settingsForm.mode" :options="accessModeOptions" value-attribute="value" option-attribute="label" />
          </UFormGroup>
          <UFormGroup v-if="settingsForm.mode === 'password'" label="访问密码" required>
            <UInput v-model="settingsForm.password" type="password" :placeholder="gallery?.has_password ? '留空保持原密码' : '设置访问密码'" />
          </UFormGroup>
          <!-- Token 授权管理 -->
          <div v-if="settingsForm.mode === 'token'" class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-stone-700 dark:text-stone-300">已授权的 Token</span>
              <UButton size="xs" color="primary" variant="soft" @click="newToken = ''; addTokenOpen = true">
                <UIcon name="heroicons:plus" class="w-3.5 h-3.5 mr-1" />添加授权
              </UButton>
            </div>
            <div v-if="loadingTokenAccess" class="flex justify-center py-4">
              <div class="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else-if="tokenAccessList.length === 0" class="text-center py-4 text-sm text-stone-500">
              暂无授权的 Token，添加后才能通过 Token 访问此画集
            </div>
            <div v-else class="max-h-48 overflow-y-auto space-y-2">
              <div v-for="item in tokenAccessList" :key="item.token_masked" class="flex items-center justify-between p-2 bg-stone-50 dark:bg-neutral-800 rounded-lg">
                <div class="min-w-0 flex-1">
                  <code class="text-xs text-stone-600 dark:text-stone-400">{{ item.token_masked }}</code>
                  <p v-if="item.description" class="text-xs text-stone-500 truncate">{{ item.description }}</p>
                </div>
                <UButton icon="heroicons:trash" color="red" variant="ghost" size="xs" :loading="revokingToken === item.token" @click="handleRevokeToken(item.token)" />
              </div>
            </div>
          </div>
          <UCheckbox v-model="settingsForm.hideFromShareAll" label="在全部分享中隐藏此画集" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="settingsOpen = false">取消</UButton>
            <UButton color="primary" :loading="settingsSaving" @click="saveSettings">保存</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加 Token 授权模态框 -->
    <UModal v-model="addTokenOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">添加 Token 授权</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="addTokenOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">输入要授权访问此画集的 Token。授权后，持有该 Token 的用户可以查看此画集。</p>
          <UFormGroup label="Token" required>
            <UInput v-model="newToken" placeholder="输入完整的 Token（如 guest_xxx...）" :disabled="addingToken" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="addTokenOpen = false">取消</UButton>
            <UButton color="primary" :loading="addingToken" :disabled="!newToken.trim()" @click="handleAddToken">授权</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 分享模态框 -->
    <UModal v-model="shareOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">单独分享链接</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="shareOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">单独分享链接仅分享这一个画集。如需分享全部画集，请使用管理后台的"全部分享"功能。</p>
          <div v-if="gallery?.share_enabled && gallery?.share_url" class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p class="text-sm font-medium text-green-800 dark:text-green-200 mb-2">分享链接已开启</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-xs p-2 bg-white dark:bg-neutral-900 rounded break-all">{{ gallery.share_url }}</code>
              <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" size="sm" @click="copyShareUrl">复制</UButton>
            </div>
          </div>
          <div v-else class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg border border-stone-200 dark:border-neutral-700">
            <p class="text-sm text-stone-600 dark:text-stone-400">分享链接未开启，点击下方按钮开启。</p>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-between">
            <UButton v-if="gallery?.share_enabled" color="red" variant="soft" :loading="sharingAction" @click="handleDisableShare">关闭分享</UButton>
            <div v-else></div>
            <UButton v-if="!gallery?.share_enabled" color="primary" :loading="sharingAction" @click="handleEnableShare">开启分享</UButton>
            <UButton v-else color="gray" variant="ghost" @click="shareOpen = false">关闭</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加图片模态框 -->
    <UModal v-model="addModalOpen" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">添加图片到画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="addModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <UInput v-model="userImagesSearch" class="flex-1" icon="heroicons:magnifying-glass" placeholder="搜索文件名" :disabled="loadingUserImages" />
          </div>
          <div class="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
            <span>共 {{ userImagesTotal }} 张图片</span>
            <div class="flex items-center gap-2">
              <UButton size="xs" color="gray" variant="ghost" :disabled="loadingUserImages || userImages.length === 0" @click="toggleSelectAllUserImages">
                {{ allSelectableSelected ? '取消本页全选' : '全选本页' }}
              </UButton>
              <UButton size="xs" color="gray" variant="ghost" :disabled="selectedToAdd.length === 0" @click="selectedToAdd = []">清空选择</UButton>
            </div>
          </div>
          <div v-if="loadingUserImages" class="flex justify-center py-8">
            <div class="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div v-else-if="userImages.length === 0" class="text-center py-8">
            <p class="text-stone-500">暂无可添加的图片</p>
          </div>
          <div v-else class="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2 max-h-[400px] overflow-y-auto">
            <div
              v-for="img in userImages"
              :key="img.encrypted_id"
              class="relative aspect-square rounded-lg overflow-hidden border-2 cursor-pointer transition-all"
              :class="[
                isAlreadyInGallery(img.encrypted_id)
                  ? 'border-stone-200 dark:border-neutral-700 opacity-50 cursor-not-allowed'
                  : selectedToAdd.includes(img.encrypted_id)
                    ? 'border-amber-500 ring-2 ring-amber-500'
                    : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
              ]"
              @click="toggleAddSelection(img.encrypted_id)"
            >
              <img :src="getUserImageSrc(img)" :alt="img.original_filename" loading="lazy" class="w-full h-full object-cover" />
              <div v-if="isAlreadyInGallery(img.encrypted_id)" class="absolute inset-0 bg-black/40 flex items-center justify-center">
                <span class="text-white text-xs font-medium">已添加</span>
              </div>
              <div v-if="selectedToAdd.includes(img.encrypted_id) && !isAlreadyInGallery(img.encrypted_id)" class="absolute inset-0 bg-amber-500/20 flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-8 h-8 text-amber-500" />
              </div>
            </div>
          </div>
          <div v-if="userImagesTotalPages > 1" class="flex justify-center pt-2">
            <div class="flex items-center gap-2">
              <UButton icon="heroicons:chevron-left" color="gray" variant="ghost" size="xs" :disabled="userImagesPage <= 1" @click="userImagesPage--" />
              <span class="text-xs text-stone-500">{{ userImagesPage }} / {{ userImagesTotalPages }}</span>
              <UButton icon="heroicons:chevron-right" color="gray" variant="ghost" size="xs" :disabled="userImagesPage >= userImagesTotalPages" @click="userImagesPage++" />
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-between items-center">
            <span class="text-sm text-stone-500">已选择 {{ selectedToAdd.length }} 张</span>
            <div class="flex gap-2">
              <UButton color="gray" variant="ghost" @click="addModalOpen = false">取消</UButton>
              <UButton color="primary" :loading="adding" :disabled="selectedToAdd.length === 0" @click="addImages">添加</UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 删除确认模态框 -->
    <UModal v-model="deleteOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
        </template>
        <p class="text-stone-700 dark:text-stone-300">确定要删除画集"{{ gallery?.name }}"吗？此操作不可恢复，但不会删除画集内的图片。</p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="deleteOpen = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="confirmDelete">删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 推荐封面模态框 -->
    <UModal v-model="coverRecommendOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">推荐封面</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="coverRecommendOpen = false" />
          </div>
        </template>
        <div class="space-y-3">
          <p class="text-sm text-stone-600 dark:text-stone-400">根据文件大小、类型和文件名智能推荐，点击即可设为封面</p>
          <div v-if="recommendedCovers.length === 0" class="text-center py-6 text-stone-500">暂无足够图片进行推荐</div>
          <div v-else class="grid grid-cols-3 gap-3">
            <div
              v-for="(img, i) in recommendedCovers"
              :key="img.encrypted_id"
              class="relative aspect-square rounded-xl overflow-hidden border-2 cursor-pointer transition-all hover:border-amber-500 hover:shadow-lg"
              :class="img.encrypted_id === gallery?.cover_image ? 'border-green-500 ring-2 ring-green-500' : 'border-stone-200 dark:border-neutral-700'"
              @click="setCoverImage(img.encrypted_id)"
            >
              <img :src="getImageSrc(img)" :alt="img.original_filename" class="w-full h-full object-cover" loading="lazy" />
              <div class="absolute top-1 left-1"><UBadge color="amber" variant="solid" size="xs">{{ i + 1 }}</UBadge></div>
              <div v-if="img.encrypted_id === gallery?.cover_image" class="absolute inset-0 bg-green-500/20 flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-8 h-8 text-green-500" />
              </div>
              <div class="absolute bottom-0 left-0 right-0 p-1.5 bg-gradient-to-t from-black/70 to-transparent">
                <p class="text-white text-xs truncate">{{ img.original_filename }}</p>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end"><UButton color="gray" variant="ghost" @click="coverRecommendOpen = false">关闭</UButton></div>
        </template>
      </UCard>
    </UModal>

    <!-- 灯箱 -->
    <GalleryLightbox
      :open="lightboxOpen"
      :index="lightboxIndex"
      :images="lightboxImages"
      :show-admin-actions="true"
      @update:open="lightboxOpen = $event"
      @update:index="lightboxIndex = $event"
      @copy-link="handleLightboxCopyLink"
    />
  </div>
</template>

<script setup lang="ts">
import type { AdminGallerySiteItem, GalleryImageItem, TokenAccessItem } from '~/composables/useGallerySiteAdmin'
import { useCoverRecommend } from '~/composables/useCoverRecommend'

definePageMeta({
  layout: 'gallery-site-admin',
  middleware: 'gallery-site-admin-auth'
})

const route = useRoute()
const router = useRouter()
const notification = useNotification()
const config = useRuntimeConfig()
const {
  getGalleryDetail, deleteGallery,
  enableShare, disableShare, updateAccess,
  getTokenAccess, addTokenAccess, removeTokenAccess,
  getGalleryImages, addImagesToGallery, removeImagesFromGallery,
  setCover
} = useGallerySiteAdmin()

const galleryId = computed(() => Number(route.params.id))

// ===================== 画集数据 =====================
const loading = ref(false)
const gallery = ref<AdminGallerySiteItem | null>(null)
const images = ref<GalleryImageItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const selectedImages = ref<string[]>([])
const selectAll = ref(false)

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const joinUrl = (base: string, path: string) => `${String(base || '').replace(/\/$/, '')}${path}`

const normalizeImageSrc = (raw: string) => {
  if (!raw || !import.meta.client) return raw
  try {
    const u = new URL(raw, window.location.origin)
    const loc = window.location
    if (loc.protocol === 'https:' && u.protocol === 'http:' && u.host === loc.host) u.protocol = loc.protocol
    return u.toString()
  } catch { return raw }
}

const getImageSrc = (img: GalleryImageItem) =>
  normalizeImageSrc(img.cdn_url || img.url || joinUrl(config.public.apiBase, `/image/${img.encrypted_id}`))

const loadGallery = async () => {
  try {
    const res = await getGalleryDetail(galleryId.value, 1, 1)
    gallery.value = res.gallery
  } catch (e: any) {
    notification.error('加载失败', e.message)
    router.push('/gallery-site/admin/galleries')
  }
}

const loadImages = async () => {
  loading.value = true
  selectedImages.value = []
  selectAll.value = false
  try {
    const res = await getGalleryImages(galleryId.value, page.value, pageSize)
    images.value = res.items
    total.value = res.total
  } catch (e: any) {
    notification.error('加载失败', e.message)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (id: string) => {
  const idx = selectedImages.value.indexOf(id)
  if (idx > -1) selectedImages.value.splice(idx, 1)
  else selectedImages.value.push(id)
}

const handleSelectAll = () => {
  selectedImages.value = selectAll.value ? images.value.map(i => i.encrypted_id) : []
}

const removeSelected = async () => {
  if (selectedImages.value.length === 0) return
  try {
    await removeImagesFromGallery(galleryId.value, selectedImages.value)
    notification.success('移除成功', `已移除 ${selectedImages.value.length} 张图片`)
    await loadGallery()
    await loadImages()
  } catch (e: any) {
    notification.error('移除失败', e.message)
  }
}

// ===================== 封面设置 =====================
const settingCover = ref('')
const setCoverImage = async (encryptedId: string) => {
  if (settingCover.value) return
  settingCover.value = encryptedId
  try {
    gallery.value = await setCover(galleryId.value, encryptedId)
    notification.success('设置成功', '封面图片已更新')
  } catch (e: any) {
    notification.error('设置失败', e.message)
  } finally {
    settingCover.value = ''
  }
}

// ===================== 推荐封面 =====================
const { recommend } = useCoverRecommend()
const coverRecommendOpen = ref(false)
const recommendedCovers = ref<GalleryImageItem[]>([])

const openCoverRecommend = () => {
  recommendedCovers.value = recommend(images.value as any)
  coverRecommendOpen.value = true
}

// ===================== 添加图片 =====================
const addModalOpen = ref(false)
const loadingUserImages = ref(false)
const selectedToAdd = ref<string[]>([])
const adding = ref(false)

type AdminImageListItem = {
  encrypted_id: string
  original_filename: string
  url?: string
  cdn_url?: string
  cdn_cached?: boolean
}

const userImages = ref<AdminImageListItem[]>([])
const userImagesTotal = ref(0)
const userImagesPage = ref(1)
const userImagesPageSize = ref(60)
const userImagesSearch = ref('')
const userImagesTotalPages = computed(() => Math.max(1, Math.ceil(userImagesTotal.value / userImagesPageSize.value)))

const existingGalleryImageIds = ref<Set<string>>(new Set())
const isAlreadyInGallery = (id: string) => existingGalleryImageIds.value.has(id)

const getUserImageSrc = (img: AdminImageListItem) =>
  normalizeImageSrc(img.cdn_url || joinUrl(config.public.apiBase, `/image/${img.encrypted_id}`) || img.url)

let suppressWatch = false
let userImagesRequestSeq = 0

const loadAllGalleryImageIds = async () => {
  const ids = new Set<string>()
  let p = 1
  const limit = 200
  while (true) {
    try {
      const result = await getGalleryImages(galleryId.value, p, limit)
      for (const item of result.items) ids.add(item.encrypted_id)
      if (p * limit >= result.total) break
      p++
    } catch { break }
  }
  existingGalleryImageIds.value = ids
}

const loadUserImages = async () => {
  const req = ++userImagesRequestSeq
  loadingUserImages.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/gallery-site/admin/images`, {
      params: { limit: userImagesPageSize.value, page: userImagesPage.value, search: userImagesSearch.value.trim() },
      credentials: 'include'
    })
    if (req !== userImagesRequestSeq) return
    if (!response?.success) throw new Error(response?.error || '加载失败')
    userImages.value = (response.data?.images || [])
      .map((img: any) => ({
        encrypted_id: img.encrypted_id,
        url: img.url,
        cdn_url: img.cdn_url,
        cdn_cached: Boolean(img.cdn_cached ?? img.cached),
        original_filename: img.original_filename || img.filename || img.encrypted_id
      }))
      .filter((u: any) => u.encrypted_id)
    userImagesTotal.value = Number(response.data?.total || 0)
  } catch (e: any) {
    if (req === userImagesRequestSeq) notification.error('加载失败', e.message)
  } finally {
    if (req === userImagesRequestSeq) loadingUserImages.value = false
  }
}

const openAddModal = async () => {
  addModalOpen.value = true
  selectedToAdd.value = []
  suppressWatch = true
  userImagesPage.value = 1
  userImagesSearch.value = ''
  suppressWatch = false
  loadingUserImages.value = true
  await loadAllGalleryImageIds()
  await loadUserImages()
}

watch(addModalOpen, (isOpen) => {
  if (!isOpen) {
    if (searchDebounceTimer) { clearTimeout(searchDebounceTimer); searchDebounceTimer = undefined }
    userImagesRequestSeq++
  }
})

const toggleAddSelection = (id: string) => {
  if (isAlreadyInGallery(id)) return
  const idx = selectedToAdd.value.indexOf(id)
  if (idx > -1) selectedToAdd.value.splice(idx, 1)
  else selectedToAdd.value.push(id)
}

const selectableOnPage = computed(() =>
  userImages.value.map(i => i.encrypted_id).filter(id => id && !isAlreadyInGallery(id))
)
const allSelectableSelected = computed(() => {
  const s = selectableOnPage.value
  if (s.length === 0) return false
  const set = new Set(selectedToAdd.value)
  return s.every(id => set.has(id))
})
const toggleSelectAllUserImages = () => {
  const s = selectableOnPage.value
  const set = new Set(selectedToAdd.value)
  if (allSelectableSelected.value) { for (const id of s) set.delete(id) }
  else { for (const id of s) set.add(id) }
  selectedToAdd.value = Array.from(set)
}

let searchDebounceTimer: ReturnType<typeof setTimeout> | undefined
watch(userImagesSearch, () => {
  if (!addModalOpen.value || suppressWatch) return
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    if (!addModalOpen.value) return
    const needReset = userImagesPage.value !== 1
    userImagesPage.value = 1
    if (!needReset) void loadUserImages()
  }, 300)
})

watch(userImagesPage, () => {
  if (!addModalOpen.value || suppressWatch) return
  void loadUserImages()
})

const addImages = async () => {
  if (selectedToAdd.value.length === 0) return
  adding.value = true
  try {
    const result = await addImagesToGallery(galleryId.value, selectedToAdd.value)
    notification.success('添加成功', `已添加 ${result.added} 张图片`)
    addModalOpen.value = false
    await loadGallery()
    await loadImages()
  } catch (e: any) {
    notification.error('添加失败', e.message)
  } finally {
    adding.value = false
  }
}

// ===================== 设置模态框 =====================
const settingsOpen = ref(false)
const settingsForm = ref({ mode: 'public', password: '', hideFromShareAll: false })
const settingsSaving = ref(false)
const tokenAccessList = ref<TokenAccessItem[]>([])
const loadingTokenAccess = ref(false)
const addTokenOpen = ref(false)
const newToken = ref('')
const addingToken = ref(false)
const revokingToken = ref('')

const accessModeOptions = [
  { value: 'public', label: '公开访问' },
  { value: 'password', label: '密码保护' },
  { value: 'token', label: 'Token 授权' },
  { value: 'admin_only', label: '仅管理员可见' }
]

const openSettings = () => {
  settingsForm.value = {
    mode: gallery.value?.access_mode || 'public',
    password: '',
    hideFromShareAll: gallery.value?.hide_from_share_all || false
  }
  settingsOpen.value = true
  if (gallery.value?.access_mode === 'token') loadTokenList()
}

watch(() => settingsForm.value.mode, (m) => {
  if (m === 'token' && settingsOpen.value) loadTokenList()
})

const loadTokenList = async () => {
  loadingTokenAccess.value = true
  try { tokenAccessList.value = await getTokenAccess(galleryId.value) }
  catch (e: any) { console.error('加载 Token 列表失败:', e) }
  finally { loadingTokenAccess.value = false }
}

const saveSettings = async () => {
  settingsSaving.value = true
  try {
    const body: any = { access_mode: settingsForm.value.mode, hide_from_share_all: settingsForm.value.hideFromShareAll }
    if (settingsForm.value.mode === 'password' && settingsForm.value.password) body.password = settingsForm.value.password
    gallery.value = await updateAccess(galleryId.value, body)
    notification.success('已保存', '访问控制已更新')
    settingsOpen.value = false
  } catch (e: any) {
    notification.error('保存失败', e.message)
  } finally { settingsSaving.value = false }
}

const handleAddToken = async () => {
  if (!newToken.value.trim()) return
  addingToken.value = true
  try {
    await addTokenAccess(galleryId.value, newToken.value.trim())
    notification.success('授权成功', 'Token 已添加')
    addTokenOpen.value = false
    await loadTokenList()
  } catch (e: any) { notification.error('授权失败', e.message) }
  finally { addingToken.value = false }
}

const handleRevokeToken = async (token: string) => {
  revokingToken.value = token
  try {
    await removeTokenAccess(galleryId.value, token)
    notification.success('已撤销', 'Token 授权已移除')
    await loadTokenList()
  } catch (e: any) { notification.error('撤销失败', e.message) }
  finally { revokingToken.value = '' }
}

// ===================== 分享模态框 =====================
const shareOpen = ref(false)
const sharingAction = ref(false)

const handleEnableShare = async () => {
  sharingAction.value = true
  try {
    gallery.value = await enableShare(galleryId.value)
    notification.success('已开启', '分享链接已生成')
  } catch (e: any) { notification.error('操作失败', e.message) }
  finally { sharingAction.value = false }
}

const handleDisableShare = async () => {
  sharingAction.value = true
  try {
    gallery.value = await disableShare(galleryId.value)
    notification.success('已关闭', '分享链接已关闭')
    shareOpen.value = false
  } catch (e: any) { notification.error('操作失败', e.message) }
  finally { sharingAction.value = false }
}

const copyShareUrl = async () => {
  if (!gallery.value?.share_url) return
  try {
    await navigator.clipboard.writeText(gallery.value.share_url)
    notification.success('已复制', '链接已复制到剪贴板')
  } catch { notification.error('复制失败', '请手动复制链接') }
}

// ===================== 删除 =====================
const deleteOpen = ref(false)
const deleting = ref(false)

const confirmDelete = async () => {
  deleting.value = true
  try {
    await deleteGallery(galleryId.value)
    notification.success('已删除', `画集"${gallery.value?.name}"已删除`)
    router.push('/gallery-site/admin/galleries')
  } catch (e: any) { notification.error('删除失败', e.message) }
  finally { deleting.value = false }
}

// ===================== 灯箱 =====================
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxImages = computed(() =>
  images.value.map(img => ({ ...img, image_url: getImageSrc(img), original_filename: img.original_filename || img.encrypted_id }))
)
const openLightbox = (idx: number) => { lightboxIndex.value = idx; lightboxOpen.value = true }
const handleLightboxCopyLink = (image: any) => {
  const url = image.image_url || image.cdn_url
  if (url) navigator.clipboard.writeText(url).then(() => notification.success('已复制', '图片链接已复制')).catch(() => {})
}

watch(page, loadImages)

onMounted(async () => {
  await loadGallery()
  await loadImages()
})
</script>
