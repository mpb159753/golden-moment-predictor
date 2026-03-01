import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PosterView from '@/views/PosterView.vue'

// ── 测试用 posterData ──
const mockPosterData = {
    generated_at: '2026-02-21T08:00:00+08:00',
    days: ['2026-02-21', '2026-02-22', '2026-02-23', '2026-02-24', '2026-02-25', '2026-02-26', '2026-02-27', '2026-02-28'],
    groups: [
        {
            name: '贡嘎山系',
            key: 'gongga',
            viewpoints: [{ id: 'niubei_gongga', name: '牛背山', daily: [] }],
        },
        {
            name: '四姑娘山',
            key: 'siguniang',
            viewpoints: [{ id: 'siguniang_changping', name: '长坪沟', daily: [] }],
        },
    ],
}

// Mock vue-router
const mockRouteQuery = {}
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockRouteQuery }),
}))

// Mock useDataLoader
const mockLoadPoster = vi.fn()
vi.mock('@/composables/useDataLoader', () => ({
    useDataLoader: () => ({
        loadPoster: mockLoadPoster,
        loading: { value: false },
        error: { value: null },
    }),
}))

// Stub child components
const globalConfig = {
    stubs: {
        PredictionMatrix: { template: '<div class="prediction-matrix-stub" />', props: ['group', 'days', 'showHeader', 'showFooter'] },
    },
}

describe('PosterView', () => {
    beforeEach(() => {
        mockLoadPoster.mockReset()
        mockLoadPoster.mockResolvedValue(mockPosterData)
        // 清空 query
        Object.keys(mockRouteQuery).forEach(k => delete mockRouteQuery[k])
    })

    it('shows loading state before data is loaded', () => {
        mockLoadPoster.mockReturnValue(new Promise(() => { })) // never resolves
        const wrapper = mount(PosterView, { global: globalConfig })
        expect(wrapper.text()).toContain('加载中')
    })

    it('renders all groups after load', async () => {
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        const matrices = wrapper.findAll('.prediction-matrix-stub')
        expect(matrices).toHaveLength(2)
    })

    it('day selector defaults to 7', async () => {
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        const activeBtn = wrapper.find('.day-btn.active')
        expect(activeBtn?.text()).toBe('7天')
    })

    it('reads days from URL query parameter', async () => {
        mockRouteQuery.days = '3'
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        const activeBtn = wrapper.find('.day-btn.active')
        expect(activeBtn?.text()).toBe('3天')
    })
})
