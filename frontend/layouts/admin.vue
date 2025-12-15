<template>
  <AdminShell
    @open-settings="settingsOpen = true"
    @logout="handleLogout"
  >
    <slot />
  </AdminShell>

  <!-- 管理员设置模态框 -->
  <UModal v-model="settingsOpen">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-stone-900 dark:text-white">管理员设置</h3>
          <UButton
            icon="heroicons:x-mark"
            color="gray"
            variant="ghost"
            @click="settingsOpen = false"
          />
        </div>
      </template>

      <div class="space-y-4">
        <UFormGroup label="新用户名">
          <UInput v-model="settingsForm.username" placeholder="留空则不修改" />
        </UFormGroup>
        <UFormGroup label="新密码">
          <UInput v-model="settingsForm.password" type="password" placeholder="留空则不修改" />
        </UFormGroup>
        <UFormGroup label="确认密码">
          <UInput v-model="settingsForm.confirmPassword" type="password" placeholder="再次输入新密码" />
        </UFormGroup>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="settingsOpen = false">
            取消
          </UButton>
          <UButton color="primary" :loading="saving" @click="handleUpdateSettings">
            保存
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const authStore = useAuthStore()
const notification = useNotification()

const settingsOpen = ref(false)
const saving = ref(false)
const settingsForm = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

const handleLogout = async () => {
  await authStore.logout()
  navigateTo('/admin')
}

const handleUpdateSettings = async () => {
  if (settingsForm.value.password && settingsForm.value.password !== settingsForm.value.confirmPassword) {
    notification.error('错误', '两次输入的密码不一致')
    return
  }

  saving.value = true
  try {
    await authStore.updateSettings(settingsForm.value)
    notification.success('成功', '设置已更新')
    settingsOpen.value = false
    settingsForm.value = { username: '', password: '', confirmPassword: '' }
  } catch (error) {
    notification.error('错误', '更新设置失败')
  } finally {
    saving.value = false
  }
}
</script>
