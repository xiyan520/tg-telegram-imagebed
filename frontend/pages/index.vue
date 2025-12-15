<template>
  <div class="max-w-5xl mx-auto space-y-8">
    <!-- 上传区域 -->
    <div class="flex justify-center items-center min-h-[60vh]">
      <UCard class="upload-card shadow-2xl w-full max-w-2xl">
        <div
          class="upload-area relative rounded-2xl p-12 text-center transition-all cursor-pointer"
        :class="[
          isDragging
            ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20'
            : '',
          uploading ? 'pointer-events-none opacity-50' : '',
        ]"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/gif,image/webp,image/svg+xml,image/avif"
          multiple
          class="hidden"
          @change="handleFileSelect"
        />

        <!-- 上传内容 -->
        <div v-if="!uploading" class="upload-content">
          <div class="folder-container">
            <div class="folder">
              <div class="front-side">
                <div class="tip"></div>
                <div class="cover"></div>
              </div>
              <div class="back-side cover"></div>
            </div>
          </div>
          <h3 class="text-2xl font-bold text-stone-900 dark:text-white mb-2">
            点击或拖拽上传图片
          </h3>
          <p class="text-stone-600 dark:text-stone-400 mb-2">
            支持 JPG、JPEG、PNG、GIF、WebP、AVIF、SVG 等格式，最大 20MB
          </p>
          <p class="paste-hint text-sm text-stone-500 dark:text-stone-400">
            💡 你也可以直接 <kbd
              class="px-2 py-1 bg-stone-200 dark:bg-stone-700 rounded text-xs"
              >Ctrl+V</kbd
            >
            粘贴剪贴板中的图片
          </p>
        </div>

        <!-- 上传进度 -->
        <div v-else class="space-y-4">
          <div class="flex justify-center">
            <div
              class="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"
            ></div>
          </div>
          <div>
            <p class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ uploadProgress.label }}
            </p>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {{ uploadProgress.percent }}%
            </p>
          </div>
          <UProgress :value="uploadProgress.percent" color="primary" />
          <UButton color="red" variant="soft" @click="cancelUpload">
            取消上传
          </UButton>
        </div>
      </div>
    </UCard>
    </div>

    <!-- 上传结果 -->
    <UCard v-if="uploadedImages.length > 0" class="shadow-xl">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-bold text-gray-900 dark:text-white">
            上传成功 ({{ uploadedImages.length }}张)
          </h3>
          <UButton color="gray" variant="ghost" @click="clearResults">
            清空
          </UButton>
        </div>
      </template>

      <!-- 缩略图网格 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div
          v-for="(image, index) in uploadedImages"
          :key="index"
          class="relative group aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
        >
          <img
            :src="image.url"
            :alt="image.filename"
            class="w-full h-full object-cover"
          />
          <div
            class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2"
          >
            <UButton
              icon="heroicons:eye"
              color="white"
              size="sm"
              @click="previewImage(image)"
            />
            <UButton
              icon="heroicons:clipboard-document"
              color="white"
              size="sm"
              @click="copyImageUrl(image.url)"
            />
          </div>
        </div>
      </div>

      <!-- 链接格式标签页 -->
      <div class="mt-6">
        <div
          class="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700"
        >
          <button
            v-for="(tab, index) in formatTabs"
            :key="index"
            @click="selectedFormat = index"
            :class="[
              'px-4 py-2 font-medium text-sm transition-colors',
              selectedFormat === index
                ? 'text-cyan-600 dark:text-cyan-400 border-b-2 border-cyan-600 dark:border-cyan-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
            ]"
          >
            {{ tab.label }}
          </button>
        </div>
        <div class="space-y-4 py-4">
          <UTextarea
            :model-value="getFormattedLinks(formatTabs[selectedFormat].value)"
            readonly
            :rows="6"
            class="font-mono text-sm"
          />
          <UButton
            icon="heroicons:clipboard-document"
            color="primary"
            block
            @click="copyAllLinks(formatTabs[selectedFormat].value)"
          >
            复制全部链接
          </UButton>
        </div>
      </div>
    </UCard>
  </div>

  <!-- Token生成器模态框 -->
  <UModal
    v-model="showTokenGenerator"
    :ui="{
      width: 'sm:max-w-md',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">生成Token</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="showTokenGenerator = false"
          />
        </div>
      </template>
      <div class="space-y-4">
        <p class="text-sm text-gray-600 dark:text-gray-400">
          生成专属Token后即可开始上传图片。Token会自动保存，下次访问时自动恢复。
        </p>
        <div
          class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800"
        >
          <div class="flex items-start gap-3">
            <UIcon
              name="heroicons:check-circle"
              class="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5"
            />
            <div class="flex-1">
              <p
                class="text-sm font-medium text-green-900 dark:text-green-100 mb-1"
              >
                无限制使用
              </p>
              <ul class="text-xs text-green-700 dark:text-green-300 space-y-1">
                <li>• 无上传数量限制</li>
                <li>• 无时间限制，永久有效</li>
                <li>• 可随时查看上传历史</li>
              </ul>
            </div>
          </div>
        </div>
        <UButton
          color="primary"
          block
          :loading="generatingToken"
          @click="handleGenerateToken"
        >
          生成Token
        </UButton>
      </div>
    </UCard>
  </UModal>

  <!-- Token信息模态框 -->
  <UModal
    v-model="showTokenInfo"
    :ui="{
      width: 'sm:max-w-md',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Token管理</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="showTokenInfo = false"
          />
        </div>
      </template>
      <div class="space-y-4">
        <div>
          <label
            class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
          >
            您的Token
          </label>
          <div class="flex gap-2">
            <UInput
              :model-value="guestStore.token"
              readonly
              class="flex-1 font-mono text-xs"
            />
            <UButton
              icon="heroicons:clipboard-document"
              color="gray"
              @click="copyToken"
            />
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            请妥善保管您的Token
          </p>
        </div>
        <div
          class="p-4 bg-gradient-to-br from-cyan-50 to-blue-50 dark:from-cyan-900/20 dark:to-blue-900/20 rounded-lg border border-cyan-200 dark:border-cyan-800"
        >
          <div class="text-center">
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
              已上传图片
            </p>
            <p class="text-3xl font-bold text-cyan-600 dark:text-cyan-400">
              {{ guestStore.uploadCount }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
              无数量限制 · 永久有效
            </p>
          </div>
        </div>
        <div class="space-y-2">
          <UButton
            color="cyan"
            variant="soft"
            block
            @click="
              () => {
                showTokenInfo = false;
                showTokenHistory = true;
              }
            "
          >
            <template #leading>
              <UIcon name="heroicons:clock" />
            </template>
            查看上传历史
          </UButton>
          <UButton
            color="gray"
            variant="outline"
            block
            @click="handleRefreshToken"
          >
            <template #leading>
              <UIcon name="heroicons:arrow-path" />
            </template>
            刷新Token
          </UButton>
        </div>
      </div>
    </UCard>
  </UModal>

  <!-- Token说明模态框 -->
  <UModal
    v-model="showGuestInfo"
    :ui="{
      width: 'sm:max-w-md',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Token功能说明</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="showGuestInfo = false"
          />
        </div>
      </template>
      <div class="space-y-4">
        <div>
          <h4 class="font-semibold text-gray-900 dark:text-white mb-2">
            ✨ 什么是Token？
          </h4>
          <p class="text-gray-600 dark:text-gray-400 text-sm">
            Token是您的专属凭证，用于管理和追踪您上传的图片。生成Token后，您可以查看上传历史、管理图片。
          </p>
        </div>
        <div>
          <h4 class="font-semibold text-gray-900 dark:text-white mb-2">
            🎯 主要功能
          </h4>
          <ul
            class="list-disc list-inside text-gray-600 dark:text-gray-400 text-sm space-y-1"
          >
            <li>查看上传历史记录</li>
            <li>无上传数量限制</li>
            <li>永久有效，无时间限制</li>
            <li>随时刷新获取新Token</li>
            <li>Token自动保存，下次访问自动恢复</li>
          </ul>
        </div>
        <div>
          <h4 class="font-semibold text-gray-900 dark:text-white mb-2">
            🔒 安全提示
          </h4>
          <ul
            class="list-disc list-inside text-gray-600 dark:text-gray-400 text-sm space-y-1"
          >
            <li>Token会自动保存在浏览器中</li>
            <li>Token丢失后无法找回，但可重新生成</li>
            <li>刷新Token会清除旧Token并生成新的</li>
            <li>请妥善保管您的Token</li>
          </ul>
        </div>
        <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
          <UButton
            color="primary"
            block
            @click="
              () => {
                showGuestInfo = false;
                showTokenGenerator = true;
              }
            "
          >
            生成Token
          </UButton>
        </div>
      </div>
    </UCard>
  </UModal>

  <!-- 上传历史模态框 -->
  <UModal
    v-model="showTokenHistory"
    :ui="{
      width: 'sm:max-w-md',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">上传历史</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="showTokenHistory = false"
          />
        </div>
      </template>
      <div class="space-y-4">
        <div
          v-if="tokenHistory.length > 0"
          class="space-y-3 max-h-96 overflow-y-auto"
        >
          <div
            v-for="(item, index) in tokenHistory"
            :key="index"
            class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:shadow-md transition-shadow"
          >
            <img
              :src="item.image_url"
              :alt="item.original_filename"
              class="w-12 h-12 object-cover rounded"
            />
            <div class="flex-1 min-w-0">
              <p
                class="text-sm font-medium text-gray-900 dark:text-white truncate"
              >
                {{ item.original_filename }}
              </p>
              <p class="text-xs text-gray-600 dark:text-gray-400">
                {{ item.created_at }}
              </p>
            </div>
            <UButton
              icon="heroicons:clipboard-document"
              color="gray"
              variant="ghost"
              size="sm"
              @click="copyImageUrl(item.image_url)"
            />
          </div>
        </div>
        <div
          v-else-if="!loadingHistory"
          class="text-center py-8 text-gray-500 dark:text-gray-400"
        >
          暂无上传记录
        </div>
        <div v-else class="text-center py-8">
          <div
            class="inline-block w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"
          ></div>
        </div>
      </div>
    </UCard>
  </UModal>

  <!-- 图片预览模态框 -->
  <UModal
    v-model="previewOpen"
    :ui="{
      width: 'sm:max-w-2xl',
      height: 'max-h-[85vh]',
      container: 'flex items-center justify-center',
      overlay: { background: 'bg-gray-200/75 dark:bg-gray-800/75' }
    }"
  >
    <UCard class="overflow-y-auto max-h-[80vh]">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">图片预览</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="previewOpen = false"
          />
        </div>
      </template>
      <div v-if="previewingImage">
        <img
          :src="previewingImage.url"
          :alt="previewingImage.filename"
          class="w-full rounded-lg"
        />
        <div class="mt-4 space-y-2">
          <p class="text-sm text-gray-600 dark:text-gray-400">
            <strong>文件名:</strong> {{ previewingImage.filename }}
          </p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            <strong>URL:</strong>
            <code
              class="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded"
            >
              {{ previewingImage.url }}
            </code>
          </p>
        </div>
      </div>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const toast = useNotification();
const { uploadImages, getStats } = useImageApi();
const guestStore = useGuestTokenStore();
const authStore = useAuthStore();
const config = useRuntimeConfig();
const { triggerStatsRefresh } = useStatsRefresh();

// 状态
const isDragging = ref(false);
const uploading = ref(false);
const uploadProgress = ref({ label: "上传中...", percent: 0 });
const uploadedImages = ref<any[]>([]);
const stats = ref<any>({});
const fileInput = ref<HTMLInputElement>();
const selectedFormat = ref(0);
const previewOpen = ref(false);
const previewingImage = ref<any>(null);
const showGuestInfo = ref(false);
const showTokenGenerator = ref(false);
const showTokenInfo = ref(false);
const showTokenHistory = ref(false);
const tokenConfig = ref({
  upload_limit: 100,
  expires_days: 30,
});
const generatingToken = ref(false);
const tokenHistory = ref<any[]>([]);
const loadingHistory = ref(false);

// 格式标签
const formatTabs = [
  { label: "URL", value: "url" },
  { label: "Markdown", value: "markdown" },
  { label: "HTML", value: "html" },
  { label: "BBCode", value: "bbcode" },
];

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value?.click();
};

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    handleFiles(Array.from(target.files));
  }
};

// 处理拖放
const handleDrop = (event: DragEvent) => {
  isDragging.value = false;
  if (event.dataTransfer?.files) {
    handleFiles(Array.from(event.dataTransfer.files));
  }
};

// 生成Token
const handleGenerateToken = async () => {
  generatingToken.value = true;
  try {
    await guestStore.generateToken(tokenConfig.value);
    showTokenGenerator.value = false;
    toast.success("Token已生成");
  } catch (error: any) {
    toast.error("生成失败", error.message);
  } finally {
    generatingToken.value = false;
  }
};

// 刷新Token
const handleRefreshToken = async () => {
  if (!confirm("刷新Token将清除当前Token并生成新的Token，确定继续吗？")) {
    return;
  }
  try {
    showTokenInfo.value = false;
    await guestStore.refreshToken(tokenConfig.value);
    toast.success("Token已刷新");
  } catch (error: any) {
    toast.error("刷新失败", error.message);
  }
};

// 清除Token
const handleClearToken = () => {
  if (confirm("确定要清除Token吗？清除后将无法查看上传历史。")) {
    guestStore.clearToken();
    tokenHistory.value = [];
    toast.success("Token已清除");
  }
};

// 复制Token
const copyToken = async () => {
  await copyToClipboard(guestStore.token, "Token已复制到剪贴板");
};

// 加载上传历史
const loadTokenHistory = async () => {
  if (!guestStore.hasToken) return;

  loadingHistory.value = true;
  try {
    const data = await guestStore.getUploads(1, 20);
    tokenHistory.value = data.uploads;
  } catch (error: any) {
    toast.error("加载失败", error.message);
  } finally {
    loadingHistory.value = false;
  }
};

// 监听历史模态框打开
watch(showTokenHistory, (newVal) => {
  if (newVal) {
    loadTokenHistory();
  }
});

// 复制图片URL
const copyImageUrl = async (url: string) => {
  await copyToClipboard(url, "已复制");
};

// 处理文件上传
const handleFiles = async (files: File[]) => {
  if (files.length === 0) return;

  // Token检查（如果有Token则使用Token上传）
  // 已移除上传次数限制检查
  // if (guestStore.hasToken) {
  //   if (guestStore.remainingUploads <= 0) {
  //     toast.add({
  //       title: '上传次数已用完',
  //       description: '请刷新Token以获取新的上传次数',
  //       color: 'red'
  //     })
  //     return
  //   }

  //   // 限制上传数量
  //   const maxFiles = Math.min(files.length, guestStore.remainingUploads)
  //   if (files.length > maxFiles) {
  //     toast.add({
  //       title: '提示',
  //       description: `剩余上传次数不足，只能上传${maxFiles}张图片`,
  //       color: 'orange'
  //     })
  //     files = files.slice(0, maxFiles)
  //   }
  // }

  // 验证文件
  const validFiles = files.filter((file) => {
    if (!file.type.startsWith("image/")) {
      toast.error("错误", `${file.name} 不是图片文件`);
      return false;
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error("错误", `${file.name} 超过 20MB`);
      return false;
    }
    return true;
  });

  if (validFiles.length === 0) return;

  uploading.value = true;
  uploadProgress.value = { label: "上传中...", percent: 0 };

  try {
    let results = [];

    if (authStore.isAuthenticated) {
      // 管理员上传（优先级最高，不受游客上传限制）
      for (let i = 0; i < validFiles.length; i++) {
        const file = validFiles[i];
        const formData = new FormData();
        formData.append("file", file);

        const response = await new Promise<any>((resolve, reject) => {
          const xhr = new XMLHttpRequest();

          xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
              const fileProgress = (event.loaded / event.total) * 100;
              const totalProgress = ((i + (event.loaded / event.total)) / validFiles.length) * 100;
              uploadProgress.value = {
                label: `上传中 (${i + 1}/${validFiles.length}) - ${Math.round(fileProgress)}%`,
                percent: Math.round(totalProgress),
              };
            }
          });

          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                resolve(JSON.parse(xhr.responseText));
              } catch (error) {
                reject(new Error('解析响应失败'));
              }
            } else {
              try {
                const errData = JSON.parse(xhr.responseText);
                reject(new Error(errData.error || `上传失败: ${xhr.status}`));
              } catch {
                reject(new Error(`上传失败: ${xhr.status}`));
              }
            }
          });

          xhr.addEventListener('error', () => reject(new Error('网络错误')));
          xhr.addEventListener('abort', () => reject(new Error('上传已取消')));

          xhr.open('POST', `${config.public.apiBase}/api/admin/upload`);
          xhr.withCredentials = true;
          xhr.send(formData);
        });

        if (response.success) {
          results.push(response.data);
        }
      }
    } else if (guestStore.hasToken) {
      // 使用Token上传（支持实时进度）
      for (let i = 0; i < validFiles.length; i++) {
        const file = validFiles[i];
        const formData = new FormData();
        formData.append("file", file);

        // 使用 XMLHttpRequest 支持实时进度
        const response = await new Promise<any>((resolve, reject) => {
          const xhr = new XMLHttpRequest();

          // 监听上传进度
          xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
              // 计算当前文件的上传进度
              const fileProgress = (event.loaded / event.total) * 100;
              // 计算总体进度：已完成的文件 + 当前文件的进度
              const totalProgress = ((i + (event.loaded / event.total)) / validFiles.length) * 100;

              uploadProgress.value = {
                label: `上传中 (${i + 1}/${validFiles.length}) - ${Math.round(fileProgress)}%`,
                percent: Math.round(totalProgress),
              };
            }
          });

          // 监听上传完成
          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const response = JSON.parse(xhr.responseText);
                resolve(response);
              } catch (error) {
                reject(new Error('解析响应失败'));
              }
            } else {
              reject(new Error(`上传失败: ${xhr.status}`));
            }
          });

          // 监听上传错误
          xhr.addEventListener('error', () => {
            reject(new Error('网络错误'));
          });

          // 监听上传中止
          xhr.addEventListener('abort', () => {
            reject(new Error('上传已取消'));
          });

          // 发送请求
          xhr.open('POST', `${config.public.apiBase}/api/auth/upload`);
          xhr.setRequestHeader('Authorization', `Bearer ${guestStore.token}`);
          xhr.send(formData);
        });

        if (response.success) {
          results.push(response.data);
        }
      }

      // 刷新token信息
      await guestStore.verifyToken();
    } else {
      // 普通上传（无Token）
      results = await uploadImages(validFiles, (progress) => {
        uploadProgress.value = progress;
      });
    }

    uploadProgress.value = { label: "完成", percent: 100 };
    uploadedImages.value = results;

    // 显示上传成功通知
    toast.success("上传成功", `成功上传 ${results.length} 张图片`);

    // 刷新统计数据
    await loadStats();

    // 触发全局统计刷新事件
    triggerStatsRefresh();
  } catch (error: any) {
    toast.error("上传失败", error.data?.error || error.message || "未知错误");
  } finally {
    uploading.value = false;
  }
};

// 取消上传
const cancelUpload = () => {
  uploading.value = false;
  uploadProgress.value = { label: "上传中...", percent: 0 };
};

// 清空结果
const clearResults = () => {
  uploadedImages.value = [];
};

// 获取格式化链接
const getFormattedLinks = (format: string) => {
  return uploadedImages.value
    .map((img) => {
      switch (format) {
        case "url":
          return img.url;
        case "markdown":
          return `![${img.filename}](${img.url})`;
        case "html":
          return `<img src="${img.url}" alt="${img.filename}" />`;
        case "bbcode":
          return `[img]${img.url}[/img]`;
        default:
          return img.url;
      }
    })
    .join("\n");
};

// 通用复制函数（带错误处理）
const copyToClipboard = async (text: string, successMessage: string = "已复制") => {
  try {
    // 优先使用现代剪贴板API
    await navigator.clipboard.writeText(text);
    toast.success(successMessage);
    return true;
  } catch (err) {
    // 回退方案：使用传统方法
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);

      if (successful) {
        toast.success(successMessage);
        return true;
      } else {
        throw new Error("复制失败");
      }
    } catch (fallbackErr) {
      toast.error("复制失败", "请手动复制内容");
      console.error("复制失败:", fallbackErr);
      return false;
    }
  }
};

// 复制所有链接
const copyAllLinks = async (format: string) => {
  const text = getFormattedLinks(format);
  await copyToClipboard(text, "已复制全部链接");
};

// 快速复制所有链接（用于通知按钮）
const copyAllLinksQuick = async (format: string) => {
  const text = getFormattedLinks(format);
  await copyToClipboard(text, "已复制全部链接");
};

// 预览图片
const previewImage = (image: any) => {
  previewingImage.value = image;
  previewOpen.value = true;
};

// 加载统计信息
const loadStats = async () => {
  try {
    stats.value = await getStats();
  } catch (error) {
    console.error("加载统计信息失败:", error);
  }
};

// 定时刷新统计数据
let statsRefreshInterval: NodeJS.Timeout | null = null;

// 处理剪贴板粘贴
const handlePaste = (event: ClipboardEvent) => {
  const items = event.clipboardData?.items;
  if (!items) return;

  const files: File[] = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        files.push(file);
      }
    }
  }

  if (files.length > 0) {
    event.preventDefault();
    handleFiles(files);
  }
};

// 页面加载时获取统计和恢复认证状态
onMounted(async () => {
  await loadStats();
  authStore.restoreAuth();
  await guestStore.restoreToken();

  // 添加全局粘贴事件监听
  window.addEventListener("paste", handlePaste);

  // 每30秒自动刷新统计数据
  statsRefreshInterval = setInterval(() => {
    loadStats();
  }, 30000);
});

// 页面卸载时清除定时器和事件监听
onUnmounted(() => {
  if (statsRefreshInterval) {
    clearInterval(statsRefreshInterval);
  }
  // 移除粘贴事件监听
  window.removeEventListener("paste", handlePaste);
});
</script>
