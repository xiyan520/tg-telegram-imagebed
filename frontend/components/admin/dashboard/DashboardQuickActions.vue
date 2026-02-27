<template>
  <UCard class="border border-stone-200/80 bg-white/92 shadow-sm dark:border-neutral-700/80 dark:bg-neutral-900/88">
    <template #header>
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500">
          <UIcon name="heroicons:cursor-arrow-rays" class="h-4.5 w-4.5 text-white" />
        </div>
        <div>
          <h3 class="text-sm font-semibold text-stone-900 dark:text-white">快捷操作</h3>
          <p class="text-xs text-stone-500 dark:text-stone-400">高频入口，减少跳转层级</p>
        </div>
      </div>
    </template>

    <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
      <NuxtLink
        v-for="item in actions"
        :key="item.to"
        :to="item.to"
        class="group flex items-center gap-2.5 rounded-xl border border-stone-200/80 px-3 py-2.5 transition-all hover:border-amber-300 hover:bg-amber-50/50 dark:border-neutral-700/80 dark:hover:border-amber-600/60 dark:hover:bg-neutral-800/80"
      >
        <div class="flex h-8 w-8 items-center justify-center rounded-lg" :class="item.iconBg">
          <UIcon :name="item.icon" class="h-4.5 w-4.5 text-white" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold text-stone-800 dark:text-stone-100">
            {{ item.label }}
          </p>
          <p class="truncate text-xs text-stone-500 dark:text-stone-400">
            {{ item.desc }}
          </p>
        </div>
        <UIcon
          name="heroicons:chevron-right"
          class="h-4 w-4 text-stone-400 transition-transform group-hover:translate-x-0.5 group-hover:text-amber-500"
        />
      </NuxtLink>
    </div>
  </UCard>
</template>

<script setup lang="ts">
const actions = [
  {
    to: '/admin/images',
    label: '图片管理',
    desc: '检索、清理、查看详情',
    icon: 'heroicons:photo',
    iconBg: 'bg-gradient-to-br from-violet-500 to-fuchsia-500',
  },
  {
    to: '/admin/tokens',
    label: 'Token 管理',
    desc: '创建、禁用与批量操作',
    icon: 'heroicons:key',
    iconBg: 'bg-gradient-to-br from-cyan-500 to-sky-500',
  },
  {
    to: '/admin/galleries',
    label: '画集管理',
    desc: '维护分享入口与访问控制',
    icon: 'heroicons:rectangle-stack',
    iconBg: 'bg-gradient-to-br from-emerald-500 to-teal-500',
  },
  {
    to: '/admin/storage',
    label: '存储设置',
    desc: '切换存储、路由与策略',
    icon: 'heroicons:server-stack',
    iconBg: 'bg-gradient-to-br from-orange-500 to-amber-500',
  },
  {
    to: '/admin/settings',
    label: '系统设置',
    desc: '游客策略与全局开关',
    icon: 'heroicons:cog-6-tooth',
    iconBg: 'bg-gradient-to-br from-blue-500 to-indigo-500',
  },
  {
    to: '/admin/announcements',
    label: '公告管理',
    desc: '更新站点公告与模板',
    icon: 'heroicons:megaphone',
    iconBg: 'bg-gradient-to-br from-rose-500 to-pink-500',
  },
]
</script>
