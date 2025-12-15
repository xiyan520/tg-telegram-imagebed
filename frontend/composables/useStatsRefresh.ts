// 统计数据刷新事件总线
import { ref } from 'vue'

// 创建一个全局的刷新触发器
const refreshTrigger = ref(0)

export const useStatsRefresh = () => {
  // 触发统计数据刷新
  const triggerStatsRefresh = () => {
    refreshTrigger.value++
  }

  // 监听统计数据刷新
  const onStatsRefresh = (callback: () => void) => {
    watch(refreshTrigger, () => {
      callback()
    })
  }

  return {
    refreshTrigger,
    triggerStatsRefresh,
    onStatsRefresh
  }
}
