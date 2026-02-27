<template>
  <div class="space-y-4">
    <div class="rounded-2xl border border-stone-200/80 dark:border-stone-700/80 bg-white/90 dark:bg-neutral-900/80 backdrop-blur-sm shadow-sm">
      <div class="p-4 sm:p-5 flex items-start gap-3">
        <div
          class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-white shadow-sm"
          :class="isTgLoggedIn ? 'bg-gradient-to-br from-blue-500 to-cyan-500' : 'bg-gradient-to-br from-amber-500 to-orange-500'"
        >
          <UIcon :name="isTgLoggedIn ? 'heroicons:chat-bubble-left-right' : 'heroicons:key'" class="w-5 h-5" />
        </div>
        <div class="min-w-0 flex-1">
          <h1 class="text-lg sm:text-xl font-semibold text-stone-900 dark:text-white truncate">{{ title }}</h1>
          <p v-if="subtitle" class="text-xs sm:text-sm text-stone-500 dark:text-stone-400 mt-0.5">{{ subtitle }}</p>
        </div>
        <UButton
          v-if="showLogout"
          color="gray"
          variant="soft"
          size="sm"
          icon="heroicons:arrow-right-start-on-rectangle"
          @click="emit('logout')"
        >
          退出
        </UButton>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside class="hidden lg:block">
        <div class="rounded-2xl border border-stone-200/80 dark:border-stone-700/80 bg-white/85 dark:bg-neutral-900/75 backdrop-blur-sm shadow-sm p-2">
          <button
            v-for="item in visibleItems"
            :key="item.key"
            class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors"
            :class="item.key === modelValue
              ? 'bg-amber-500 text-white shadow-sm shadow-amber-500/25'
              : 'text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-800'"
            @click="emit('update:modelValue', item.key)"
          >
            <span class="inline-flex items-center gap-2 min-w-0">
              <UIcon :name="item.icon" class="w-4 h-4 flex-shrink-0" />
              <span class="truncate">{{ item.label }}</span>
            </span>
            <span v-if="toBadgeText(item.badge)" class="text-[11px] px-2 py-0.5 rounded-full bg-black/10 dark:bg-white/10">
              {{ toBadgeText(item.badge) }}
            </span>
            <span v-else-if="item.badge === true" class="w-2 h-2 rounded-full bg-red-500" />
          </button>
        </div>
      </aside>

      <div class="space-y-3 lg:space-y-0">
        <div class="lg:hidden -mx-1 px-1 overflow-x-auto">
          <div class="inline-flex min-w-full gap-1 p-1 rounded-xl border border-stone-200/80 dark:border-stone-700/80 bg-white/85 dark:bg-neutral-900/75 backdrop-blur-sm">
            <button
              v-for="item in visibleItems"
              :key="item.key"
              class="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors flex-1"
              :class="item.key === modelValue
                ? 'bg-amber-500 text-white'
                : 'text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-neutral-800'"
              @click="emit('update:modelValue', item.key)"
            >
              <UIcon :name="item.icon" class="w-3.5 h-3.5" />
              {{ item.label }}
              <span v-if="toBadgeText(item.badge)" class="text-[10px] px-1.5 py-0.5 rounded-full bg-black/10 dark:bg-white/10">
                {{ toBadgeText(item.badge) }}
              </span>
              <span v-else-if="item.badge === true" class="w-1.5 h-1.5 rounded-full bg-red-500" />
            </button>
          </div>
        </div>

        <div class="min-w-0">
          <slot />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export type MeNavKey = 'overview' | 'tokens' | 'uploads' | 'galleries' | 'tg'

export interface MeNavItem {
  key: MeNavKey
  label: string
  icon: string
  badge?: number | boolean
  hidden?: boolean
}

const props = defineProps<{
  title: string
  subtitle?: string
  modelValue: MeNavKey
  items: MeNavItem[]
  isTgLoggedIn?: boolean
  showLogout?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: MeNavKey): void
  (e: 'logout'): void
}>()

const visibleItems = computed(() => props.items.filter(i => !i.hidden))

const toBadgeText = (badge?: number | boolean) => {
  if (typeof badge === 'number' && badge > 0) return String(badge)
  return ''
}
</script>
