import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TimePeriodBar from '@/components/forecast/TimePeriodBar.vue'

describe('TimePeriodBar', () => {
    const mockPeriods = [
        { id: 'sunrise', label: '日出', icon: '🌄', start: 5, end: 8, bestScore: 85, bestEvent: 'clear_sky', events: [] },
        { id: 'daytime', label: '白天', icon: '☀️', start: 8, end: 16, bestScore: 0, bestEvent: null, events: [] },
        { id: 'sunset', label: '日落', icon: '🌅', start: 16, end: 19, bestScore: 72, bestEvent: 'sunset_golden_mountain', events: [] },
        { id: 'night', label: '夜晚', icon: '⭐', start: 19, end: 5, bestScore: 60, bestEvent: 'stargazing', events: [] },
    ]

    it('renders 4 .period-cell elements', () => {
        const wrapper = mount(TimePeriodBar, { props: { periods: mockPeriods } })
        expect(wrapper.findAll('.period-cell')).toHaveLength(4)
    })

    it('displays period label and icon', () => {
        const wrapper = mount(TimePeriodBar, { props: { periods: mockPeriods } })
        const cells = wrapper.findAll('.period-cell')
        expect(cells[0].text()).toContain('日出')
        expect(cells[0].text()).toContain('🌄')
    })

    it('displays score when bestScore > 0', () => {
        const wrapper = mount(TimePeriodBar, { props: { periods: mockPeriods } })
        const cells = wrapper.findAll('.period-cell')
        expect(cells[0].text()).toContain('85')
    })

    it('displays -- for zero score period', () => {
        const wrapper = mount(TimePeriodBar, { props: { periods: mockPeriods } })
        const cells = wrapper.findAll('.period-cell')
        // daytime has bestScore=0
        expect(cells[1].text()).toContain('--')
    })
})
