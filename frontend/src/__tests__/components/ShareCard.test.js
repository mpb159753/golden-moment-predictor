import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock useScreenshot composable
vi.mock('@/composables/useScreenshot', () => ({
    useScreenshot: () => ({
        capture: vi.fn(() => Promise.resolve()),
        captureToCanvas: vi.fn(),
    }),
}))

// Mock SVG imports used by EventIcon
vi.mock('@/assets/icons/sunrise-golden-mountain.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/sunset-golden-mountain.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/cloud-sea.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/stargazing.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/frost.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/snow-tree.svg', () => ({ default: { template: '<svg />' } }))
vi.mock('@/assets/icons/ice-icicle.svg', () => ({ default: { template: '<svg />' } }))

import ShareCard from '@/components/export/ShareCard.vue'

const mockViewpoint = {
    name: '牛背山',
}

const mockDay = {
    date: '2026-02-12',
    best_score: 90,
    best_status: 'Recommended',
    events: [
        { event_type: 'sunrise_golden_mountain', display_name: '日出金山', score: 90 },
        { event_type: 'cloud_sea', display_name: '云海', score: 90 },
        { event_type: 'stargazing', display_name: '观星', score: 45 },
    ],
}

const mountOptions = {
    global: {
        stubs: {
            teleport: true,
        },
    },
}

describe('ShareCard', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('does not render when visible is false', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: false },
            ...mountOptions,
        })
        expect(wrapper.find('.share-overlay').exists()).toBe(false)
    })

    it('renders overlay when visible is true', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        expect(wrapper.find('.share-overlay').exists()).toBe(true)
        expect(wrapper.find('.share-card').exists()).toBe(true)
    })

    it('displays viewpoint name and formatted date', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const heading = wrapper.find('.share-card__content h2')
        expect(heading.text()).toContain('牛背山')
        expect(heading.text()).toContain('2月12日')
    })

    it('displays brand header', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        expect(wrapper.find('.share-card__header').exists()).toBe(true)
        expect(wrapper.find('.share-card__brand').text()).toContain('GMP 川西景观预测')
    })

    it('renders event rows for all events', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const eventRows = wrapper.findAll('.share-card__event-row')
        expect(eventRows.length).toBe(3)
    })

    it('displays event scores', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const scores = wrapper.findAll('.share-card__event-score')
        expect(scores[0].text()).toBe('90')
        expect(scores[1].text()).toBe('90')
        expect(scores[2].text()).toBe('45')
    })

    it('displays combo tags when conditions met', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const tags = wrapper.find('.share-card__tags')
        expect(tags.exists()).toBe(true)
        // Should have combo_day (2+ recommended) and photographer_pick (golden_mountain + cloud_sea)
        expect(tags.text()).toContain('组合日')
        expect(tags.text()).toContain('摄影师推荐')
    })

    it('displays brand footer slogan', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const footer = wrapper.find('.share-card__footer')
        expect(footer.text()).toContain('让每一次川西之行')
    })

    it('emits close event when overlay background is clicked', async () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        await wrapper.find('.share-overlay').trigger('click')
        expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('emits close event when close button is clicked', async () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        // The close button is the last button in the actions area
        const buttons = wrapper.findAll('.share-overlay__actions button')
        const closeBtn = buttons[buttons.length - 1]
        await closeBtn.trigger('click')
        expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('includes ScreenshotBtn in actions', () => {
        const wrapper = mount(ShareCard, {
            props: { viewpoint: mockViewpoint, day: mockDay, visible: true },
            ...mountOptions,
        })
        const actions = wrapper.find('.share-overlay__actions')
        expect(actions.exists()).toBe(true)
        expect(actions.find('.screenshot-btn').exists()).toBe(true)
    })
})
