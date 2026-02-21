<template>
  <UModal v-model="open">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">创建画集</h3>
          <UButton icon="heroicons:x-mark" color="gray" variant="ghost" @click="open = false" />
        </div>
      </template>

      <form class="space-y-4" @submit.prevent="handleCreate">
        <UFormGroup label="画集名称" required>
          <UInput
            v-model="name"
            placeholder="输入画集名称"
            :maxlength="100"
            autofocus
          />
        </UFormGroup>
        <UFormGroup label="描述（可选）">
          <UInput
            v-model="description"
            placeholder="输入画集描述"
            :maxlength="500"
          />
        </UFormGroup>
      </form>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="open = false">取消</UButton>
          <UButton color="primary" :loading="creating" :disabled="!name.trim()" @click="handleCreate">
            创建
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const open = defineModel<boolean>({ default: false })
const emit = defineEmits<{ (e: 'created'): void }>()

const toast = useLightToast()
const galleryApi = useGalleryApi()

const name = ref('')
const description = ref('')
const creating = ref(false)

const handleCreate = async () => {
  const trimmed = name.value.trim()
  if (!trimmed) return
  creating.value = true
  try {
    await galleryApi.createGallery(trimmed, description.value.trim() || undefined)
    toast.success('画集创建成功')
    name.value = ''
    description.value = ''
    open.value = false
    emit('created')
  } catch (e: any) {
    toast.error('创建失败', e.message)
  } finally {
    creating.value = false
  }
}
</script>
