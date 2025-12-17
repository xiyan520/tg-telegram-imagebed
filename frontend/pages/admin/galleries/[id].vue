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
          v-for="image in images"
          :key="image.encrypted_id"
          class="relative group aspect-square rounded-xl overflow-hidden border-2 transition-all hover:shadow-lg cursor-pointer"
          :class="[
            selectedImages.includes(image.encrypted_id)
              ? 'border-amber-500 ring-2 ring-amber-500 ring-offset-2'
              : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
          ]"
          @click="toggleSelection(image.encrypted_id)"
        >
          <img
            :src="image.image_url"
            :alt="image.original_filename"
            loading="lazy"
            class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
          />
          <div class="absolute top-2 left-2 z-10">
            <div class="bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm rounded-lg p-1.5 shadow-lg">
              <UCheckbox :model-value="selectedImages.includes(image.encrypted_id)" @click.stop />
            </div>
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
    <UModal v-model="editModalOpen">
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
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">分享画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="shareModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <div v-if="gallery?.share_enabled && gallery?.share_url" class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p class="text-sm font-medium text-green-800 dark:text-green-200 mb-2">分享链接</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-xs p-2 bg-white dark:bg-neutral-900 rounded break-all">{{ gallery.share_url }}</code>
              <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" size="sm" @click="copyShareUrl">复制</UButton>
            </div>
          </div>
          <div v-else class="text-center py-4">
            <p class="text-stone-600 dark:text-stone-400">点击下方按钮开启分享</p>
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
    <UModal v-model="addModalOpen" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">添加图片到画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="addModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">选择要添加到画集的图片（仅显示您上传的图片）</p>
          <div v-if="loadingUserImages" class="flex justify-center py-8">
            <div class="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <div v-else-if="userImages.length === 0" class="text-center py-8">
            <p class="text-stone-500">暂无可添加的图片</p>
          </div>
          <div v-else class="grid grid-cols-4 md:grid-cols-6 gap-2 max-h-96 overflow-y-auto">
            <div
              v-for="img in userImages"
              :key="img.encrypted_id"
              class="relative aspect-square rounded-lg overflow-hidden border-2 cursor-pointer transition-all"
              :class="[
                selectedToAdd.includes(img.encrypted_id)
                  ? 'border-amber-500 ring-2 ring-amber-500'
                  : 'border-stone-200 dark:border-neutral-700 hover:border-amber-400'
              ]"
              @click="toggleAddSelection(img.encrypted_id)"
            >
              <img :src="img.image_url" :alt="img.original_filename" class="w-full h-full object-cover" />
              <div v-if="selectedToAdd.includes(img.encrypted_id)" class="absolute inset-0 bg-amber-500/20 flex items-center justify-center">
                <UIcon name="heroicons:check-circle" class="w-8 h-8 text-amber-500" />
              </div>
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
  </div>
</template>

<script setup lang="ts">
import type { Gallery, GalleryImage } from '~/composables/useAdminGalleryApi'

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

const deleteModalOpen = ref(false)
const deleting = ref(false)

const addModalOpen = ref(false)
const userImages = ref<any[]>([])
const loadingUserImages = ref(false)
const selectedToAdd = ref<string[]>([])
const adding = ref(false)

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

const openEditModal = () => {
  editForm.value = { name: gallery.value?.name || '', description: gallery.value?.description || '' }
  editModalOpen.value = true
}

const saveEdit = async () => {
  saving.value = true
  try {
    gallery.value = await galleryApi.updateGallery(galleryId.value, editForm.value)
    notification.success('保存成功', '画集信息已更新')
    editModalOpen.value = false
  } catch (error: any) {
    notification.error('保存失败', error.message)
  } finally {
    saving.value = false
  }
}

const openShareModal = () => { shareModalOpen.value = true }

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

const openAddModal = async () => {
  addModalOpen.value = true
  selectedToAdd.value = []
  loadingUserImages.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/images`, {
      params: { limit: 200, page: 1 },
      credentials: 'include'
    })
    if (!response?.success) throw new Error(response?.error || '加载失败')
    const existingIds = new Set(images.value.map(i => i.encrypted_id))
    const imgs = response.data?.images || []
    userImages.value = imgs
      .map((img: any) => ({
        encrypted_id: img.encrypted_id,
        image_url: img.url,
        original_filename: img.original_filename || img.filename || img.encrypted_id
      }))
      .filter((u: any) => u.encrypted_id && !existingIds.has(u.encrypted_id))
  } catch (error: any) {
    notification.error('加载失败', error.message)
  } finally {
    loadingUserImages.value = false
  }
}

const toggleAddSelection = (id: string) => {
  const idx = selectedToAdd.value.indexOf(id)
  if (idx > -1) selectedToAdd.value.splice(idx, 1)
  else selectedToAdd.value.push(id)
}

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

watch(page, loadImages)

onMounted(async () => {
  await loadGallery()
  await loadImages()
})
</script>
