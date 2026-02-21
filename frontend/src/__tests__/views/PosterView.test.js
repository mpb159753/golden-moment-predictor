import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PosterView from '@/views/PosterView.vue'

const mockPosterData = {
    generated_at: '2026-02-21T08:00:00+08:00',
    days: ['2026-02-21', '2026-02-22', '2026-02-23', '2026-02-24', '2026-02-25'],
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

    it('day selector defaults to 5', async () => {
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        // 默认选中 5 天按钮
        const activeBtn = wrapper.find('.day-btn.active')
        expect(activeBtn?.text()).toBe('5天')
    })
})
