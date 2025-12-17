<template>
  <div class="flex justify-center items-center min-h-[50vh]">
    <div class="text-center space-y-4">
      <div class="w-12 h-12 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p class="text-stone-600 dark:text-stone-400">正在跳转到相册页面...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
onMounted(() => {
  navigateTo('/album', { replace: true })
})
</script>
