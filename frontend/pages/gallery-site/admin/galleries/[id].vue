<template>
  <div class="space-y-6 sm:space-y-8">
    <section class="rounded-3xl border border-stone-200/70 bg-white/85 p-5 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/75 sm:p-7">
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <UButton icon="heroicons:arrow-left" color="gray" variant="ghost" to="/gallery-site/admin/galleries" />
            <span class="text-xs font-semibold uppercase tracking-[0.2em] text-amber-600 dark:text-amber-400">Gallery Detail</span>
          </div>
          <h1 class="text-2xl font-bold font-serif tracking-tight text-stone-900 dark:text-white sm:text-4xl">{{ gallery?.name || '画集详情' }}</h1>
          <div class="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
            <span class="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300">
              {{ gallery?.image_count || 0 }} 张图片
            </span>
            <span class="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300">
              创建于 {{ formatDate(gallery?.created_at) }}
            </span>
            <span class="rounded-full border border-stone-200 bg-stone-100 px-3 py-1 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300">
              第 {{ page }} / {{ totalPages }} 页
            </span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 lg:justify-end">
          <UButton
            icon="heroicons:share"
            :color="isShareEnabled ? 'green' : 'gray'"
            variant="outline"
            size="sm"
            :disabled="sharingAction"
            @click="shareOpen = true"
          >
            {{ isShareEnabled ? '已分享' : '分享' }}
          </UButton>
          <UButton icon="heroicons:cog-6-tooth" color="gray" variant="outline" size="sm" @click="openSettings">
            设置
          </UButton>
          <UButton icon="heroicons:trash" color="red" variant="outline" size="sm" @click="deleteOpen = true">
            删除
          </UButton>
        </div>
      </div>
    </section>

    <section class="rounded-2xl border border-stone-200/80 bg-white/90 p-4 backdrop-blur-sm dark:border-stone-700/70 dark:bg-neutral-900/80">
      <div class="flex flex-col gap-3 md:flex-row md:items-center">
        <div class="flex flex-wrap items-center gap-2">
          <UCheckbox v-model="selectAll" @change="handleSelectAll">
            <template #label><span class="text-sm font-medium">全选</span></template>
          </UCheckbox>
          <UButton color="red" variant="soft" size="sm" :disabled="selectedImages.length === 0" @click="removeSelected">
            <template #leading><UIcon name="heroicons:trash" /></template>
            移除选中 ({{ selectedImages.length }})
          </UButton>
        </div>
        <div class="flex flex-wrap items-center gap-2 md:ml-auto">
          <UButton icon="heroicons:sparkles" color="amber" variant="soft" size="sm" :disabled="images.length === 0" @click="openCoverRecommend">
            推荐封面
          </UButton>
          <UButton icon="heroicons:plus" color="primary" size="sm" @click="openAddModal">
            添加图片
          </UButton>
          <UButton icon="heroicons:arrow-path" color="gray" variant="ghost" size="sm" :loading="loading" @click="loadImages" />
        </div>
      </div>
    </section>

    <section class="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-700 dark:bg-neutral-900 sm:p-5">
      <div v-if="loading" class="flex flex-col items-center justify-center py-16">
        <div class="mb-4 h-16 w-16 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
        <p class="text-stone-600 dark:text-stone-400">加载中...</p>
      </div>

      <div v-else-if="images.length === 0" class="py-16 text-center">
        <div class="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-stone-100 dark:bg-neutral-800">
          <UIcon name="heroicons:photo" class="h-10 w-10 text-stone-400" />
        </div>
        <p class="mb-2 text-lg font-medium text-stone-900 dark:text-white">暂无图片</p>
        <p class="text-sm text-stone-600 dark:text-stone-400">点击“添加图片”将图片添加到画集</p>
      </div>

      <div v-else class="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4 lg:grid-cols-6">
        <div
          v-for="(image, idx) in images"
          :key="image.encrypted_id"
          class="group relative aspect-square cursor-pointer overflow-hidden rounded-xl border-2 transition-all hover:shadow-lg"
          :class="[
            selectedImages.includes(image.encrypted_id)
              ? 'border-amber-500 ring-2 ring-amber-500 ring-offset-2 dark:ring-offset-neutral-900'
              : image.encrypted_id === gallery?.cover_image
                ? 'border-green-500 ring-2 ring-green-500 ring-offset-2 dark:ring-offset-neutral-900'
                : 'border-stone-200 hover:border-amber-400 dark:border-neutral-700 dark:hover:border-amber-500'
          ]"
          @click="openLightbox(idx)"
        >
          <img :src="getImageSrc(image)" :alt="image.original_filename" loading="lazy" class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-110" />
          <div v-if="image.encrypted_id === gallery?.cover_image" class="absolute right-2 top-2 z-10">
            <div class="flex items-center gap-1 rounded-full bg-green-500 px-2 py-0.5 text-xs text-white shadow-lg">
              <UIcon name="heroicons:star-solid" class="h-3 w-3" /><span>封面</span>
            </div>
          </div>
          <div class="absolute left-2 top-2 z-10" @click.stop>
            <div class="rounded-lg bg-white/90 p-2 shadow-lg backdrop-blur-sm dark:bg-neutral-800/90">
              <UCheckbox :model-value="selectedImages.includes(image.encrypted_id)" @change="toggleSelection(image.encrypted_id)" />
            </div>
          </div>
          <div v-if="image.encrypted_id !== gallery?.cover_image" class="absolute right-2 top-2 z-10 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
            <UButton icon="heroicons:star" color="white" variant="solid" size="xs" :loading="settingCover === image.encrypted_id" @click.stop="setCoverImage(image.encrypted_id)">
              设为封面
            </UButton>
          </div>
          <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
            <p class="truncate text-xs text-white">{{ image.original_filename }}</p>
          </div>
        </div>
      </div>

      <div v-if="totalPages > 1" class="flex justify-center pt-5">
        <div class="flex items-center gap-2">
          <UButton icon="heroicons:chevron-left" color="gray" variant="ghost" size="sm" :disabled="page <= 1" @click="page--" />
          <span class="text-sm text-stone-500">{{ page }} / {{ totalPages }}</span>
          <UButton icon="heroicons:chevron-right" color="gray" variant="ghost" size="sm" :disabled="page >= totalPages" @click="page++" />
        </div>
      </div>
    </section>

    <!-- 设置模态框 -->
    <UModal v-model="settingsOpen" :prevent-close="addTokenOpen" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">画集设置</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="settingsOpen = false" />
          </div>
        </template>
        <div class="space-y-6">
          <div class="space-y-4">
            <h4 class="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">展示与 SEO</h4>
            <UFormGroup label="画集标题" required>
              <UInput v-model="settingsForm.name" :maxlength="100" placeholder="请输入画集标题" />
            </UFormGroup>
            <UFormGroup label="首页卡片副标题">
              <UInput v-model="settingsForm.cardSubtitle" placeholder="例如：编辑推荐 · 风格集" />
            </UFormGroup>
            <div class="grid gap-3 sm:grid-cols-2">
              <UFormGroup label="首页精选权重">
                <UInput v-model.number="settingsForm.editorPickWeight" type="number" :min="0" :max="1000" />
              </UFormGroup>
              <UFormGroup label="主题色">
                <UInput v-model="settingsForm.themeColor" placeholder="如 #f59e0b" />
              </UFormGroup>
            </div>
            <div class="grid gap-3 sm:grid-cols-3">
              <UFormGroup label="布局模式">
                <USelect v-model="settingsForm.layoutMode" :options="layoutModeOptions" value-attribute="value" option-attribute="label" />
              </UFormGroup>
              <UFormGroup label="图片排序">
                <USelect v-model="settingsForm.sortOrder" :options="sortOrderOptions" value-attribute="value" option-attribute="label" />
              </UFormGroup>
              <UFormGroup label="OG 图图片 ID">
                <UInput v-model="settingsForm.ogImageEncryptedId" placeholder="留空使用封面图" />
              </UFormGroup>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <UCheckbox v-model="settingsForm.homepageExposeEnabled" label="允许首页曝光" />
              <UCheckbox v-model="settingsForm.showImageInfo" label="前台显示图片信息" />
              <UCheckbox v-model="settingsForm.allowDownload" label="前台允许下载图片" />
              <UCheckbox v-model="settingsForm.nsfwWarning" label="启用 NSFW 提示" />
            </div>
            <UFormGroup label="自定义头部文案">
              <UInput v-model="settingsForm.customHeaderText" placeholder="进入画集详情页时显示在头部" />
            </UFormGroup>
            <UFormGroup label="SEO 标题">
              <UInput v-model="settingsForm.seoTitle" placeholder="留空则使用画集名称" />
            </UFormGroup>
            <UFormGroup label="SEO 描述">
              <UTextarea v-model="settingsForm.seoDescription" :rows="2" placeholder="留空则使用画集描述" />
            </UFormGroup>
            <UFormGroup label="SEO 关键词">
              <UInput v-model="settingsForm.seoKeywords" placeholder="例如：插画,摄影,二次元" />
            </UFormGroup>
          </div>

          <div class="space-y-4 border-t border-stone-200 pt-5 dark:border-stone-700">
            <h4 class="text-sm font-semibold uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">访问控制</h4>
            <UFormGroup label="访问模式">
              <USelect v-model="settingsForm.mode" :options="accessModeOptions" value-attribute="value" option-attribute="label" />
            </UFormGroup>
            <UFormGroup v-if="settingsForm.mode === 'password'" label="访问密码" required>
              <UInput v-model="settingsForm.password" type="password" :placeholder="gallery?.has_password ? '留空保持原密码' : '设置访问密码'" />
            </UFormGroup>
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
        </div>
        <template #footer>
          <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <UButton color="gray" variant="ghost" @click="settingsOpen = false">取消</UButton>
            <UButton color="primary" :loading="settingsSaving" @click="saveSettings">保存</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加 Token 授权模态框 -->
    <UModal v-model="addTokenOpen" :ui="{ width: 'sm:max-w-lg' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
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
          <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <UButton color="gray" variant="ghost" @click="addTokenOpen = false">取消</UButton>
            <UButton color="primary" :loading="addingToken" :disabled="!newToken.trim()" @click="handleAddToken">授权</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 分享模态框 -->
    <UModal v-model="shareOpen" :ui="{ width: 'sm:max-w-xl' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">单独分享链接</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" :disabled="sharingAction" @click="shareOpen = false" />
          </div>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-stone-600 dark:text-stone-400">单独分享链接仅分享这一个画集。如需分享全部画集，请使用管理后台的"全部分享"功能。</p>
          <div v-if="isShareEnabled && gallery?.share_url" class="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
            <p class="text-sm font-medium text-green-800 dark:text-green-200 mb-2">分享链接已开启</p>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
              <code class="flex-1 break-all rounded bg-white p-2 text-xs dark:bg-neutral-900">{{ gallery.share_url }}</code>
              <UButton icon="heroicons:clipboard-document" color="primary" variant="soft" size="sm" @click="copyShareUrl">复制</UButton>
            </div>
          </div>
          <div v-else class="p-4 bg-stone-50 dark:bg-neutral-800 rounded-lg border border-stone-200 dark:border-neutral-700">
            <p class="text-sm text-stone-600 dark:text-stone-400">分享链接未开启，点击下方按钮开启。</p>
          </div>
        </div>
        <template #footer>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <UButton
              v-if="isShareEnabled"
              color="red"
              variant="soft"
              :loading="sharingAction"
              :disabled="sharingAction"
              @click="handleToggleShare(false)"
            >
              关闭分享
            </UButton>
            <div v-else></div>
            <UButton
              v-if="!isShareEnabled"
              color="primary"
              :loading="sharingAction"
              :disabled="sharingAction"
              @click="handleToggleShare(true)"
            >
              开启分享
            </UButton>
            <UButton v-else color="gray" variant="ghost" :disabled="sharingAction" @click="shareOpen = false">关闭</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 添加图片模态框 -->
    <UModal v-model="addModalOpen" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard class="max-h-[90vh] overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold text-stone-900 dark:text-white sm:text-lg">添加图片到画集</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="addModalOpen = false" />
          </div>
        </template>
        <div class="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
            <UInput v-model="userImagesSearch" class="flex-1" icon="heroicons:magnifying-glass" placeholder="搜索文件名" :disabled="loadingUserImages" />
          </div>
          <div class="flex flex-col gap-2 text-xs text-stone-500 dark:text-stone-400 sm:flex-row sm:items-center sm:justify-between">
            <span>共 {{ userImagesTotal }} 张图片</span>
            <div class="flex flex-wrap items-center gap-2">
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
          <div v-else class="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 max-h-[400px] overflow-y-auto">
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
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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
    <UModal v-model="deleteOpen" :ui="{ width: 'sm:max-w-lg' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
        <template #header>
          <h3 class="text-lg font-semibold text-red-600">确认删除</h3>
        </template>
        <p class="text-stone-700 dark:text-stone-300">确定要删除画集"{{ gallery?.name }}"吗？此操作不可恢复，但不会删除画集内的图片。</p>
        <template #footer>
          <div class="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <UButton color="gray" variant="ghost" @click="deleteOpen = false">取消</UButton>
            <UButton color="red" :loading="deleting" @click="confirmDelete">删除</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- 推荐封面模态框 -->
    <UModal v-model="coverRecommendOpen" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard class="max-h-[85vh] overflow-y-auto">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-stone-900 dark:text-white">推荐封面</h3>
            <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="coverRecommendOpen = false" />
          </div>
        </template>
        <div class="space-y-3">
          <p class="text-sm text-stone-600 dark:text-stone-400">根据文件大小、类型和文件名智能推荐，点击即可设为封面</p>
          <div v-if="recommendedCovers.length === 0" class="text-center py-6 text-stone-500">暂无足够图片进行推荐</div>
          <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3">
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
const { copy: clipboardCopy } = useClipboardCopy()
const config = useRuntimeConfig()
const {
  getGalleryDetail, deleteGallery,
  enableShare, disableShare, updateAccess, updateGallery,
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
const settingsForm = ref({
  name: '',
  mode: 'public',
  password: '',
  hideFromShareAll: false,
  homepageExposeEnabled: true,
  editorPickWeight: 0,
  cardSubtitle: '',
  layoutMode: 'masonry',
  themeColor: '',
  showImageInfo: true,
  allowDownload: true,
  sortOrder: 'newest',
  nsfwWarning: false,
  customHeaderText: '',
  seoTitle: '',
  seoDescription: '',
  seoKeywords: '',
  ogImageEncryptedId: ''
})
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

const openSettings = () => {
  settingsForm.value = {
    name: gallery.value?.name || '',
    mode: gallery.value?.access_mode || 'public',
    password: '',
    hideFromShareAll: gallery.value?.hide_from_share_all || false,
    homepageExposeEnabled: Boolean(gallery.value?.homepage_expose_enabled ?? true),
    editorPickWeight: gallery.value?.editor_pick_weight ?? 0,
    cardSubtitle: gallery.value?.card_subtitle || '',
    layoutMode: gallery.value?.layout_mode || 'masonry',
    themeColor: gallery.value?.theme_color || '',
    showImageInfo: Boolean(gallery.value?.show_image_info ?? true),
    allowDownload: Boolean(gallery.value?.allow_download ?? true),
    sortOrder: gallery.value?.sort_order || 'newest',
    nsfwWarning: Boolean(gallery.value?.nsfw_warning ?? false),
    customHeaderText: gallery.value?.custom_header_text || '',
    seoTitle: gallery.value?.seo_title || '',
    seoDescription: gallery.value?.seo_description || '',
    seoKeywords: gallery.value?.seo_keywords || '',
    ogImageEncryptedId: gallery.value?.og_image_encrypted_id || ''
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
    const normalizedName = settingsForm.value.name.trim()
    if (!normalizedName) {
      notification.error('保存失败', '画集标题不能为空')
      return
    }

    const accessBody: any = {
      access_mode: settingsForm.value.mode,
      hide_from_share_all: settingsForm.value.hideFromShareAll
    }
    if (settingsForm.value.mode === 'password' && settingsForm.value.password) {
      accessBody.password = settingsForm.value.password
    }
    gallery.value = await updateAccess(galleryId.value, accessBody)

    gallery.value = await updateGallery(galleryId.value, {
      name: normalizedName,
      card_subtitle: settingsForm.value.cardSubtitle,
      editor_pick_weight: settingsForm.value.editorPickWeight,
      homepage_expose_enabled: settingsForm.value.homepageExposeEnabled,
      layout_mode: settingsForm.value.layoutMode as any,
      theme_color: settingsForm.value.themeColor,
      show_image_info: settingsForm.value.showImageInfo,
      allow_download: settingsForm.value.allowDownload,
      sort_order: settingsForm.value.sortOrder as any,
      nsfw_warning: settingsForm.value.nsfwWarning,
      custom_header_text: settingsForm.value.customHeaderText,
      seo_title: settingsForm.value.seoTitle,
      seo_description: settingsForm.value.seoDescription,
      seo_keywords: settingsForm.value.seoKeywords,
      og_image_encrypted_id: settingsForm.value.ogImageEncryptedId || null
    })

    notification.success('已保存', '画集设置已更新')
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
const shareActionSeq = ref(0)
const isShareEnabled = computed(() => Boolean(Number(gallery.value?.share_enabled ?? 0)))

const handleToggleShare = async (nextEnabled: boolean) => {
  if (sharingAction.value) return

  const actionId = ++shareActionSeq.value
  sharingAction.value = true
  try {
    const updatedGallery = nextEnabled
      ? await enableShare(galleryId.value)
      : await disableShare(galleryId.value)

    if (actionId !== shareActionSeq.value) return
    gallery.value = updatedGallery

    const freshDetail = await getGalleryDetail(galleryId.value, 1, 1)
    if (actionId !== shareActionSeq.value) return
    gallery.value = freshDetail.gallery

    if (nextEnabled) {
      notification.success('已开启', '分享链接已生成')
    } else {
      notification.success('已关闭', '分享链接已关闭')
      shareOpen.value = false
    }
  } catch (e: any) {
    if (actionId === shareActionSeq.value) {
      notification.error('操作失败', e.message)
    }
  } finally {
    if (actionId === shareActionSeq.value) {
      sharingAction.value = false
    }
  }
}

const copyShareUrl = async () => {
  if (!gallery.value?.share_url) return
  await clipboardCopy(gallery.value.share_url, '链接已复制到剪贴板')
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
  if (url) void clipboardCopy(url, '图片链接已复制')
}

watch(page, loadImages)

onMounted(async () => {
  await loadGallery()
  await loadImages()
})
</script>
