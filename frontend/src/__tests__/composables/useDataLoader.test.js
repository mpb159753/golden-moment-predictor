import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useDataLoader } from '@/composables/useDataLoader'

describe('useDataLoader', () => {
    let originalFetch

    beforeEach(() => {
        originalFetch = globalThis.fetch
    })

    afterEach(() => {
        globalThis.fetch = originalFetch
    })

    function mockFetch(responses = {}) {
        globalThis.fetch = vi.fn((url) => {
            const key = url.replace('/data/', '')
            const data = responses[key]
            if (data === undefined) {
                return Promise.resolve({
                    ok: false,
                    status: 404,
                    json: () => Promise.resolve({}),
                })
            }
            return Promise.resolve({
                ok: true,
                status: 200,
                json: () => Promise.resolve(data),
            })
        })
    }

    it('loadIndex() returns parsed index and meta objects', async () => {
        const indexData = { viewpoints: [{ id: 'test' }], routes: [] }
        const metaData = { generated_at: '2026-02-18T12:00:00+08:00' }
        mockFetch({ 'index.json': indexData, 'meta.json': metaData })

        const { loadIndex } = useDataLoader()
        const result = await loadIndex()

        expect(result.index).toEqual(indexData)
        expect(result.meta).toEqual(metaData)
        expect(globalThis.fetch).toHaveBeenCalledTimes(2)
    })

    it('loadForecast() requests correct URL and returns JSON', async () => {
        const forecastData = { viewpoint_id: 'niubei_gongga', daily: [] }
        mockFetch({ 'viewpoints/niubei_gongga/forecast.json': forecastData })

        const { loadForecast } = useDataLoader()
        const result = await loadForecast('niubei_gongga')

        expect(result).toEqual(forecastData)
        expect(globalThis.fetch).toHaveBeenCalledWith('/data/viewpoints/niubei_gongga/forecast.json')
    })

    it('loadTimeline() requests correct URL with date', async () => {
        const timelineData = { viewpoint_id: 'niubei_gongga', date: '2026-02-18', hourly: [] }
        mockFetch({ 'viewpoints/niubei_gongga/timeline_2026-02-18.json': timelineData })

        const { loadTimeline } = useDataLoader()
        const result = await loadTimeline('niubei_gongga', '2026-02-18')

        expect(result).toEqual(timelineData)
        expect(globalThis.fetch).toHaveBeenCalledWith('/data/viewpoints/niubei_gongga/timeline_2026-02-18.json')
    })

    it('loadRouteForecast() requests correct URL and returns JSON', async () => {
        const routeData = { route_id: 'lixiao', stops: [] }
        mockFetch({ 'routes/lixiao/forecast.json': routeData })

        const { loadRouteForecast } = useDataLoader()
        const result = await loadRouteForecast('lixiao')

        expect(result).toEqual(routeData)
        expect(globalThis.fetch).toHaveBeenCalledWith('/data/routes/lixiao/forecast.json')
    })

    it('caches results - same URL only fetched once', async () => {
        const forecastData = { viewpoint_id: 'test', daily: [] }
        mockFetch({ 'viewpoints/test/forecast.json': forecastData })

        const { loadForecast } = useDataLoader()
        const result1 = await loadForecast('test')
        const result2 = await loadForecast('test')

        expect(result1).toEqual(forecastData)
        expect(result2).toEqual(forecastData)
        expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    })

    it('throws on 404 and sets error.value', async () => {
        mockFetch({}) // no responses = 404

        const { loadForecast, error } = useDataLoader()
        await expect(loadForecast('nonexistent')).rejects.toThrow('Failed to load')
        expect(error.value).toContain('Failed to load')
    })

    it('loadPoster() requests correct URL and returns JSON', async () => {
        const posterData = { generated_at: '2026-02-21T08:00:00+08:00', days: ['2026-02-21'], groups: [] }
        mockFetch({ 'poster.json': posterData })

        const { loadPoster } = useDataLoader()
        const result = await loadPoster()

        expect(result).toEqual(posterData)
        expect(globalThis.fetch).toHaveBeenCalledWith('/data/poster.json')
    })

    it('loading.value is true during fetch and false after', async () => {
        let resolvePromise
        globalThis.fetch = vi.fn(() => new Promise((resolve) => {
            resolvePromise = resolve
        }))

        const { loadForecast, loading } = useDataLoader()
        expect(loading.value).toBe(false)

        const promise = loadForecast('test')
        expect(loading.value).toBe(true)

        resolvePromise({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ data: 'test' }),
        })
        await promise
        expect(loading.value).toBe(false)
    })
})
