import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'

export const useViewpointStore = defineStore('viewpoints', () => {
    const { loadIndex, loadForecast, loadTimeline } = useDataLoader()

    // --- State ---
    const index = ref([])           // index.json → viewpoints 数组
    const meta = ref(null)          // meta.json
    const forecasts = ref({})       // { viewpointId: forecast.json }
    const timelines = ref({})       // { "viewpointId:date": timeline.json }
    const selectedId = ref(null)    // 当前选中的观景台 ID
    const selectedDate = ref(null)  // 当前选中的日期 (默认=今天)
    const loading = ref(false)
    const error = ref(null)

    // --- Getters ---

    /** 当前选中的观景台信息 (来自 index) */
    const currentViewpoint = computed(() =>
        index.value.find(v => v.id === selectedId.value)
    )

    /** 当前选中观景台的预测数据 */
    const currentForecast = computed(() =>
        forecasts.value[selectedId.value] ?? null
    )

    /** 当前选中日期的事件列表 */
    const currentDayEvents = computed(() => {
        const forecast = currentForecast.value
        if (!forecast || !selectedDate.value) return []
        const day = forecast.daily?.find(d => d.date === selectedDate.value)
        return day?.events ?? []
    })

    /** 当前选中日期的逐时数据 */
    const currentTimeline = computed(() => {
        const key = `${selectedId.value}:${selectedDate.value}`
        return timelines.value[key] ?? null
    })

    // --- Actions ---

    /** 初始化: 加载索引 + 元数据 */
    async function init() {
        loading.value = true
        error.value = null
        try {
            const { index: idx, meta: m } = await loadIndex()
            index.value = idx.viewpoints
            meta.value = m
            // 默认日期 = 今天 (YYYY-MM-DD)
            if (!selectedDate.value) {
                selectedDate.value = new Date().toISOString().split('T')[0]
            }
        } catch (e) {
            error.value = e.message
        } finally {
            loading.value = false
        }
    }

    /** 选择观景台 → 自动加载预测 */
    async function selectViewpoint(id) {
        selectedId.value = id
        if (!forecasts.value[id]) {
            loading.value = true
            try {
                forecasts.value[id] = await loadForecast(id)
            } catch (e) {
                error.value = e.message
            } finally {
                loading.value = false
            }
        }
    }

    /** 选择日期 → 自动加载逐时数据 */
    async function selectDate(date) {
        selectedDate.value = date
        const key = `${selectedId.value}:${date}`
        if (selectedId.value && !timelines.value[key]) {
            loading.value = true
            try {
                timelines.value[key] = await loadTimeline(selectedId.value, date)
            } catch (e) {
                error.value = e.message
            } finally {
                loading.value = false
            }
        }
    }

    return {
        // State
        index, meta, forecasts, timelines, selectedId, selectedDate, loading, error,
        // Getters
        currentViewpoint, currentForecast, currentDayEvents, currentTimeline,
        // Actions
        init, selectViewpoint, selectDate,
    }
})
