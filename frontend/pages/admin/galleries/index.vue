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
          icon="heroicons:globe-alt"
          :color="shareAllLink?.enabled ? 'green' : 'gray'"
          variant="outline"
          @click="openShareAllModal"
        >
          {{ shareAllLink?.enabled ? '全部分享中' : '全部分享' }}
        </UButton>
        <UButton
          icon="heroicons:arrow-path"
          color="gray"
          variant="ghost"
          :loading="loading"
          @click="loadGalleries"
        />
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

    <!-- 全部分享管理模态框 -->
    <UModal v-model="shareAllModalOpen">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">全部分享管理</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="shareAllModalOpen = false" />
          </div>
        </template>

        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">
            开启后，所有已分享的画集将通过一个链接统一展示。新创建并分享的画集会自动加入。
          </p>

          <div v-if="shareAllLink?.enabled && shareAllLink?.share_url" class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <p class="text-sm font-medium text-green-800 dark:text-green-200 mb-2">全部分享链接</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-xs p-2 bg-white dark:bg-neutral-900 rounded break-all">{{ shareAllLink.share_url }}</code>
              <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" size="sm" @click="copyShareAllUrl">复制</UButton>
            </div>
          </div>

          <div v-if="!shareAllLink?.enabled" class="text-center py-4">
            <div class="w-16 h-16 bg-stone-100 dark:bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-3">
              <UIcon name="heroicons:globe-alt" class="w-8 h-8 text-stone-400" />
            </div>
            <p class="text-stone-600 dark:text-stone-400">点击下方按钮开启全部分享</p>
          </div>

          <UAlert v-if="shareAllLink?.enabled" color="amber" variant="soft" icon="heroicons:information-circle">
            <template #description>
              仅显示已开启分享且未隐藏的画集。设置为"仅管理员可见"或"隐藏"的画集不会出现在列表中。
            </template>
          </UAlert>
        </div>

        <template #footer>
          <div class="flex justify-between">
            <div>
              <UButton v-if="shareAllLink?.enabled" color="red" variant="soft" :loading="shareAllAction" @click="disableShareAll">
                关闭分享
              </UButton>
            </div>
            <div class="flex gap-2">
              <UButton v-if="shareAllLink?.enabled" color="gray" variant="outline" :loading="shareAllAction" @click="rotateShareAll">
                更换链接
              </UButton>
              <UButton v-if="!shareAllLink?.enabled" color="primary" :loading="shareAllAction" @click="enableShareAll">
                开启全部分享
              </UButton>
              <UButton v-else color="gray" variant="ghost" @click="shareAllModalOpen = false">关闭</UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>

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
import type { Gallery } from '~/composables/useGalleryApi'

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

// 全部分享
const shareAllModalOpen = ref(false)
const shareAllLink = ref<{ enabled: boolean; share_url?: string; share_token?: string } | null>(null)
const shareAllAction = ref(false)

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

// 全部分享功能
const config = useRuntimeConfig()

const loadShareAllLink = async () => {
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/share-all`, {
      credentials: 'include'
    })
    if (response.success) {
      shareAllLink.value = response.data.link
    }
  } catch (error) {
    console.error('加载全部分享链接失败:', error)
  }
}

const openShareAllModal = () => {
  shareAllModalOpen.value = true
}

const enableShareAll = async () => {
  shareAllAction.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/share-all`, {
      method: 'POST',
      credentials: 'include',
      body: { enabled: true }
    })
    if (response.success) {
      shareAllLink.value = response.data.link
      notification.success('开启成功', '全部分享已开启')
    }
  } catch (error: any) {
    notification.error('操作失败', error.data?.error || '无法开启全部分享')
  } finally {
    shareAllAction.value = false
  }
}

const disableShareAll = async () => {
  shareAllAction.value = true
  try {
    await $fetch<any>(`${config.public.apiBase}/api/admin/share-all`, {
      method: 'DELETE',
      credentials: 'include'
    })
    shareAllLink.value = null
    notification.success('已关闭', '全部分享已关闭')
    shareAllModalOpen.value = false
  } catch (error: any) {
    notification.error('操作失败', error.data?.error || '无法关闭全部分享')
  } finally {
    shareAllAction.value = false
  }
}

const rotateShareAll = async () => {
  shareAllAction.value = true
  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/share-all`, {
      method: 'POST',
      credentials: 'include',
      body: { enabled: true, rotate: true }
    })
    if (response.success) {
      shareAllLink.value = response.data.link
      notification.success('已更换', '分享链接已更换')
    }
  } catch (error: any) {
    notification.error('操作失败', error.data?.error || '无法更换链接')
  } finally {
    shareAllAction.value = false
  }
}

const copyShareAllUrl = async () => {
  if (!shareAllLink.value?.share_url) return
  try {
    await navigator.clipboard.writeText(shareAllLink.value.share_url)
    notification.success('已复制', '链接已复制到剪贴板')
  } catch {
    notification.error('复制失败', '请手动复制链接')
  }
}

watch(page, loadGalleries)

onMounted(() => {
  loadGalleries()
  loadShareAllLink()
})
</script>
