import { computed } from 'vue'
import type { Ref } from 'vue'
import type { SettingsDirtyMap, SettingsSectionKey } from '~/types/admin-settings'

interface UseSettingsDirtyStateOptions<T extends Record<string, any>> {
  current: Ref<T>
  original: Ref<T | null>
  groups: Record<SettingsSectionKey, string[]>
  extras?: Partial<Record<SettingsSectionKey, () => boolean>>
}

const stableStringify = (value: any): string => {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  const keys = Object.keys(value).sort()
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`
}

const pick = (source: Record<string, any>, keys: string[]) => {
  const out: Record<string, any> = {}
  for (const key of keys) out[key] = source[key]
  return out
}

export const useSettingsDirtyState = <T extends Record<string, any>>(options: UseSettingsDirtyStateOptions<T>) => {
  const dirtyMap = computed<SettingsDirtyMap>(() => {
    const base = options.original.value
    const map: SettingsDirtyMap = {}
    for (const [groupKey, fields] of Object.entries(options.groups) as Array<[SettingsSectionKey, string[]]>) {
      const hasCoreDiff = !base
        ? false
        : stableStringify(pick(options.current.value, fields)) !== stableStringify(pick(base, fields))
      const hasExtraDiff = options.extras?.[groupKey]?.() || false
      map[groupKey] = hasCoreDiff || hasExtraDiff
    }
    return map
  })

  const dirtyCount = computed(() => Object.values(dirtyMap.value).filter(Boolean).length)
  const isAnyDirty = computed(() => dirtyCount.value > 0)
  const isGroupDirty = (key: SettingsSectionKey) => computed(() => Boolean(dirtyMap.value[key]))

  return {
    dirtyMap,
    dirtyCount,
    isAnyDirty,
    isGroupDirty,
  }
}
