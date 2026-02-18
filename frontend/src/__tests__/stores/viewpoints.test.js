import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useViewpointStore } from '@/stores/viewpoints'

// Mock useDataLoader
vi.mock('@/composables/useDataLoader', () => ({
    useDataLoader: () => ({
        loadIndex: vi.fn().mockResolvedValue({
            index: {
                viewpoints: [
                    { id: 'niubei_gongga', name: '牛背山' },
                    { id: 'zheduo_gongga', name: '折多山' },
                ],
            },
            meta: { generated_at: '2026-02-18T12:00:00+08:00' },
        }),
        loadForecast: vi.fn().mockImplementation((id) => {
            const forecasts = {
                niubei_gongga: {
                    viewpoint_id: 'niubei_gongga',
                    daily: [
                        {
                            date: '2026-02-18',
                            events: [
                                { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                                { event_type: 'cloud_sea', score: 85, status: 'Recommended' },
                            ],
                        },
                    ],
                },
            }
            return Promise.resolve(forecasts[id] || null)
        }),
        loadTimeline: vi.fn().mockResolvedValue({
            viewpoint_id: 'niubei_gongga',
            date: '2026-02-18',
            hourly: [{ hour: 6, time: '06:00' }],
        }),
    }),
}))

describe('useViewpointStore', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('init() loads index and meta, sets index and default date', async () => {
        const store = useViewpointStore()
        await store.init()

        expect(store.index).toHaveLength(2)
        expect(store.index[0].id).toBe('niubei_gongga')
        expect(store.meta).toEqual({ generated_at: '2026-02-18T12:00:00+08:00' })
        expect(store.selectedDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
        expect(store.loading).toBe(false)
    })

    it('selectViewpoint() sets selectedId and loads forecast', async () => {
        const store = useViewpointStore()
        await store.init()
        await store.selectViewpoint('niubei_gongga')

        expect(store.selectedId).toBe('niubei_gongga')
        expect(store.forecasts['niubei_gongga']).toBeDefined()
        expect(store.forecasts['niubei_gongga'].viewpoint_id).toBe('niubei_gongga')
    })

    it('selectViewpoint() does not reload already cached forecast', async () => {
        const store = useViewpointStore()
        await store.init()
        await store.selectViewpoint('niubei_gongga')
        await store.selectViewpoint('niubei_gongga')

        // forecasts should exist, no double loading
        expect(store.forecasts['niubei_gongga']).toBeDefined()
    })

    it('currentViewpoint returns correct item from index', async () => {
        const store = useViewpointStore()
        await store.init()
        store.selectedId = 'zheduo_gongga'

        expect(store.currentViewpoint).toEqual({ id: 'zheduo_gongga', name: '折多山' })
    })

    it('currentForecast returns forecast for selected viewpoint', async () => {
        const store = useViewpointStore()
        await store.init()
        await store.selectViewpoint('niubei_gongga')

        expect(store.currentForecast).toBeDefined()
        expect(store.currentForecast.viewpoint_id).toBe('niubei_gongga')
    })

    it('currentDayEvents returns events for selected date', async () => {
        const store = useViewpointStore()
        await store.init()
        await store.selectViewpoint('niubei_gongga')
        store.selectedDate = '2026-02-18'

        expect(store.currentDayEvents).toHaveLength(2)
        expect(store.currentDayEvents[0].event_type).toBe('sunrise_golden_mountain')
    })

    it('selectDate() sets date and loads timeline', async () => {
        const store = useViewpointStore()
        await store.init()
        await store.selectViewpoint('niubei_gongga')
        await store.selectDate('2026-02-18')

        expect(store.selectedDate).toBe('2026-02-18')
        expect(store.currentTimeline).toBeDefined()
        expect(store.currentTimeline.hourly).toHaveLength(1)
    })
})
