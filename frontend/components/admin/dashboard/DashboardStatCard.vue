<template>
  <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-xs font-medium uppercase tracking-[0.12em] text-stone-500 dark:text-stone-400">
          {{ label }}
        </p>
        <div v-if="loading" class="mt-2 h-8 w-28 animate-pulse rounded-md bg-stone-200 dark:bg-neutral-700" />
        <p v-else class="mt-1.5 truncate text-2xl font-bold text-stone-900 dark:text-white">
          {{ displayValue }}
        </p>
        <p v-if="hint" class="mt-1 text-xs text-stone-500 dark:text-stone-400">
          {{ hint }}
        </p>
      </div>

      <div
        class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset"
        :class="[toneUi.bg, toneUi.ring]"
      >
        <UIcon :name="icon" class="h-5 w-5" :class="toneUi.icon" />
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  label: string
  value?: string | number | null
  hint?: string
  icon: string
  tone?: 'amber' | 'blue' | 'indigo' | 'emerald' | 'rose'
  loading?: boolean
}>(), {
  tone: 'amber',
  loading: false,
})

const toneMap = {
  amber: {
    bg: 'bg-amber-100/70 dark:bg-amber-900/25',
    ring: 'ring-amber-200 dark:ring-amber-800/60',
    icon: 'text-amber-600 dark:text-amber-300',
  },
  blue: {
    bg: 'bg-blue-100/70 dark:bg-blue-900/25',
    ring: 'ring-blue-200 dark:ring-blue-800/60',
    icon: 'text-blue-600 dark:text-blue-300',
  },
  indigo: {
    bg: 'bg-indigo-100/70 dark:bg-indigo-900/25',
    ring: 'ring-indigo-200 dark:ring-indigo-800/60',
    icon: 'text-indigo-600 dark:text-indigo-300',
  },
  emerald: {
    bg: 'bg-emerald-100/70 dark:bg-emerald-900/25',
    ring: 'ring-emerald-200 dark:ring-emerald-800/60',
    icon: 'text-emerald-600 dark:text-emerald-300',
  },
  rose: {
    bg: 'bg-rose-100/70 dark:bg-rose-900/25',
    ring: 'ring-rose-200 dark:ring-rose-800/60',
    icon: 'text-rose-600 dark:text-rose-300',
  },
} as const

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '--'
  if (typeof props.value === 'string' && props.value.trim() === '') return '--'
  return String(props.value)
})

const toneUi = computed(() => toneMap[props.tone])
</script>
