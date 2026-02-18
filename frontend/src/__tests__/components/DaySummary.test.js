import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DaySummary from '@/components/forecast/DaySummary.vue'

// Stub child components to isolate DaySummary
const stubs = {
    EventIcon: { template: '<span class="event-icon-stub" />', props: ['eventType', 'size'] },
    ScoreRing: { template: '<span class="score-ring-stub" />', props: ['score', 'size'] },
    StatusBadge: { template: '<span class="status-badge-stub">{{ status }}</span>', props: ['status'] },
}

function createDay(overrides = {}) {
    return {
        date: '2026-02-12',
        summary: '🌄☁️ 日照金山+壮观云海 — 绝佳组合日',
        best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
        events: [
            { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
            { event_type: 'cloud_sea', score: 90, status: 'Recommended' },
            { event_type: 'stargazing', score: 45, status: 'Possible' },
        ],
        ...overrides,
    }
}

describe('DaySummary', () => {
    it('renders formatted date with weekday', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay() },
            global: { stubs },
        })
        // 2026-02-12 is a Thursday (周四)
        const dateEl = wrapper.find('.day-summary__date')
        expect(dateEl.exists()).toBe(true)
        expect(dateEl.text()).toContain('2月12日')
        expect(dateEl.text()).toContain('周四')
    })

    it('renders summary text', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay() },
            global: { stubs },
        })
        const textEl = wrapper.find('.day-summary__text')
        expect(textEl.exists()).toBe(true)
        expect(textEl.text()).toContain('日照金山+壮观云海')
    })

    it('renders event chips for each event', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay() },
            global: { stubs },
        })
        const chips = wrapper.findAll('.day-summary__event-chip')
        expect(chips).toHaveLength(3)
    })

    it('renders combo tags when conditions are met', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay() },
            global: { stubs },
        })
        const tags = wrapper.findAll('.day-summary__tag')
        // 2 events >=80 → combo_day; golden_mountain + cloud_sea → photographer_pick
        expect(tags.length).toBeGreaterThanOrEqual(2)
        const tagTexts = tags.map(t => t.text())
        expect(tagTexts.some(t => t.includes('组合日'))).toBe(true)
        expect(tagTexts.some(t => t.includes('摄影师推荐'))).toBe(true)
    })

    it('does not render combo tags when no conditions met', () => {
        const wrapper = mount(DaySummary, {
            props: {
                day: createDay({
                    events: [
                        { event_type: 'stargazing', score: 40, status: 'Not Recommended' },
                    ],
                }),
            },
            global: { stubs },
        })
        const tagsContainer = wrapper.find('.day-summary__tags')
        expect(tagsContainer.exists()).toBe(false)
    })

    it('emits select event with date when clickable and clicked', async () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay(), clickable: true },
            global: { stubs },
        })
        await wrapper.find('.day-summary').trigger('click')
        expect(wrapper.emitted('select')).toBeTruthy()
        expect(wrapper.emitted('select')[0]).toEqual(['2026-02-12'])
    })

    it('does not emit select event when clickable is false', async () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay(), clickable: false },
            global: { stubs },
        })
        await wrapper.find('.day-summary').trigger('click')
        expect(wrapper.emitted('select')).toBeFalsy()
    })

    it('applies clickable class when clickable prop is true', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay(), clickable: true },
            global: { stubs },
        })
        expect(wrapper.find('.day-summary--clickable').exists()).toBe(true)
    })

    it('does not apply clickable class when clickable is false', () => {
        const wrapper = mount(DaySummary, {
            props: { day: createDay(), clickable: false },
            global: { stubs },
        })
        expect(wrapper.find('.day-summary--clickable').exists()).toBe(false)
    })
})
