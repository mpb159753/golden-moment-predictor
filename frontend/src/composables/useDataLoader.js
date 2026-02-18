import { ref } from 'vue'

/**
 * JSON 数据加载 composable，提供统一的数据获取+缓存机制。
 *
 * 加载策略:
 * - 内存缓存: Map<url, data>，页面生命周期内有效
 * - 重复请求: 同一 URL 不重复 fetch
 * - 错误处理: fetch 失败抛出，调用方自行处理
 *
 * @returns {Object} { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loading, error }
 */
export function useDataLoader() {
    const cache = new Map()
    const loading = ref(false)
    const error = ref(null)

    /**
     * 通用加载函数 (内部)
     * @param {string} url - 数据 URL (相对于 /data/)
     * @returns {Promise<Object>} 解析后的 JSON 对象
     */
    async function _fetch(url) {
        if (cache.has(url)) return cache.get(url)
        loading.value = true
        error.value = null
        const promise = fetch(`/data/${url}`)
            .then(async (resp) => {
                if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`)
                return resp.json()
            })
            .catch((e) => {
                cache.delete(url)
                error.value = e.message
                throw e
            })
            .finally(() => {
                loading.value = false
            })
        cache.set(url, promise)
        return promise
    }

    /**
     * 加载全局索引 + 元数据
     * @returns {Promise<{index: Object, meta: Object}>}
     */
    async function loadIndex() {
        const [index, meta] = await Promise.all([
            _fetch('index.json'),
            _fetch('meta.json'),
        ])
        return { index, meta }
    }

    /**
     * 加载观景台预测数据
     * @param {string} viewpointId - 观景台 ID (如 'niubei_gongga')
     * @returns {Promise<Object>} forecast.json 内容
     */
    async function loadForecast(viewpointId) {
        return _fetch(`viewpoints/${viewpointId}/forecast.json`)
    }

    /**
     * 加载逐时数据
     * @param {string} viewpointId - 观景台 ID
     * @param {string} date - 日期 'YYYY-MM-DD'
     * @returns {Promise<Object>} timeline_YYYY-MM-DD.json 内容
     */
    async function loadTimeline(viewpointId, date) {
        return _fetch(`viewpoints/${viewpointId}/timeline_${date}.json`)
    }

    /**
     * 加载线路预测数据
     * @param {string} routeId - 线路 ID (如 'lixiao')
     * @returns {Promise<Object>} 线路 forecast.json 内容
     */
    async function loadRouteForecast(routeId) {
        return _fetch(`routes/${routeId}/forecast.json`)
    }

    return { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loading, error }
}
