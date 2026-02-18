import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'

export const useRouteStore = defineStore('routes', () => {
    const { loadIndex, loadRouteForecast } = useDataLoader()

    // --- State ---
    const index = ref([])           // index.json → routes 数组
    const forecasts = ref({})       // { routeId: forecast.json }
    const selectedId = ref(null)
    const loading = ref(false)
    const error = ref(null)

    // --- Getters ---
    const currentRoute = computed(() =>
        index.value.find(r => r.id === selectedId.value)
    )
    const currentForecast = computed(() =>
        forecasts.value[selectedId.value] ?? null
    )

    // --- Actions ---
    async function init() {
        loading.value = true
        try {
            const { index: idx } = await loadIndex()
            index.value = idx.routes
        } catch (e) {
            error.value = e.message
        } finally {
            loading.value = false
        }
    }

    async function selectRoute(id) {
        selectedId.value = id
        if (!forecasts.value[id]) {
            loading.value = true
            try {
                forecasts.value[id] = await loadRouteForecast(id)
            } catch (e) {
                error.value = e.message
            } finally {
                loading.value = false
            }
        }
    }

    return {
        index, forecasts, selectedId, loading, error,
        currentRoute, currentForecast,
        init, selectRoute,
    }
})
