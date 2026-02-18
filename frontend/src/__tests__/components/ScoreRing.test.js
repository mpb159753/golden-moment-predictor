import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreRing from '@/components/score/ScoreRing.vue'

describe('ScoreRing', () => {
    it('renders SVG with correct dimensions for md size', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 85, size: 'md' },
        })
        const svg = wrapper.find('svg')
        expect(svg.exists()).toBe(true)
        expect(svg.attributes('width')).toBe('48')
        expect(svg.attributes('height')).toBe('48')
    })

    it('renders SVG with correct dimensions for sm size', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, size: 'sm' },
        })
        const svg = wrapper.find('svg')
        expect(svg.attributes('width')).toBe('32')
        expect(svg.attributes('height')).toBe('32')
    })

    it('renders SVG with correct dimensions for lg size', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, size: 'lg' },
        })
        const svg = wrapper.find('svg')
        expect(svg.attributes('width')).toBe('72')
    })

    it('renders SVG with correct dimensions for xl size', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, size: 'xl' },
        })
        const svg = wrapper.find('svg')
        expect(svg.attributes('width')).toBe('120')
    })

    it('uses gradient stroke for Perfect score (96)', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 96 },
        })
        // Perfect score should have a linearGradient defined
        const gradient = wrapper.find('linearGradient')
        expect(gradient.exists()).toBe(true)
        // The foreground circle should reference the gradient
        const circles = wrapper.findAll('circle')
        const foregroundCircle = circles[1]
        expect(foregroundCircle.attributes('stroke')).toMatch(/^url\(#scoreGradient-/)
    })

    it('uses solid green stroke for Recommended score (85)', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 85 },
        })
        const gradient = wrapper.find('linearGradient')
        expect(gradient.exists()).toBe(false)
        const circles = wrapper.findAll('circle')
        const foregroundCircle = circles[1]
        expect(foregroundCircle.attributes('stroke')).toBe('#10B981')
    })

    it('hides label when showLabel is false', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 75, showLabel: false },
        })
        const label = wrapper.find('.score-ring__label')
        expect(label.exists()).toBe(false)
    })

    it('shows label with score value when showLabel is true', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 75, showLabel: true },
        })
        const label = wrapper.find('.score-ring__label')
        expect(label.exists()).toBe(true)
        expect(label.text()).toBe('75')
    })

    it('calculates correct dashOffset for score 50', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 50, size: 'md' },
        })
        // md: diameter=48, strokeWidth=4, radius=48/2-4=20
        // circumference = 2 * PI * 20 = 125.66...
        // dashOffset = circumference * (1 - 50/100) = 62.83...
        const circles = wrapper.findAll('circle')
        const foregroundCircle = circles[1]
        const circumference = 2 * Math.PI * 20
        const expectedOffset = circumference * 0.5
        expect(Number(foregroundCircle.attributes('stroke-dashoffset'))).toBeCloseTo(expectedOffset, 1)
    })

    it('calculates correct dashOffset for score 0', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 0, size: 'md' },
        })
        const circles = wrapper.findAll('circle')
        const foregroundCircle = circles[1]
        const circumference = 2 * Math.PI * 20
        // score=0 → offset = circumference (full offset, no fill)
        expect(Number(foregroundCircle.attributes('stroke-dashoffset'))).toBeCloseTo(circumference, 1)
    })

    it('calculates correct dashOffset for score 100', () => {
        const wrapper = mount(ScoreRing, {
            props: { score: 100, size: 'md' },
        })
        const circles = wrapper.findAll('circle')
        const foregroundCircle = circles[1]
        // score=100 → offset = 0 (full circle)
        expect(Number(foregroundCircle.attributes('stroke-dashoffset'))).toBeCloseTo(0, 1)
    })
})
