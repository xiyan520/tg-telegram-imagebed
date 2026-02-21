<template>
  <div class="space-y-4">
    <!-- 顶部导航 + 画集信息 -->
    <div class="flex flex-col gap-3">
      <div class="flex items-center gap-3">
        <UButton icon="heroicons:arrow-left" color="gray" variant="ghost" @click="$emit('navigate', 'list')" />
        <div class="flex-1 min-w-0">
          <div class="group/name relative flex items-center gap-1">
            <input
              v-model="editName"
              type="text"
              class="text-lg font-bold bg-transparent border-none outline-none text-gray-900 dark:text-white w-full hover:underline hover:decoration-amber-400 hover:decoration-2 hover:underline-offset-4 focus:ring-2 focus:ring-amber-500/50 focus:rounded-md focus:px-2 focus:-mx-2 transition-all"
              placeholder="画集名称"
              @blur="saveName"
              @keyup.enter="($event.target as HTMLInputElement)?.blur()"
            />
            <UIcon name="heroicons:pencil" class="w-3.5 h-3.5 text-gray-400 opacity-0 group-hover/name:opacity-100 transition-opacity flex-shrink-0" />
          </div>
          <p class="text-sm text-gray-500">{{ gallery?.description || '' }} · {{ gallery?.image_count || 0 }} 张图片</p>
        </div>
        <div class="flex items-center gap-1">
          <UButton icon="heroicons:share" color="gray" variant="ghost" size="sm" title="分享" @click="showShare = true" />
          <UButton icon="heroicons:pencil-square" color="gray" variant="ghost" size="sm" title="编辑" @click="showEdit = true" />
          <UButton icon="heroicons:trash" color="red" variant="ghost" size="sm" title="删除" @click="showDelete = true" />
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
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

    <!-- 图片网格 -->
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

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex justify-center">
      <UPagination v-model="currentPage" :total="totalImages" :page-count="pageSize" @update:model-value="loadImages" />
    </div>

    <!-- 分享弹窗 -->
    <AlbumShareModal v-model="showShare" :gallery="gallery" @updated="loadGalleryInfo" />

    <!-- 编辑弹窗 -->
    <UModal v-model="showEdit">
      <UCard>
        <template #header><h3 class="text-lg font-semibold">编辑画集</h3></template>
        <form class="space-y-4" @submit.prevent="saveEdit">
          <UFormGroup label="名称">
            <UInput v-model="editFormName" :maxlength="100" />
          </UFormGroup>
          <UFormGroup label="描述">
            <UInput v-model="editFormDesc" :maxlength="500" />
          </UFormGroup>
        </form>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="showEdit = false">取消</UButton>
            <UButton color="primary" :loading="saving" @click="saveEdit">保存</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 删除确认 -->
    <UModal v-model="showDelete">
      <UCard>
        <template #header><h3 class="text-lg font-semibold text-red-600">删除画集</h3></template>
        <p>确定要删除画集「{{ gallery?.name }}」吗？此操作不可撤销，画集中的图片不会被删除。</p>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="showDelete = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="handleDelete">确认删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加图片弹窗 -->
    <UModal v-model="showAddImages" :ui="{ width: 'max-w-3xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">添加图片到画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="showAddImages = false" />
          </div>
        </template>
        <div v-if="uploadsLoading" class="flex justify-center py-8">
          <div class="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <div v-else-if="uploadsList.length === 0" class="text-center py-8 text-gray-500">
          暂无可添加的图片
        </div>
        <div v-else class="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 max-h-80 overflow-y-auto">
          <div
            v-for="img in uploadsList"
            :key="img.encrypted_id"
            class="relative aspect-square rounded-lg overflow-hidden border-2 cursor-pointer"
            :class="addImageIds.includes(img.encrypted_id) ? 'border-amber-500 ring-2 ring-amber-500/50' : 'border-gray-200 dark:border-gray-700'"
            @click="toggleAddImage(img.encrypted_id)"
          >
            <img :src="img.image_url" :alt="img.original_filename" class="w-full h-full object-cover" loading="lazy" />
            <div v-if="addImageIds.includes(img.encrypted_id)" class="absolute top-1 left-1">
              <div class="w-5 h-5 rounded bg-amber-500 flex items-center justify-center">
                <UIcon name="heroicons:check" class="w-3.5 h-3.5 text-white" />
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-between items-center">
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
  </div>
</template>

<script setup lang="ts">
import type { Gallery, GalleryImage } from '~/composables/useGalleryApi'

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

// 画集信息
const gallery = ref<Gallery | null>(null)
const editName = ref('')

// 图片列表
const loading = ref(false)
const images = ref<GalleryImage[]>([])
const totalImages = ref(0)
const currentPage = ref(1)
const pageSize = 50
const totalPages = computed(() => Math.max(1, Math.ceil(totalImages.value / pageSize)))

// 选择
const selectedIds = ref<string[]>([])
const selectAll = computed(() => images.value.length > 0 && selectedIds.value.length === images.value.length)

// 弹窗状态
const showShare = ref(false)
const showEdit = ref(false)
const showDelete = ref(false)
const showAddImages = ref(false)

// 编辑表单
const editFormName = ref('')
const editFormDesc = ref('')
const saving = ref(false)
const deleting = ref(false)

// 添加图片相关
const uploadsLoading = ref(false)
const uploadsList = ref<GalleryImage[]>([])
const addImageIds = ref<string[]>([])
const addingImages = ref(false)

const toggleSelect = (id: string) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

const toggleSelectAll = () => {
  if (selectAll.value) selectedIds.value = []
  else selectedIds.value = images.value.map(img => img.encrypted_id)
}

const toggleAddImage = (id: string) => {
  const idx = addImageIds.value.indexOf(id)
  if (idx >= 0) addImageIds.value.splice(idx, 1)
  else addImageIds.value.push(id)
}

// 加载画集信息
const loadGalleryInfo = async () => {
  try {
    gallery.value = await galleryApi.getGallery(props.galleryId)
    editName.value = gallery.value.name
    editFormName.value = gallery.value.name
    editFormDesc.value = gallery.value.description || ''
  } catch (e: any) {
    toast.error('加载画集失败', e.message)
  }
}

// 加载图片
const loadImages = async () => {
  loading.value = true
  selectedIds.value = []
  try {
    const data = await galleryApi.getGalleryImages(props.galleryId, currentPage.value, pageSize)
    images.value = data.items
    totalImages.value = data.total
  } catch (e: any) {
    toast.error('加载图片失败', e.message)
  } finally {
    loading.value = false
  }
}

const loadDetail = async () => {
  await Promise.all([loadGalleryInfo(), loadImages()])
}

// 保存名称（inline编辑）
const saveName = async () => {
  const name = editName.value.trim()
  if (!name || !gallery.value || name === gallery.value.name) return
  try {
    gallery.value = await galleryApi.updateGallery(props.galleryId, { name })
  } catch (e: any) {
    toast.error('保存失败', e.message)
    editName.value = gallery.value?.name || ''
  }
}

// 编辑弹窗保存
const saveEdit = async () => {
  saving.value = true
  try {
    gallery.value = await galleryApi.updateGallery(props.galleryId, {
      name: editFormName.value.trim(),
      description: editFormDesc.value.trim()
    })
    editName.value = gallery.value.name
    showEdit.value = false
    toast.success('保存成功')
  } catch (e: any) {
    toast.error('保存失败', e.message)
  } finally {
    saving.value = false
  }
}

// 删除画集
const handleDelete = async () => {
  deleting.value = true
  try {
    await galleryApi.deleteGallery(props.galleryId)
    toast.success('画集已删除')
    emit('navigate', 'list')
  } catch (e: any) {
    toast.error('删除失败', e.message)
  } finally {
    deleting.value = false
  }
}

// 移除选中图片（二次确认）
const confirmRemove = async () => {
  if (selectedIds.value.length === 0) return
  if (!confirm(`确定要从画集中移除 ${selectedIds.value.length} 张图片吗？`)) return
  try {
    const removed = await galleryApi.removeImagesFromGallery(props.galleryId, selectedIds.value)
    toast.success(`已移除 ${removed} 张图片`)
    selectedIds.value = []
    await loadDetail()
  } catch (e: any) {
    toast.error('移除失败', e.message)
  }
}

// 复制选中链接
const copySelectedLinks = () => {
  const links = images.value
    .filter(img => selectedIds.value.includes(img.encrypted_id))
    .map(img => img.image_url)
    .join('\n')
  clipboardCopy(links, `已复制 ${selectedIds.value.length} 个链接`)
}

// 设为封面
const handleSetCover = async (encryptedId: string) => {
  try {
    gallery.value = await galleryApi.setCover(props.galleryId, encryptedId)
    toast.success('封面已设置')
  } catch (e: any) {
    toast.error('设置封面失败', e.message)
  }
}

const handleViewImage = (imgs: GalleryImage[], idx: number) => {
  emit('view-image', imgs, idx)
}

// 打开添加图片弹窗时加载上传列表（排除已在画集中的图片）
watch(showAddImages, async (v) => {
  if (!v) return
  uploadsLoading.value = true
  addImageIds.value = []
  try {
    const data = await store.getUploads(1, 100)
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
  } catch { /* ignore */ } finally {
    uploadsLoading.value = false
  }
}
)

const handleAddImages = async () => {
  if (addImageIds.value.length === 0) return
  addingImages.value = true
  try {
    const result = await galleryApi.addImagesToGallery(props.galleryId, addImageIds.value)
    if (result.added > 0) {
      toast.success(`已添加 ${result.added} 张图片${result.skipped ? `，${result.skipped} 张已存在` : ''}`)
    } else if (result.skipped > 0) {
      toast.info(`所选图片均已在画集中`)
    } else {
      toast.warning('未能添加任何图片')
    }
    showAddImages.value = false
    await loadDetail()
  } catch (e: any) {
    toast.error('添加失败', e.message)
  } finally {
    addingImages.value = false
  }
}

// 监听编辑弹窗打开
watch(showEdit, (v) => {
  if (v && gallery.value) {
    editFormName.value = gallery.value.name
    editFormDesc.value = gallery.value.description || ''
  }
})

onMounted(loadDetail)
defineExpose({ refresh: loadDetail })
</script>

