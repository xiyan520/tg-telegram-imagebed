<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3">
        <UButton
          icon="heroicons:arrow-left"
          color="gray"
          variant="ghost"
          to="/admin/galleries"
        />
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
          @click="openShareModal"
        >
          {{ gallery?.share_enabled ? '已分享' : '分享' }}
        </UButton>
        <UButton icon="heroicons:pencil" color="gray" variant="outline" @click="openEditModal">
          编辑
        </UButton>
        <UButton icon="heroicons:trash" color="red" variant="outline" @click="askDelete">
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
          <UButton
            color="red"
            variant="soft"
            size="sm"
            :disabled="selectedImages.length === 0"
            @click="removeSelected"
          >
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
          <img
            :src="getGalleryImageSrc(image)"
            :alt="image.original_filename"
            loading="lazy"
            class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
          />
          <!-- 封面标记 -->
          <div v-if="image.encrypted_id === gallery?.cover_image" class="absolute top-2 right-2 z-10">
            <div class="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full shadow-lg flex items-center gap-1">
              <UIcon name="heroicons:star-solid" class="w-3 h-3" />
              <span>封面</span>
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
            <UButton
              icon="heroicons:star"
              color="white"
              variant="solid"
              size="xs"
              :loading="settingCover === image.encrypted_id"
              @click.stop="setCoverImage(image.encrypted_id)"
            >
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
          <UPagination v-model="page" :total="total" :page-count="pageSize" />
        </div>
      </template>
    </UCard>

    <!-- 编辑画集模态框 -->
    <UModal v-model="editModalOpen" :prevent-close="addTokenModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">编辑画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="editModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <UFormGroup label="画集名称" required>
            <UInput v-model="editForm.name" placeholder="输入画集名称" :maxlength="100" />
          </UFormGroup>
          <UFormGroup label="描述" hint="可选">
            <UTextarea v-model="editForm.description" placeholder="输入画集描述" :rows="3" :maxlength="500" />
          </UFormGroup>

          <!-- 访问控制设置 -->
          <UDivider label="访问控制" />
          <p class="text-xs text-stone-500 dark:text-stone-400">控制通过分享链接访问此画集的权限</p>

          <UFormGroup label="访问模式">
            <USelectMenu
              v-model="accessForm.mode"
              :options="accessModeOptions"
              value-attribute="value"
              option-attribute="label"
            />
          </UFormGroup>

          <UFormGroup v-if="accessForm.mode === 'password'" label="访问密码" required>
            <UInput v-model="accessForm.password" type="password" placeholder="设置新密码（留空则保持原密码）" />
          </UFormGroup>

          <!-- Token 授权管理 -->
          <div v-if="accessForm.mode === 'token'" class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-stone-700 dark:text-stone-300">已授权的 Token</span>
              <UButton size="xs" color="primary" variant="soft" @click="openAddTokenModal">
                <UIcon name="heroicons:plus" class="w-3.5 h-3.5 mr-1" />
                添加授权
              </UButton>
            </div>
            <div v-if="loadingTokenAccess" class="flex justify-center py-4">
              <div class="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else-if="tokenAccessList.length === 0" class="text-center py-4 text-sm text-stone-500">
              暂无授权的 Token，添加后才能通过 Token 访问此画集
            </div>
            <div v-else class="max-h-48 overflow-y-auto space-y-2">
              <div
                v-for="item in tokenAccessList"
                :key="item.token_masked"
                class="flex items-center justify-between p-2 bg-stone-50 dark:bg-neutral-800 rounded-lg"
              >
                <div class="min-w-0 flex-1">
                  <code class="text-xs text-stone-600 dark:text-stone-400">{{ item.token_masked }}</code>
                  <p v-if="item.description" class="text-xs text-stone-500 truncate">{{ item.description }}</p>
                </div>
                <UButton
                  icon="heroicons:trash"
                  color="red"
                  variant="ghost"
                  size="xs"
                  :loading="revokingToken === item.token"
                  @click="revokeTokenAccess(item.token)"
                />
              </div>
            </div>
          </div>

          <UCheckbox v-model="accessForm.hideFromShareAll" label="在全部分享中隐藏此画集" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="editModalOpen = false">取消</UButton>
            <UButton color="primary" :loading="saving" :disabled="!editForm.name.trim()" @click="saveEdit">保存</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 分享模态框 -->
    <UModal v-model="shareModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">单独分享链接</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="shareModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">
            单独分享链接仅分享这一个画集。如需分享全部画集，请使用管理后台的"全部分享"功能。
          </p>

          <!-- 分享链接状态 -->
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
            <UButton v-if="gallery?.share_enabled" color="red" variant="soft" :loading="sharingAction" @click="disableShare">关闭分享</UButton>
            <div v-else></div>
            <UButton v-if="!gallery?.share_enabled" color="primary" :loading="sharingAction" @click="enableShare">开启分享</UButton>
            <UButton v-else color="gray" variant="ghost" @click="shareModalOpen = false">关闭</UButton>
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
          <!-- 搜索和筛选栏 -->
          <div class="space-y-3">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <UInput
                v-model="userImagesSearch"
                class="flex-1"
                icon="heroicons:magnifying-glass"
                placeholder="搜索文件名/用户名"
                :disabled="loadingUserImages"
              />
              <div class="flex items-center gap-2">
                <USelectMenu
                  v-model="userImagesFilter"
                  :options="userImagesFilterOptions"
                  value-attribute="value"
                  option-attribute="label"
                  :disabled="loadingUserImages"
                  class="w-28"
                />
                <USelectMenu
                  v-model="userImagesPageSize"
                  :options="userImagesPageSizeOptions"
                  value-attribute="value"
                  option-attribute="label"
                  :disabled="loadingUserImages"
                  class="w-24"
                />
              </div>
            </div>
            <div class="flex items-center justify-between text-xs text-stone-500 dark:text-stone-400">
              <span>共 {{ userImagesTotal }} 张图片</span>
              <div class="flex items-center gap-2">
                <UButton
                  size="xs"
                  color="gray"
                  variant="ghost"
                  :disabled="loadingUserImages || userImages.length === 0"
                  @click="toggleSelectAllOnUserImagesPage"
                >
                  {{ allSelectableOnPageSelected ? '取消本页全选' : '全选本页' }}
                </UButton>
                <UButton
                  size="xs"
                  color="gray"
                  variant="ghost"
                  :disabled="selectedToAdd.length === 0"
                  @click="clearAddSelection"
                >
                  清空选择
                </UButton>
              </div>
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
              <div
                v-if="selectedToAdd.includes(img.encrypted_id) && !isAlreadyInGallery(img.encrypted_id)"
                class="absolute inset-0 bg-amber-500/20 flex items-center justify-center"
              >
                <UIcon name="heroicons:check-circle" class="w-8 h-8 text-amber-500" />
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="userImagesTotalPages > 1" class="flex justify-center pt-2">
            <UPagination v-model="userImagesPage" :total="userImagesTotal" :page-count="userImagesPageSize" />
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
    <UModal v-model="deleteModalOpen">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
        </template>
        <p class="text-stone-700 dark:text-stone-300">确定要删除画集"{{ gallery?.name }}"吗？此操作不可恢复，但不会删除画集内的图片。</p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="confirmDelete">删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加 Token 授权模态框 -->
    <UModal v-model="addTokenModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">添加 Token 授权</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="addTokenModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">
            输入要授权访问此画集的 Token。授权后，持有该 Token 的用户可以查看此画集。
          </p>
          <UFormGroup label="Token" required>
            <UInput
              v-model="newTokenToAdd"
              placeholder="输入完整的 Token（如 guest_xxx...）"
              :disabled="addingToken"
            />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="addTokenModalOpen = false">取消</UButton>
            <UButton color="primary" :loading="addingToken" :disabled="!newTokenToAdd.trim()" @click="addTokenAccess">
              授权
            </UButton>
          </div>
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
          <div v-if="recommendedCovers.length === 0" class="text-center py-6 text-stone-500">
            暂无足够图片进行推荐
          </div>
          <div v-else class="grid grid-cols-3 gap-3">
            <div
              v-for="(img, i) in recommendedCovers"
              :key="img.encrypted_id"
              class="relative aspect-square rounded-xl overflow-hidden border-2 cursor-pointer transition-all hover:border-amber-500 hover:shadow-lg"
              :class="img.encrypted_id === gallery?.cover_image ? 'border-green-500 ring-2 ring-green-500' : 'border-stone-200 dark:border-neutral-700'"
              @click="setCoverFromRecommend(img.encrypted_id)"
            >
              <img :src="getGalleryImageSrc(img)" :alt="img.original_filename" class="w-full h-full object-cover" loading="lazy" />
              <div class="absolute top-1 left-1">
                <UBadge color="amber" variant="solid" size="xs">{{ i + 1 }}</UBadge>
              </div>
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
          <div class="flex justify-end">
            <UButton color="gray" variant="ghost" @click="coverRecommendOpen = false">关闭</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { Gallery, GalleryImage } from '~/composables/useGalleryApi'
import { useCoverRecommend } from '~/composables/useCoverRecommend'

definePageMeta({ layout: 'admin', middleware: 'auth' })

const route = useRoute()
const router = useRouter()
const notification = useNotification()
const galleryApi = useAdminGalleryApi()
const config = useRuntimeConfig()

const galleryId = computed(() => Number(route.params.id))

const loading = ref(false)
const gallery = ref<Gallery | null>(null)
const images = ref<GalleryImage[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const selectedImages = ref<string[]>([])
const selectAll = ref(false)

const editModalOpen = ref(false)
const editForm = ref({ name: '', description: '' })
const saving = ref(false)

const shareModalOpen = ref(false)
const sharingAction = ref(false)
const accessForm = ref({ mode: 'public', password: '', hideFromShareAll: false })
const accessModeOptions = [
  { value: 'public', label: '公开访问' },
  { value: 'password', label: '密码保护' },
  { value: 'token', label: 'Token 授权' },
  { value: 'admin_only', label: '仅管理员可见' }
]

const deleteModalOpen = ref(false)
const deleting = ref(false)

const addModalOpen = ref(false)
const loadingUserImages = ref(false)
const selectedToAdd = ref<string[]>([])
const adding = ref(false)

// 图片选择模态框状态
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
const userImagesFilter = ref<'all' | 'cached' | 'uncached' | 'group'>('all')
const userImagesTotalPages = computed(() => Math.max(1, Math.ceil(userImagesTotal.value / userImagesPageSize.value)))

const userImagesFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '已缓存', value: 'cached' },
  { label: '未缓存', value: 'uncached' },
  { label: '群组上传', value: 'group' }
]

const userImagesPageSizeOptions = [
  { label: '24/页', value: 24 },
  { label: '60/页', value: 60 },
  { label: '120/页', value: 120 }
]

const existingGalleryImageIds = ref<Set<string>>(new Set())
const isAlreadyInGallery = (encryptedId: string) => existingGalleryImageIds.value.has(encryptedId)

// URL处理函数
const joinUrl = (base: string, path: string) => `${String(base || '').replace(/\/$/, '')}${path}`

const normalizeImageSrc = (raw: string) => {
  if (!raw) return raw
  if (!import.meta.client) return raw
  try {
    const u = new URL(raw, window.location.origin)
    const loc = window.location
    if (loc.protocol === 'https:' && u.protocol === 'http:' && u.host === loc.host) u.protocol = loc.protocol
    return u.toString()
  } catch {
    return raw
  }
}

const getGalleryImageSrc = (image: GalleryImage) =>
  normalizeImageSrc(image.cdn_url || joinUrl(config.public.apiBase, `/image/${image.encrypted_id}`) || image.image_url)

const getUserImageSrc = (img: AdminImageListItem) =>
  normalizeImageSrc(img.cdn_url || joinUrl(config.public.apiBase, `/image/${img.encrypted_id}`) || img.url)

// Token 授权管理状态
const tokenAccessList = ref<any[]>([])
const loadingTokenAccess = ref(false)
const addTokenModalOpen = ref(false)
const newTokenToAdd = ref('')
const addingToken = ref(false)
const revokingToken = ref('')

// 封面设置状态
const settingCover = ref('')

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const loadGallery = async () => {
  try {
    gallery.value = await galleryApi.getGallery(galleryId.value)
  } catch (error: any) {
    notification.error('加载失败', error.message)
    router.push('/admin/galleries')
  }
}

const loadImages = async () => {
  loading.value = true
  selectedImages.value = []
  selectAll.value = false
  try {
    const result = await galleryApi.getGalleryImages(galleryId.value, page.value, pageSize.value)
    images.value = result.items
    total.value = result.total
  } catch (error: any) {
    notification.error('加载失败', error.message)
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
    await galleryApi.removeImagesFromGallery(galleryId.value, selectedImages.value)
    notification.success('移除成功', `已移除 ${selectedImages.value.length} 张图片`)
    await loadGallery()
    await loadImages()
  } catch (error: any) {
    notification.error('移除失败', error.message)
  }
}

const setCoverImage = async (encryptedId: string) => {
  if (settingCover.value) return
  settingCover.value = encryptedId
  try {
    gallery.value = await galleryApi.setCover(galleryId.value, encryptedId)
    notification.success('设置成功', '封面图片已更新')
  } catch (error: any) {
    notification.error('设置失败', error.message)
  } finally {
    settingCover.value = ''
  }
}

const openEditModal = () => {
  editForm.value = { name: gallery.value?.name || '', description: gallery.value?.description || '' }
  accessForm.value = {
    mode: gallery.value?.access_mode || 'public',
    password: '',
    hideFromShareAll: gallery.value?.hide_from_share_all || false
  }
  editModalOpen.value = true
  // 如果是 token 模式，加载 Token 授权列表
  if (accessForm.value.mode === 'token') {
    loadTokenAccessList()
  }
}

// 监听访问模式变化，当切换到 token 模式时加载列表
watch(() => accessForm.value.mode, (newMode) => {
  if (newMode === 'token' && editModalOpen.value) {
    loadTokenAccessList()
  }
})

const saveEdit = async () => {
  saving.value = true
  try {
    // 保存基本信息
    gallery.value = await galleryApi.updateGallery(galleryId.value, editForm.value)

    // 保存访问控制设置
    const accessBody: any = {
      access_mode: accessForm.value.mode,
      hide_from_share_all: accessForm.value.hideFromShareAll
    }
    if (accessForm.value.mode === 'password' && accessForm.value.password) {
      accessBody.password = accessForm.value.password
    }
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/galleries/${galleryId.value}/access`, {
      method: 'PATCH',
      credentials: 'include',
      body: accessBody
    })
    if (response.success) {
      gallery.value = { ...gallery.value, ...response.data.gallery }
    }

    notification.success('保存成功', '画集信息已更新')
    editModalOpen.value = false
    accessForm.value.password = ''
  } catch (error: any) {
    notification.error('保存失败', error.data?.error || error.message)
  } finally {
    saving.value = false
  }
}

const openShareModal = () => {
  shareModalOpen.value = true
}

const enableShare = async () => {
  sharingAction.value = true
  try {
    const result = await galleryApi.enableShare(galleryId.value)
    await loadGallery()
    notification.success('分享已开启', '分享链接已生成')
  } catch (error: any) {
    notification.error('操作失败', error.message)
  } finally {
    sharingAction.value = false
  }
}

const disableShare = async () => {
  sharingAction.value = true
  try {
    await galleryApi.disableShare(galleryId.value)
    await loadGallery()
    notification.success('分享已关闭', '')
    shareModalOpen.value = false
  } catch (error: any) {
    notification.error('操作失败', error.message)
  } finally {
    sharingAction.value = false
  }
}

const copyShareUrl = async () => {
  if (!gallery.value?.share_url) return
  try {
    await navigator.clipboard.writeText(gallery.value.share_url)
    notification.success('已复制', '分享链接已复制到剪贴板')
  } catch {
    notification.error('复制失败', '无法复制到剪贴板')
  }
}

const askDelete = () => { deleteModalOpen.value = true }

const confirmDelete = async () => {
  deleting.value = true
  try {
    await galleryApi.deleteGallery(galleryId.value)
    notification.success('删除成功', '画集已删除')
    router.push('/admin/galleries')
  } catch (error: any) {
    notification.error('删除失败', error.message)
  } finally {
    deleting.value = false
  }
}

// 加载所有已在画集中的图片ID（用于添加图片时的去重）
const loadingGalleryIds = ref(false)
const loadAllGalleryImageIds = async () => {
  loadingGalleryIds.value = true
  const ids = new Set<string>()
  let page = 1
  const limit = 200
  while (true) {
    try {
      const result = await galleryApi.getGalleryImages(galleryId.value, page, limit)
      for (const item of result.items) ids.add(item.encrypted_id)
      if (page * limit >= result.total) break
      page++
    } catch {
      break
    }
  }
  existingGalleryImageIds.value = ids
  loadingGalleryIds.value = false
}

let suppressUserImagesWatch = false

const openAddModal = async () => {
  addModalOpen.value = true
  selectedToAdd.value = []
  suppressUserImagesWatch = true
  userImagesPage.value = 1
  userImagesSearch.value = ''
  userImagesFilter.value = 'all'
  suppressUserImagesWatch = false
  loadingUserImages.value = true
  await loadAllGalleryImageIds()
  await loadUserImages()
}

// 关闭模态框时清理
watch(addModalOpen, (isOpen) => {
  if (!isOpen) {
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer)
      searchDebounceTimer = undefined
    }
    userImagesRequestSeq++
  }
})

const toggleAddSelection = (id: string) => {
  if (isAlreadyInGallery(id)) return
  const idx = selectedToAdd.value.indexOf(id)
  if (idx > -1) selectedToAdd.value.splice(idx, 1)
  else selectedToAdd.value.push(id)
}

const clearAddSelection = () => { selectedToAdd.value = [] }

const selectableUserImagesOnPage = computed(() =>
  userImages.value.map(i => i.encrypted_id).filter(id => id && !isAlreadyInGallery(id))
)

const allSelectableOnPageSelected = computed(() => {
  const selectable = selectableUserImagesOnPage.value
  if (selectable.length === 0) return false
  const selected = new Set(selectedToAdd.value)
  return selectable.every(id => selected.has(id))
})

const toggleSelectAllOnUserImagesPage = () => {
  const selectable = selectableUserImagesOnPage.value
  const selected = new Set(selectedToAdd.value)
  if (allSelectableOnPageSelected.value) {
    for (const id of selectable) selected.delete(id)
  } else {
    for (const id of selectable) selected.add(id)
  }
  selectedToAdd.value = Array.from(selected)
}

let userImagesRequestSeq = 0
const loadUserImages = async () => {
  const req = ++userImagesRequestSeq
  loadingUserImages.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/images`, {
      params: {
        limit: userImagesPageSize.value,
        page: userImagesPage.value,
        search: userImagesSearch.value.trim(),
        filter: userImagesFilter.value
      },
      credentials: 'include'
    })
    if (req !== userImagesRequestSeq) return
    if (!response?.success) throw new Error(response?.error || '加载失败')
    const imgs = response.data?.images || []
    userImages.value = imgs
      .map((img: any) => ({
        encrypted_id: img.encrypted_id,
        url: img.url,
        cdn_url: img.cdn_url,
        cdn_cached: Boolean(img.cdn_cached ?? img.cached),
        original_filename: img.original_filename || img.filename || img.encrypted_id
      }))
      .filter((u: any) => u.encrypted_id)
    userImagesTotal.value = Number(response.data?.total || 0)
  } catch (error: any) {
    if (req === userImagesRequestSeq) notification.error('加载失败', error.message)
  } finally {
    if (req === userImagesRequestSeq) loadingUserImages.value = false
  }
}

let searchDebounceTimer: ReturnType<typeof setTimeout> | undefined
watch(userImagesSearch, () => {
  if (!addModalOpen.value || suppressUserImagesWatch) return
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    if (!addModalOpen.value) return
    const needReset = userImagesPage.value !== 1
    userImagesPage.value = 1
    if (!needReset) void loadUserImages()
  }, 300)
})

watch(userImagesPage, () => {
  if (!addModalOpen.value || suppressUserImagesWatch) return
  void loadUserImages()
})

watch([userImagesPageSize, userImagesFilter], () => {
  if (!addModalOpen.value || suppressUserImagesWatch) return
  const needReset = userImagesPage.value !== 1
  userImagesPage.value = 1
  if (!needReset) void loadUserImages()
})

const addImages = async () => {
  if (selectedToAdd.value.length === 0) return
  adding.value = true
  try {
    const result = await galleryApi.addImagesToGallery(galleryId.value, selectedToAdd.value)
    notification.success('添加成功', `已添加 ${result.added} 张图片`)
    addModalOpen.value = false
    await loadGallery()
    await loadImages()
  } catch (error: any) {
    notification.error('添加失败', error.message)
  } finally {
    adding.value = false
  }
}

// ===================== Token 授权管理 =====================
const loadTokenAccessList = async () => {
  loadingTokenAccess.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/galleries/${galleryId.value}/access-tokens`, {
      credentials: 'include'
    })
    if (response.success) {
      tokenAccessList.value = response.data.items || []
    }
  } catch (error: any) {
    console.error('加载 Token 授权列表失败:', error)
  } finally {
    loadingTokenAccess.value = false
  }
}

const openAddTokenModal = () => {
  newTokenToAdd.value = ''
  addTokenModalOpen.value = true
}

const addTokenAccess = async () => {
  if (!newTokenToAdd.value.trim()) return
  addingToken.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/galleries/${galleryId.value}/access-tokens`, {
      method: 'POST',
      credentials: 'include',
      body: { token: newTokenToAdd.value.trim() }
    })
    if (response.success) {
      notification.success('授权成功', 'Token 已添加到授权列表')
      addTokenModalOpen.value = false
      newTokenToAdd.value = ''
      await loadTokenAccessList()
    } else {
      throw new Error(response.error || '授权失败')
    }
  } catch (error: any) {
    notification.error('授权失败', error.data?.error || error.message)
  } finally {
    addingToken.value = false
  }
}

const revokeTokenAccess = async (token: string) => {
  revokingToken.value = token
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/galleries/${galleryId.value}/access-tokens`, {
      method: 'DELETE',
      credentials: 'include',
      body: { token }
    })
    if (response.success) {
      notification.success('撤销成功', 'Token 授权已移除')
      await loadTokenAccessList()
    } else {
      throw new Error(response.error || '撤销失败')
    }
  } catch (error: any) {
    notification.error('撤销失败', error.data?.error || error.message)
  } finally {
    revokingToken.value = ''
  }
}

// ===================== 灯箱 =====================
const lightboxOpen = ref(false)
const lightboxIndex = ref(0)
const lightboxImages = computed(() =>
  images.value.map(img => ({
    ...img,
    image_url: getGalleryImageSrc(img),
  }))
)

const openLightbox = (idx: number) => {
  lightboxIndex.value = idx
  lightboxOpen.value = true
}

const handleLightboxCopyLink = (image: any) => {
  const url = image.image_url || image.cdn_url
  if (url) {
    navigator.clipboard.writeText(url).then(() => {
      notification.success('已复制', '图片链接已复制到剪贴板')
    }).catch(() => {})
  }
}

// ===================== 推荐封面 =====================
const { recommend } = useCoverRecommend()
const coverRecommendOpen = ref(false)
const recommendedCovers = ref<GalleryImage[]>([])

const openCoverRecommend = () => {
  recommendedCovers.value = recommend(images.value as any)
  coverRecommendOpen.value = true
}

const setCoverFromRecommend = async (encryptedId: string) => {
  await setCoverImage(encryptedId)
  // 不关闭弹窗，让用户看到选择结果
}

watch(page, loadImages)

onMounted(async () => {
  await loadGallery()
  await loadImages()
})
</script>
