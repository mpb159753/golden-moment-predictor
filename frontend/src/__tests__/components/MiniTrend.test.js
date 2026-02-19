import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MiniTrend from '@/components/forecast/MiniTrend.vue'

describe('MiniTrend', () => {
    const mockDaily = [
        { date: '2026-02-19', best_event: { event_type: 'clear_sky', score: 30 } },
        { date: '2026-02-20', best_event: { event_type: 'clear_sky', score: 39 } },
        { date: '2026-02-21', best_event: { event_type: 'sunset_golden_mountain', score: 50 } },
        { date: '2026-02-22', best_event: { event_type: 'sunset_golden_mountain', score: 90 } },
        { date: '2026-02-23', best_event: { event_type: 'clear_sky', score: 55 } },
        { date: '2026-02-24', best_event: { event_type: 'clear_sky', score: 30 } },
        { date: '2026-02-25', best_event: { event_type: 'clear_sky', score: 5 } },
    ]

    it('renders N .trend-day elements matching daily array length', () => {
        const wrapper = mount(MiniTrend, { props: { daily: mockDaily } })
        expect(wrapper.findAll('.trend-day')).toHaveLength(7)
    })

    it('displays date number', () => {
        const wrapper = mount(MiniTrend, { props: { daily: mockDaily } })
        const days = wrapper.findAll('.trend-day')
        expect(days[0].text()).toContain('19')
    })

    it('displays score', () => {
        const wrapper = mount(MiniTrend, { props: { daily: mockDaily } })
        const days = wrapper.findAll('.trend-day')
        expect(days[3].text()).toContain('90')
    })

    it('emits select event with date string on click', async () => {
        const wrapper = mount(MiniTrend, { props: { daily: mockDaily } })
        const days = wrapper.findAll('.trend-day')
        await days[2].trigger('click')
        expect(wrapper.emitted('select')).toBeTruthy()
        expect(wrapper.emitted('select')[0]).toEqual(['2026-02-21'])
    })

    it('applies .selected class to selectedDate', () => {
        const wrapper = mount(MiniTrend, {
            props: { daily: mockDaily, selectedDate: '2026-02-22' },
        })
        const days = wrapper.findAll('.trend-day')
        expect(days[3].classes()).toContain('selected')
        expect(days[0].classes()).not.toContain('selected')
    })
})
