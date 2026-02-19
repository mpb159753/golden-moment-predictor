import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock SVG imports as simple Vue components (vite-svg-loader transforms them to components)
// Note: vi.mock is hoisted, so we must inline the stub object
vi.mock('@/assets/icons/sunrise-golden-mountain.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/sunset-golden-mountain.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/cloud-sea.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/stargazing.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/frost.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/snow-tree.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/ice-icicle.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/clear-sky.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))

import EventIcon from '@/components/event/EventIcon.vue'

describe('EventIcon', () => {
    it('renders with correct size style', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'cloud_sea', size: 32 },
        })
        const span = wrapper.find('.event-icon')
        expect(span.attributes('style')).toContain('width: 32px')
        expect(span.attributes('style')).toContain('height: 32px')
    })

    it('uses default size of 24', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'cloud_sea' },
        })
        const span = wrapper.find('.event-icon')
        expect(span.attributes('style')).toContain('width: 24px')
        expect(span.attributes('style')).toContain('height: 24px')
    })

    it('applies theme color when colored is true (default)', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'cloud_sea' },
        })
        const span = wrapper.find('.event-icon')
        // cloud_sea color is #87CEEB
        expect(span.attributes('style')).toContain('color: #87CEEB')
    })

    it('uses currentColor when colored is false', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'cloud_sea', colored: false },
        })
        const span = wrapper.find('.event-icon')
        // DOM normalizes currentColor to lowercase
        expect(span.attributes('style').toLowerCase()).toContain('color: currentcolor')
    })

    it('sets title to Chinese name of event type', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'sunrise_golden_mountain' },
        })
        const span = wrapper.find('.event-icon')
        expect(span.attributes('title')).toBe('日出金山')
    })

    it('uses correct color for each event type', () => {
        const colorMap = {
            sunrise_golden_mountain: '#FF8C00',
            sunset_golden_mountain: '#FF4500',
            cloud_sea: '#87CEEB',
            stargazing: '#4A0E8F',
            frost: '#B0E0E6',
            snow_tree: '#E0E8EF',
            ice_icicle: '#ADD8E6',
            clear_sky: '#FFB300',
        }
        for (const [eventType, expectedColor] of Object.entries(colorMap)) {
            const wrapper = mount(EventIcon, {
                props: { eventType },
            })
            expect(wrapper.find('.event-icon').attributes('style')).toContain(`color: ${expectedColor}`)
        }
    })

    it('renders an SVG icon component for known event type', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'cloud_sea' },
        })
        const svg = wrapper.find('svg[data-testid="svg-icon"]')
        expect(svg.exists()).toBe(true)
    })

    it('falls back gracefully for unknown event type', () => {
        const wrapper = mount(EventIcon, {
            props: { eventType: 'unknown_type' },
        })
        const span = wrapper.find('.event-icon')
        // fallback color
        expect(span.attributes('style')).toContain('color: #9CA3AF')
        // title falls back to raw event type
        expect(span.attributes('title')).toBe('unknown_type')
        // no SVG rendered
        const svg = wrapper.find('svg')
        expect(svg.exists()).toBe(false)
    })
})
