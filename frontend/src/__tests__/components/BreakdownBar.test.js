import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BreakdownBar from '@/components/score/BreakdownBar.vue'

const sampleBreakdown = {
    light_path: { score: 30, max: 35 },
    target_visible: { score: 35, max: 40 },
    local_clear: { score: 25, max: 25 },
}

const sampleLabelMap = {
    light_path: '光路',
    target_visible: '目标',
    local_clear: '本地',
}

describe('BreakdownBar', () => {
    it('renders correct number of segments matching breakdown entries', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: sampleBreakdown, labelMap: sampleLabelMap },
        })
        const segments = wrapper.findAll('.breakdown-bar__segment')
        expect(segments).toHaveLength(3)
    })

    it('calculates segment widths as percentage of total max', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: sampleBreakdown, labelMap: sampleLabelMap },
        })
        const segments = wrapper.findAll('.breakdown-bar__segment')
        // totalMax = 35 + 40 + 25 = 100
        // light_path width = 35/100 = 35%
        expect(segments[0].element.style.width).toBe('35%')
        // target_visible width = 40/100 = 40%
        expect(segments[1].element.style.width).toBe('40%')
        // local_clear width = 25/100 = 25%
        expect(segments[2].element.style.width).toBe('25%')
    })

    it('calculates fill percentage as score / max', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: sampleBreakdown, labelMap: sampleLabelMap },
        })
        const fills = wrapper.findAll('.breakdown-bar__fill')
        // light_path: 30/35 ≈ 85.71%
        const fill0Width = parseFloat(fills[0].element.style.width)
        expect(fill0Width).toBeCloseTo(85.71, 0)
        // target_visible: 35/40 = 87.5%
        const fill1Width = parseFloat(fills[1].element.style.width)
        expect(fill1Width).toBeCloseTo(87.5, 0)
        // local_clear: 25/25 = 100%
        expect(fills[2].element.style.width).toBe('100%')
    })

    it('displays correct total score', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: sampleBreakdown, labelMap: sampleLabelMap },
        })
        const total = wrapper.find('.breakdown-bar__total')
        // totalScore = 30 + 35 + 25 = 90, totalMax = 100
        expect(total.text()).toBe('90/100')
    })

    it('shows dimension label and score in segment labels', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: sampleBreakdown, labelMap: sampleLabelMap },
        })
        const labels = wrapper.findAll('.breakdown-bar__label')
        const texts = labels.map(l => l.text())
        expect(texts).toContain('光路 30')
        expect(texts).toContain('目标 35')
        expect(texts).toContain('本地 25')
    })

    it('does not render when breakdown is empty', () => {
        const wrapper = mount(BreakdownBar, {
            props: { breakdown: {}, labelMap: {} },
        })
        expect(wrapper.find('.breakdown-bar').exists()).toBe(false)
    })
})
