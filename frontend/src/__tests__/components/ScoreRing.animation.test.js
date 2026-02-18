import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock gsap
const { mockTo } = vi.hoisted(() => ({
    mockTo: vi.fn(),
}))
vi.mock('gsap', () => ({
    default: {
        to: mockTo,
    },
}))

import ScoreRing from '@/components/score/ScoreRing.vue'

describe('ScoreRing - CountUp Animation', () => {
    beforeEach(() => {
        mockTo.mockClear()
    })

    it('animates score from old to new value when score changes and animated is true', async () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, animated: true },
        })

        await wrapper.setProps({ score: 85 })

        expect(mockTo).toHaveBeenCalledTimes(1)
        const [obj, opts] = mockTo.mock.calls[0]
        expect(opts.value).toBe(85)
        expect(opts.duration).toBe(0.8)
        expect(opts.ease).toBe('power2.out')
        expect(typeof opts.onUpdate).toBe('function')
    })

    it('does not animate when animated prop is false', async () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, animated: false },
        })

        await wrapper.setProps({ score: 85 })

        expect(mockTo).not.toHaveBeenCalled()
    })

    it('shows the score directly when animated is false', async () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, animated: false, showLabel: true },
        })

        await wrapper.setProps({ score: 85 })
        await wrapper.vm.$nextTick()

        const label = wrapper.find('.score-ring__label')
        expect(label.text()).toBe('85')
    })
})
