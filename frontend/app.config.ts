export default defineAppConfig({
  ui: {
    primary: 'amber',
    gray: 'slate',
    notifications: {
      position: 'top-0 right-0'
    },
    // 全局 Modal 默认配置，避免在 app.vue 中用 !important 强制覆盖
    modal: {
      container: 'flex items-center justify-center',
      inner: 'fixed inset-0 overflow-y-auto',
      base: 'relative overflow-hidden flex flex-col max-h-[90vh]'
    }
  }
})
