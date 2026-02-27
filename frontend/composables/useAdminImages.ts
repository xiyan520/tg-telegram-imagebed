import type {
  AdminImageItem,
  AdminImagesQuery,
  AdminImageSortBy,
  AdminImageSortOrder,
} from '~/types/api'

export type AdminImagesViewMode = 'list' | 'grid' | 'masonry'
export type AdminLegacyFilter = 'all' | 'cached' | 'uncached' | 'group'

export interface AdminImagesAdvancedFilters {
  source: string
  cacheStatus: 'all' | 'cached' | 'uncached'
  dateFrom: string
  dateTo: string
  sizeMinMb: string
  sizeMaxMb: string
  accessMin: string
  accessMax: string
}

const VIEW_MODE_STORAGE_KEY = 'admin_images_view_mode'

const createDefaultAdvancedFilters = (): AdminImagesAdvancedFilters => ({
  source: 'all',
  cacheStatus: 'all',
  dateFrom: '',
  dateTo: '',
  sizeMinMb: '',
  sizeMaxMb: '',
  accessMin: '',
  accessMax: '',
})

const parsePositiveNumber = (value: string): number | undefined => {
  const trimmed = String(value || '').trim()
  if (!trimmed) return undefined
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed) || parsed < 0) return undefined
  return parsed
}

const asBytesFromMb = (valueMb: string): number | undefined => {
  const parsed = parsePositiveNumber(valueMb)
  if (parsed === undefined) return undefined
  return Math.round(parsed * 1024 * 1024)
}

export const useAdminImages = () => {
  const notification = useNotification()
  const runtimeConfig = useRuntimeConfig()
  const { getImages, deleteImages, clearCache } = useImageApi()

  const loading = ref(false)
  const refreshing = ref(false)
  const deleting = ref(false)

  const images = ref<AdminImageItem[]>([])
  const selectedIds = ref<string[]>([])

  const searchQuery = ref('')
  const primaryFilter = ref<AdminLegacyFilter>('all')
  const sortBy = ref<AdminImageSortBy>('created_at')
  const sortOrder = ref<AdminImageSortOrder>('desc')
  const advancedFilters = ref<AdminImagesAdvancedFilters>(createDefaultAdvancedFilters())

  const currentPage = ref(1)
  const totalPages = ref(1)
  const totalCount = ref(0)
  const pageSize = ref(50)

  const detailModalOpen = ref(false)
  const detailIndex = ref(-1)
  const selectedImage = ref<AdminImageItem | null>(null)
  const deleteModalOpen = ref(false)
  const deleteMessage = ref('')

  const advancedPanelOpen = ref(false)

  const tgSyncDeleteEnabled = ref(false)
  const deleteWithStorage = ref(true)

  const viewMode = ref<AdminImagesViewMode>('list')

  if (import.meta.client) {
    const saved = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    if (saved === 'list' || saved === 'grid' || saved === 'masonry') {
      viewMode.value = saved
    }
  }

  watch(viewMode, (value) => {
    if (import.meta.client) {
      localStorage.setItem(VIEW_MODE_STORAGE_KEY, value)
    }
  })

  const selectedCount = computed(() => selectedIds.value.length)
  const isAllOnPageSelected = computed(() => {
    if (!images.value.length) return false
    return images.value.every(item => selectedIds.value.includes(item.id))
  })
  const isPagePartiallySelected = computed(() => {
    if (!images.value.length) return false
    const selectedOnPage = images.value.filter(item => selectedIds.value.includes(item.id)).length
    return selectedOnPage > 0 && selectedOnPage < images.value.length
  })

  const hasActiveAdvancedFilters = computed(() => {
    const af = advancedFilters.value
    return af.source !== 'all'
      || af.cacheStatus !== 'all'
      || !!af.dateFrom
      || !!af.dateTo
      || !!String(af.sizeMinMb || '').trim()
      || !!String(af.sizeMaxMb || '').trim()
      || !!String(af.accessMin || '').trim()
      || !!String(af.accessMax || '').trim()
  })

  const hasPrevDetail = computed(() => detailIndex.value > 0)
  const hasNextDetail = computed(() => detailIndex.value >= 0 && detailIndex.value < images.value.length - 1)

  const pageSizeOptions = [
    { label: '20 / 页', value: 20 },
    { label: '50 / 页', value: 50 },
    { label: '100 / 页', value: 100 },
    { label: '200 / 页', value: 200 },
  ]

  const primaryFilterOptions = [
    { label: '全部图片', value: 'all' },
    { label: '已缓存', value: 'cached' },
    { label: '未缓存', value: 'uncached' },
    { label: '群组上传', value: 'group' },
  ]

  const sortByOptions = [
    { label: '按上传时间', value: 'created_at' },
    { label: '按文件大小', value: 'file_size' },
    { label: '按总访问量', value: 'access_count' },
    { label: '按 CDN 访问量', value: 'cdn_hit_count' },
    { label: '按直连访问量', value: 'direct_hit_count' },
  ]

  const sortOrderOptions = [
    { label: '降序', value: 'desc' },
    { label: '升序', value: 'asc' },
  ]

  const sourceOptions = [
    { label: '全部来源', value: 'all' },
    { label: 'Token 上传', value: 'token' },
    { label: '群组上传', value: 'group' },
    { label: '机器人上传', value: 'telegram_bot' },
    { label: '管理员上传', value: 'admin_upload' },
    { label: '匿名上传', value: 'guest' },
  ]

  const buildQueryParams = (): AdminImagesQuery => {
    const query: AdminImagesQuery = {
      page: currentPage.value,
      limit: Number(pageSize.value),
      search: searchQuery.value.trim(),
      filter: primaryFilter.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    }

    const af = advancedFilters.value

    if (af.source !== 'all') {
      query.source = af.source
    }

    if (af.cacheStatus === 'cached' || af.cacheStatus === 'uncached') {
      query.filter = af.cacheStatus
    }

    if (af.dateFrom) query.date_from = af.dateFrom
    if (af.dateTo) query.date_to = af.dateTo

    const sizeMin = asBytesFromMb(af.sizeMinMb)
    const sizeMax = asBytesFromMb(af.sizeMaxMb)
    const accessMin = parsePositiveNumber(af.accessMin)
    const accessMax = parsePositiveNumber(af.accessMax)

    if (sizeMin !== undefined) query.size_min = sizeMin
    if (sizeMax !== undefined) query.size_max = sizeMax
    if (accessMin !== undefined) query.access_min = Math.floor(accessMin)
    if (accessMax !== undefined) query.access_max = Math.floor(accessMax)

    return query
  }

  const clearSelection = () => {
    selectedIds.value = []
  }

  const toggleSelect = (id: string) => {
    const idx = selectedIds.value.indexOf(id)
    if (idx >= 0) {
      selectedIds.value.splice(idx, 1)
    } else {
      selectedIds.value.push(id)
    }
  }

  const toggleSelectAllOnPage = () => {
    if (isAllOnPageSelected.value) {
      const currentIds = new Set(images.value.map(item => item.id))
      selectedIds.value = selectedIds.value.filter(id => !currentIds.has(id))
      return
    }

    const merged = new Set(selectedIds.value)
    for (const item of images.value) {
      merged.add(item.id)
    }
    selectedIds.value = [...merged]
  }

  const loadSyncDeleteSetting = async () => {
    try {
      const resp = await $fetch<any>(`${runtimeConfig.public.apiBase}/api/admin/system/settings`, {
        credentials: 'include',
      })
      if (resp?.success) {
        tgSyncDeleteEnabled.value = resp.data?.tg_sync_delete_enabled === true
          || String(resp.data?.tg_sync_delete_enabled) === '1'
      }
    } catch {
      // 静默失败
    }
  }

  const fetchImages = async (opts: { silent?: boolean; keepSelection?: boolean } = {}) => {
    const silent = opts.silent ?? false
    const keepSelection = opts.keepSelection ?? false
    loading.value = true
    try {
      const data = await getImages(buildQueryParams())
      images.value = data.images || []
      totalPages.value = data.totalPages || 1
      totalCount.value = data.total ?? images.value.length
      if (!keepSelection) {
        clearSelection()
      }
    } catch (error) {
      if (!silent) {
        notification.error('错误', '加载图片列表失败')
      }
      console.error('加载图片列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  const refresh = async () => {
    refreshing.value = true
    await fetchImages({ silent: true, keepSelection: true })
    refreshing.value = false
    notification.success('已刷新', '图片数据已更新')
  }

  const applySearchDebounced = useDebounceFn(() => {
    currentPage.value = 1
    fetchImages()
  }, 400)

  const setSearchQuery = (value: string) => {
    searchQuery.value = value
    applySearchDebounced()
  }

  const applyPrimaryFilter = (value: AdminLegacyFilter) => {
    primaryFilter.value = value
    currentPage.value = 1
    fetchImages()
  }

  const applyPageSize = (value: number) => {
    pageSize.value = Number(value || 50)
    currentPage.value = 1
    fetchImages()
  }

  const applySorting = (nextSortBy: AdminImageSortBy, nextOrder: AdminImageSortOrder) => {
    sortBy.value = nextSortBy
    sortOrder.value = nextOrder
    currentPage.value = 1
    fetchImages()
  }

  const openAdvancedPanel = () => {
    advancedPanelOpen.value = true
  }

  const closeAdvancedPanel = () => {
    advancedPanelOpen.value = false
  }

  const applyAdvancedFilters = (next: AdminImagesAdvancedFilters) => {
    advancedFilters.value = { ...next }
    currentPage.value = 1
    advancedPanelOpen.value = false
    fetchImages()
  }

  const resetAdvancedFilters = () => {
    advancedFilters.value = createDefaultAdvancedFilters()
    currentPage.value = 1
    fetchImages()
  }

  const changePage = (page: number) => {
    currentPage.value = Math.max(1, Number(page || 1))
    fetchImages()
  }

  const setDetailByIndex = (index: number) => {
    if (index < 0 || index >= images.value.length) return false
    detailIndex.value = index
    selectedImage.value = images.value[index]
    return true
  }

  const openDetailById = (id: string) => {
    const targetId = String(id || '').trim()
    if (!targetId) return
    const index = images.value.findIndex(item => item.id === targetId)
    if (index < 0) return
    setDetailByIndex(index)
    detailModalOpen.value = true
  }

  const openDetail = (image: AdminImageItem) => {
    if (image?.id) {
      openDetailById(image.id)
      return
    }
    detailIndex.value = -1
    selectedImage.value = image
    detailModalOpen.value = true
  }

  const goPrevDetail = () => {
    if (!hasPrevDetail.value) return
    setDetailByIndex(detailIndex.value - 1)
  }

  const goNextDetail = () => {
    if (!hasNextDetail.value) return
    setDetailByIndex(detailIndex.value + 1)
  }

  const closeDetail = () => {
    detailModalOpen.value = false
  }

  const downloadImage = (image?: AdminImageItem | null) => {
    if (!import.meta.client) return
    const target = image || selectedImage.value
    if (!target?.url) {
      notification.error('下载失败', '当前图片链接无效')
      return
    }

    const fallbackName = `${target.id || 'image'}.jpg`
    const filename = String(target.filename || '').trim() || fallbackName

    try {
      const link = document.createElement('a')
      link.href = target.url
      link.download = filename
      link.rel = 'noopener'
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      link.remove()
      notification.success('开始下载', filename)
    } catch (error) {
      console.error('下载图片失败:', error)
      notification.error('下载失败', '无法触发浏览器下载，请稍后重试')
    }
  }

  const deleteCurrentDetailImage = () => {
    const target = selectedImage.value
    if (!target?.id) return
    openDeleteForSingle(target.id)
  }

  const handleDetailKeydown = (event: KeyboardEvent) => {
    if (!detailModalOpen.value) return
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      goPrevDetail()
      return
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      goNextDetail()
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      closeDetail()
    }
  }

  watch(detailModalOpen, (open) => {
    if (!import.meta.client) return
    if (open) {
      window.addEventListener('keydown', handleDetailKeydown)
      return
    }
    window.removeEventListener('keydown', handleDetailKeydown)
  })

  onBeforeUnmount(() => {
    if (!import.meta.client) return
    window.removeEventListener('keydown', handleDetailKeydown)
  })

  watch(images, () => {
    if (!detailModalOpen.value) return
    const currentId = selectedImage.value?.id
    if (!currentId) return
    const idx = images.value.findIndex(item => item.id === currentId)
    if (idx >= 0) {
      setDetailByIndex(idx)
      return
    }
    detailIndex.value = -1
    selectedImage.value = null
    closeDetail()
  })

  const copyImageUrl = async (url?: string | null) => {
    const val = String(url || '').trim()
    if (!val) return
    try {
      await navigator.clipboard.writeText(val)
      notification.success('已复制', '链接已复制到剪贴板')
    } catch {
      notification.error('复制失败', '请检查浏览器剪贴板权限')
    }
  }

  const copySelectedUrls = async () => {
    if (!selectedIds.value.length) return
    const selectedSet = new Set(selectedIds.value)
    const urls = images.value
      .filter(item => selectedSet.has(item.id))
      .map(item => String(item.url || '').trim())
      .filter(Boolean)

    if (!urls.length) {
      notification.error('复制失败', '当前选中项没有可用链接')
      return
    }

    try {
      await navigator.clipboard.writeText(urls.join('\n'))
      notification.success('已复制', `已复制 ${urls.length} 条链接`)
    } catch {
      notification.error('复制失败', '请检查浏览器剪贴板权限')
    }
  }

  const openDeleteForSingle = (id: string) => {
    selectedIds.value = [id]
    deleteWithStorage.value = true
    deleteMessage.value = '确定要删除这张图片吗？此操作不可恢复。'
    deleteModalOpen.value = true
  }

  const openDeleteForSelection = () => {
    if (!selectedIds.value.length) return
    deleteWithStorage.value = true
    deleteMessage.value = `确定要删除选中的 ${selectedIds.value.length} 张图片吗？此操作不可恢复。`
    deleteModalOpen.value = true
  }

  const closeDeleteModal = () => {
    deleteModalOpen.value = false
  }

  const confirmDelete = async () => {
    if (!selectedIds.value.length) return
    deleting.value = true
    try {
      const deletingCount = selectedIds.value.length
      const deletingFromDetail = Boolean(
        detailModalOpen.value
        && selectedImage.value
        && selectedIds.value.includes(selectedImage.value.id)
      )
      const previousDetailIndex = detailIndex.value
      const deletingCurrentPageAll = images.value.length > 0 && selectedIds.value.length >= images.value.length

      await deleteImages(selectedIds.value, {
        deleteStorage: tgSyncDeleteEnabled.value && deleteWithStorage.value,
      })

      notification.success('删除成功', `已删除 ${deletingCount} 张图片`)
      deleteModalOpen.value = false
      clearSelection()

      if (deletingCurrentPageAll && currentPage.value > 1) {
        currentPage.value -= 1
      }
      await fetchImages({ silent: true })

      if (deletingFromDetail) {
        if (!images.value.length) {
          detailIndex.value = -1
          selectedImage.value = null
          closeDetail()
        } else {
          const fallbackIndex = Math.max(0, Math.min(previousDetailIndex, images.value.length - 1))
          setDetailByIndex(fallbackIndex)
          detailModalOpen.value = true
        }
      }
    } catch (error) {
      notification.error('删除失败', '删除图片时出错')
      console.error('删除图片失败:', error)
    } finally {
      deleting.value = false
    }
  }

  const clearCacheAction = async () => {
    try {
      await clearCache()
      notification.success('成功', '缓存已清理')
    } catch (error) {
      notification.error('错误', '清理缓存失败')
      console.error('清理缓存失败:', error)
    }
  }

  const initialize = async () => {
    await Promise.all([
      loadSyncDeleteSetting(),
      fetchImages({ silent: true }),
    ])
  }

  return {
    loading,
    refreshing,
    deleting,
    images,
    selectedIds,
    selectedCount,
    isAllOnPageSelected,
    isPagePartiallySelected,

    searchQuery,
    primaryFilter,
    sortBy,
    sortOrder,
    advancedFilters,
    hasActiveAdvancedFilters,
    currentPage,
    totalPages,
    totalCount,
    pageSize,
    viewMode,
    advancedPanelOpen,

    detailModalOpen,
    detailIndex,
    selectedImage,
    hasPrevDetail,
    hasNextDetail,
    deleteModalOpen,
    deleteMessage,
    deleteWithStorage,
    tgSyncDeleteEnabled,

    pageSizeOptions,
    primaryFilterOptions,
    sortByOptions,
    sortOrderOptions,
    sourceOptions,

    initialize,
    fetchImages,
    refresh,
    setSearchQuery,
    applyPrimaryFilter,
    applyPageSize,
    applySorting,
    applyAdvancedFilters,
    resetAdvancedFilters,
    openAdvancedPanel,
    closeAdvancedPanel,
    changePage,

    toggleSelect,
    toggleSelectAllOnPage,
    clearSelection,

    openDetail,
    openDetailById,
    goPrevDetail,
    goNextDetail,
    closeDetail,
    downloadImage,
    deleteCurrentDetailImage,
    copyImageUrl,
    copySelectedUrls,

    openDeleteForSingle,
    openDeleteForSelection,
    closeDeleteModal,
    confirmDelete,
    clearCacheAction,
  }
}
