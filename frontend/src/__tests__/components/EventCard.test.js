import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EventCard from '@/components/event/EventCard.vue'

// Stub child components to isolate EventCard behavior
const stubs = {
    EventIcon: { template: '<span class="event-icon-stub" />', props: ['eventType', 'size'] },
    ScoreRing: { template: '<span class="score-ring-stub" />', props: ['score', 'size'] },
    StatusBadge: { template: '<span class="status-badge-stub" />', props: ['status'] },
    BreakdownBar: {
        template: '<div class="breakdown-bar-stub"><span class="bd-breakdown">{{ JSON.stringify(breakdown) }}</span></div>',
        props: ['breakdown', 'labelMap'],
    },
}

const sampleEvent = {
    event_type: 'golden_mountain',
    display_name: '日照金山',
    score: 90,
    status: 'Recommended',
    confidence: 'High',
    time_window: '06:00-08:00',
    score_breakdown: {
        light_path: { score: 30, max: 35 },
        target_visible: { score: 35, max: 40 },
        local_clear: { score: 25, max: 25 },
    },
}

describe('EventCard - BreakdownBar integration', () => {
    it('renders BreakdownBar instead of ScoreBar when showBreakdown is true', () => {
        const wrapper = mount(EventCard, {
            props: { event: sampleEvent, showBreakdown: true },
            global: { stubs },
        })
        expect(wrapper.find('.breakdown-bar-stub').exists()).toBe(true)
        expect(wrapper.findAll('.score-bar').length).toBe(0)
    })

    it('passes breakdown data and labelMap to BreakdownBar', () => {
        const wrapper = mount(EventCard, {
            props: { event: sampleEvent, showBreakdown: true },
            global: { stubs },
        })
        const bdText = wrapper.find('.bd-breakdown').text()
        const bdData = JSON.parse(bdText)
        expect(bdData).toHaveProperty('light_path')
        expect(bdData.light_path.score).toBe(30)
    })

    it('does not render BreakdownBar when showBreakdown is false', () => {
        const wrapper = mount(EventCard, {
            props: { event: sampleEvent, showBreakdown: false },
            global: { stubs },
        })
        expect(wrapper.find('.breakdown-bar-stub').exists()).toBe(false)
    })
})

describe('EventCard - compact header layout', () => {
    it('renders name, time, status, confidence all inside header row', () => {
        const wrapper = mount(EventCard, {
            props: { event: sampleEvent, showBreakdown: false },
            global: { stubs },
        })
        const header = wrapper.find('.event-card__header')
        // All meta info should be inside the header container
        expect(header.text()).toContain('日照金山')
        expect(header.text()).toContain('06:00-08:00')
        expect(header.text()).toContain('高置信')
        // StatusBadge stub should be inside header
        expect(header.find('.status-badge-stub').exists()).toBe(true)
        // ScoreRing stub should be inside header
        expect(header.find('.score-ring-stub').exists()).toBe(true)
    })

    it('does not render separate time and badges rows outside header', () => {
        const wrapper = mount(EventCard, {
            props: { event: sampleEvent, showBreakdown: false },
            global: { stubs },
        })
        // Time should be inside header, not as a separate sibling div
        const header = wrapper.find('.event-card__header')
        expect(header.find('.event-card__time').exists()).toBe(true)
        // No standalone badges container should exist
        expect(wrapper.find('.event-card__badges').exists()).toBe(false)
    })
})

