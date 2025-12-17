<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-stone-900 dark:text-white">画集管理</h1>
        <p class="text-sm text-stone-500 dark:text-stone-400 mt-1">
          共 {{ total }} 个画集
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="outline"
          :loading="loading"
          @click="loadGalleries"
        >
          刷新
        </UButton>
        <UButton
          icon="heroicons:plus"
          color="primary"
          @click="openCreateModal"
        >
          创建画集
        </UButton>
      </div>
    </div>

    <!-- 画集网格 -->
    <UCard>
      <div v-if="loading" class="flex flex-col justify-center items-center py-16">
        <div class="w-14 h-14 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-stone-600 dark:text-stone-400">加载中...</p>
      </div>

      <div v-else-if="galleries.length === 0" class="text-center py-16">
        <div class="w-20 h-20 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <UIcon name="heroicons:rectangle-stack" class="w-10 h-10 text-stone-400" />
        </div>
        <p class="text-lg font-medium text-stone-900 dark:text-white mb-2">暂无画集</p>
        <p class="text-sm text-stone-600 dark:text-stone-400">点击右上角"创建画集"开始使用</p>
      </div>

      <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        <NuxtLink
          v-for="gallery in galleries"
          :key="gallery.id"
          :to="`/admin/galleries/${gallery.id}`"
          class="group relative aspect-square rounded-xl overflow-hidden border-2 border-stone-200 dark:border-neutral-700 hover:border-amber-400 dark:hover:border-amber-500 transition-all hover:shadow-lg"
        >
          <!-- 封面图 -->
          <img
            v-if="gallery.cover_url"
            :src="gallery.cover_url"
            :alt="gallery.name"
            class="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-300"
          />
          <div
            v-else
            class="w-full h-full bg-gradient-to-br from-stone-100 to-stone-200 dark:from-neutral-800 dark:to-neutral-700 flex items-center justify-center"
          >
            <UIcon name="heroicons:photo" class="w-12 h-12 text-stone-400" />
          </div>

          <!-- 分享标记 -->
          <div v-if="gallery.share_enabled" class="absolute top-2 right-2 z-10">
            <UBadge color="green" variant="solid" size="xs" class="shadow-lg">
              <template #leading>
                <UIcon name="heroicons:share" class="w-3 h-3" />
              </template>
              已分享
            </UBadge>
          </div>

          <!-- 信息遮罩 -->
          <div class="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/80 via-black/50 to-transparent">
            <p class="text-white font-medium truncate">{{ gallery.name }}</p>
            <p class="text-stone-300 text-xs">{{ gallery.image_count }} 张图片</p>
          </div>
        </NuxtLink>
      </div>

      <!-- 分页 -->
      <template v-if="totalPages > 1" #footer>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-xs text-stone-500 dark:text-stone-400">
            第 {{ page }} / {{ totalPages }} 页
          </div>
          <UPagination v-model="page" :total="total" :page-count="pageSize" />
        </div>
      </template>
    </UCard>

    <!-- 创建画集模态框 -->
    <UModal v-model="createModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">创建画集</h3>
            <UButton
              icon="heroicons:x-mark"
              color="gray"
              variant="ghost"
              @click="createModalOpen = false"
            />
          </div>
        </template>

        <div class="space-y-4">
          <UFormGroup label="画集名称" required>
            <UInput
              v-model="createForm.name"
              placeholder="输入画集名称"
              :maxlength="100"
            />
          </UFormGroup>
          <UFormGroup label="描述" hint="可选">
            <UTextarea
              v-model="createForm.description"
              placeholder="输入画集描述"
              :rows="3"
              :maxlength="500"
            />
          </UFormGroup>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="createModalOpen = false">
              取消
            </UButton>
            <UButton
              color="primary"
              :loading="creating"
              :disabled="!createForm.name.trim()"
              @click="createGallery"
            >
              创建
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { Gallery } from '~/composables/useAdminGalleryApi'

definePageMeta({
  layout: 'admin',
  middleware: 'auth'
})

const notification = useNotification()
const galleryApi = useAdminGalleryApi()

const loading = ref(false)
const galleries = ref<Gallery[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const createModalOpen = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

const loadGalleries = async () => {
  loading.value = true
  try {
    const result = await galleryApi.getGalleries(page.value, pageSize.value)
    galleries.value = result.items
    total.value = result.total
  } catch (error: any) {
    notification.error('加载失败', error.message || '无法加载画集列表')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  createForm.value = { name: '', description: '' }
  createModalOpen.value = true
}

const createGallery = async () => {
  if (!createForm.value.name.trim()) return
  creating.value = true
  try {
    await galleryApi.createGallery(createForm.value.name, createForm.value.description)
    notification.success('创建成功', '画集已创建')
    createModalOpen.value = false
    await loadGalleries()
  } catch (error: any) {
    notification.error('创建失败', error.message || '无法创建画集')
  } finally {
    creating.value = false
  }
}

watch(page, loadGalleries)

onMounted(loadGalleries)
</script>
