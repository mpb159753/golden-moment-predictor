import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BreakdownTable from '@/components/forecast/BreakdownTable.vue'

// Stub ScoreBar to avoid deep rendering
const stubs = {
    ScoreBar: {
        template: '<div class="score-bar-stub"><span class="label">{{ label }}</span><span class="score">{{ score }}/{{ max }}</span></div>',
        props: ['label', 'score', 'max'],
    },
}

const sampleBreakdown = {
    light_path: { score: 35, max: 35 },
    target_visible: { score: 35, max: 40 },
    local_clear: { score: 20, max: 25 },
}

describe('BreakdownTable', () => {
    it('renders a row for each breakdown dimension', () => {
        const wrapper = mount(BreakdownTable, {
            props: { breakdown: sampleBreakdown, totalScore: 90, totalMax: 100 },
            global: { stubs },
        })
        const rows = wrapper.findAll('.breakdown-table__row')
        expect(rows).toHaveLength(3)
    })

    it('passes correct label, score, max to ScoreBar stubs', () => {
        const wrapper = mount(BreakdownTable, {
            props: { breakdown: sampleBreakdown, totalScore: 90, totalMax: 100 },
            global: { stubs },
        })
        const labels = wrapper.findAll('.label').map(el => el.text())
        expect(labels).toContain('光路通畅')
        expect(labels).toContain('目标可见')
        expect(labels).toContain('本地晴朗')
    })

    it('renders total score', () => {
        const wrapper = mount(BreakdownTable, {
            props: { breakdown: sampleBreakdown, totalScore: 90, totalMax: 100 },
            global: { stubs },
        })
        const total = wrapper.find('.breakdown-table__total-value')
        expect(total.exists()).toBe(true)
        expect(total.text()).toContain('90')
        expect(total.text()).toContain('100')
    })

    it('falls back to key name for unknown dimension keys', () => {
        const wrapper = mount(BreakdownTable, {
            props: {
                breakdown: { unknown_key: { score: 10, max: 20 } },
                totalScore: 10,
                totalMax: 20,
            },
            global: { stubs },
        })
        const labels = wrapper.findAll('.label').map(el => el.text())
        expect(labels).toContain('unknown_key')
    })

    it('renders empty table when breakdown is empty', () => {
        const wrapper = mount(BreakdownTable, {
            props: { breakdown: {}, totalScore: 0, totalMax: 100 },
            global: { stubs },
        })
        const rows = wrapper.findAll('.breakdown-table__row')
        expect(rows).toHaveLength(0)
    })

    it('maps known dimension keys to Chinese names', () => {
        const wrapper = mount(BreakdownTable, {
            props: {
                breakdown: {
                    humidity: { score: 15, max: 20 },
                    moon_phase: { score: 8, max: 10 },
                },
                totalScore: 23,
                totalMax: 30,
            },
            global: { stubs },
        })
        const labels = wrapper.findAll('.label').map(el => el.text())
        expect(labels).toContain('湿度条件')
        expect(labels).toContain('月相')
    })
})
