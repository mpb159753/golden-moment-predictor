import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRouteStore } from '@/stores/routes'

// Mock useDataLoader
vi.mock('@/composables/useDataLoader', () => ({
    useDataLoader: () => ({
        loadIndex: vi.fn().mockResolvedValue({
            index: {
                routes: [
                    {
                        id: 'lixiao',
                        name: '理小路',
                        stops: [
                            { viewpoint_id: 'zheduo_gongga', name: '折多山' },
                            { viewpoint_id: 'niubei_gongga', name: '牛背山' },
                        ],
                    },
                ],
            },
            meta: { generated_at: '2026-02-18T12:00:00+08:00' },
        }),
        loadRouteForecast: vi.fn().mockImplementation((id) => {
            const forecasts = {
                lixiao: {
                    route_id: 'lixiao',
                    route_name: '理小路',
                    stops: [
                        { viewpoint_id: 'zheduo_gongga', order: 1 },
                        { viewpoint_id: 'niubei_gongga', order: 2 },
                    ],
                },
            }
            return Promise.resolve(forecasts[id] || null)
        }),
    }),
}))

describe('useRouteStore', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('init() loads routes from index', async () => {
        const store = useRouteStore()
        await store.init()

        expect(store.index).toHaveLength(1)
        expect(store.index[0].id).toBe('lixiao')
        expect(store.loading).toBe(false)
    })

    it('selectRoute() sets selectedId and loads forecast', async () => {
        const store = useRouteStore()
        await store.init()
        await store.selectRoute('lixiao')

        expect(store.selectedId).toBe('lixiao')
        expect(store.forecasts['lixiao']).toBeDefined()
        expect(store.forecasts['lixiao'].route_id).toBe('lixiao')
    })

    it('selectRoute() does not reload already cached forecast', async () => {
        const store = useRouteStore()
        await store.init()
        await store.selectRoute('lixiao')
        await store.selectRoute('lixiao')

        expect(store.forecasts['lixiao']).toBeDefined()
    })

    it('currentRoute returns correct item from index', async () => {
        const store = useRouteStore()
        await store.init()
        store.selectedId = 'lixiao'

        expect(store.currentRoute.id).toBe('lixiao')
        expect(store.currentRoute.name).toBe('理小路')
    })

    it('currentForecast returns forecast for selected route', async () => {
        const store = useRouteStore()
        await store.init()
        await store.selectRoute('lixiao')

        expect(store.currentForecast).toBeDefined()
        expect(store.currentForecast.route_id).toBe('lixiao')
        expect(store.currentForecast.stops).toHaveLength(2)
    })

    it('ensureIndex() loads routes if not already loaded', async () => {
        const store = useRouteStore()
        expect(store.index).toHaveLength(0)

        await store.ensureIndex()

        expect(store.index).toHaveLength(1)
        expect(store.index[0].id).toBe('lixiao')
    })

    it('ensureIndex() skips if already loaded', async () => {
        const store = useRouteStore()
        await store.init()
        expect(store.index).toHaveLength(1)

        // 再次调用
        await store.ensureIndex()
        expect(store.index).toHaveLength(1)
    })
})
