import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import RoutePanel from '@/components/scheme-a/RoutePanel.vue'

const stubs = {
    ScoreRing: {
        name: 'ScoreRing',
        template: '<span class="score-ring-stub" :data-score="score" />',
        props: ['score', 'size'],
    },
    EventIcon: {
        name: 'EventIcon',
        template: '<span class="event-icon-stub" :data-type="type" />',
        props: ['type', 'size'],
    },
}

const sampleRoute = {
    id: 'route1',
    name: '理小路',
    stops: [
        {
            viewpoint_id: 'zheduo',
            viewpoint_name: '折多山',
            stay_note: '建议停留2小时观赏日出金山',
            forecast: {
                daily: [{
                    best_event: { score: 75 },
                    events: [
                        { event_type: 'golden_mountain', score: 75 },
                    ],
                }],
            },
        },
        {
            viewpoint_id: 'niubei',
            viewpoint_name: '牛背山',
            stay_note: '建议停留3小时，金山+云海组合',
            forecast: {
                daily: [{
                    best_event: { score: 90 },
                    events: [
                        { event_type: 'golden_mountain', score: 90 },
                        { event_type: 'cloud_sea', score: 85 },
                    ],
                }],
            },
        },
    ],
}

describe('RoutePanel', () => {
    function mountPanel(props = {}) {
        return mount(RoutePanel, {
            props: { route: sampleRoute, ...props },
            global: { stubs },
        })
    }

    // --- 结构 ---
    it('renders route name and stop count in header', () => {
        const wrapper = mountPanel()
        expect(wrapper.text()).toContain('理小路')
        expect(wrapper.text()).toContain('2站')
    })

    it('renders close button', () => {
        const wrapper = mountPanel()
        expect(wrapper.find('.close-btn').exists()).toBe(true)
    })

    it('renders all stops with order numbers', () => {
        const wrapper = mountPanel()
        const stops = wrapper.findAll('.stop-item')
        expect(stops.length).toBe(2)
        expect(wrapper.text()).toContain('1')
        expect(wrapper.text()).toContain('2')
    })

    it('renders stop names', () => {
        const wrapper = mountPanel()
        expect(wrapper.text()).toContain('折多山')
        expect(wrapper.text()).toContain('牛背山')
    })

    it('renders stay notes', () => {
        const wrapper = mountPanel()
        expect(wrapper.text()).toContain('建议停留2小时观赏日出金山')
        expect(wrapper.text()).toContain('建议停留3小时，金山+云海组合')
    })

    it('renders ScoreRing for each stop', () => {
        const wrapper = mountPanel()
        const rings = wrapper.findAll('.score-ring-stub')
        expect(rings.length).toBe(2)
        expect(rings[0].attributes('data-score')).toBe('75')
        expect(rings[1].attributes('data-score')).toBe('90')
    })

    it('renders EventIcons for events with score >= 50', () => {
        const wrapper = mountPanel()
        const icons = wrapper.findAll('.event-icon-stub')
        // 折多山: 1 event (75), 牛背山: 2 events (90, 85)
        expect(icons.length).toBe(3)
    })

    // --- 选中态 ---
    it('applies active class to selected stop', () => {
        const wrapper = mountPanel({ selectedStopId: 'niubei' })
        const stops = wrapper.findAll('.stop-item')
        expect(stops[0].classes()).not.toContain('active')
        expect(stops[1].classes()).toContain('active')
    })

    // --- 交互 ---
    it('emits close when close button clicked', async () => {
        const wrapper = mountPanel()
        await wrapper.find('.close-btn').trigger('click')
        expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('emits select-stop when stop item clicked', async () => {
        const wrapper = mountPanel()
        const stops = wrapper.findAll('.stop-item')
        await stops[0].trigger('click')
        expect(wrapper.emitted('select-stop')).toBeTruthy()
        expect(wrapper.emitted('select-stop')[0][0]).toEqual(sampleRoute.stops[0])
    })

    // --- scrollToStop exposed method ---
    it('exposes scrollToStop method', () => {
        const wrapper = mountPanel()
        expect(typeof wrapper.vm.scrollToStop).toBe('function')
    })
})
