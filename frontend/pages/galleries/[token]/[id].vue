<template>
  <SharedGalleryDetailPage :adapter="adapter" />
</template>

<script setup lang="ts">
import SharedGalleryDetailPage from '~/components/gallery-share/SharedGalleryDetailPage.vue'
import { createShareAllGalleryAdapter } from '~/composables/gallery-share/adapters'

definePageMeta({ layout: false })

const route = useRoute()
const galleryApi = useGalleryApi()
const { displayName } = useSeoSettings()

const shareAllToken = computed(() => String(route.params.token || ''))
const galleryId = computed(() => Number.parseInt(String(route.params.id || ''), 10))

const adapter = computed(() => createShareAllGalleryAdapter({
  api: galleryApi,
  shareAllToken: shareAllToken.value,
  galleryId: galleryId.value,
  displayName: displayName.value
}))
</script>
