import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    const isMobile = ref(window.innerWidth < 768)
    const sidebarOpen = ref(false)
    const filterEvent = ref(null)       // 当前事件类型筛选
    const filterMinScore = ref(0)       // 最低评分筛选

    // 监听窗口大小变化
    function initResponsive() {
        const handler = () => {
            isMobile.value = window.innerWidth < 768
        }
        window.addEventListener('resize', handler)
        return () => window.removeEventListener('resize', handler)
    }

    return { isMobile, sidebarOpen, filterEvent, filterMinScore, initResponsive }
})
