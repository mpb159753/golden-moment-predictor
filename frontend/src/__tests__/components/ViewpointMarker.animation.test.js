import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock gsap — vi.hoisted ensures the variable is available before vi.mock is hoisted
const { mockFromTo } = vi.hoisted(() => ({
    mockFromTo: vi.fn(),
}))
vi.mock('gsap', () => ({
    default: {
        fromTo: mockFromTo,
    },
}))

import ViewpointMarker from '@/components/map/ViewpointMarker.vue'

// Mock AMap SDK
function createMockAMap() {
    const markerInstances = []
    function MockMarker(opts) {
        this.options = opts
        this.content = opts.content
        this.position = opts.position
        this.setContent = vi.fn((c) => { this.content = c })
        this.on = vi.fn()
        // Simulate getContentElement returning a DOM element
        this.getContentElement = vi.fn(() => {
            const el = document.createElement('div')
            el.innerHTML = this.content
            return el
        })
        markerInstances.push(this)
    }
    function MockPixel(x, y) { this.x = x; this.y = y }

    return {
        AMap: { Marker: MockMarker, Pixel: MockPixel },
        markerInstances,
    }
}

function createMockMap() {
    return {
        add: vi.fn(),
        remove: vi.fn(),
    }
}

const baseViewpoint = {
    id: 'niubei',
    name: '牛背山',
    location: { lon: 102.5, lat: 29.8 },
}

describe('ViewpointMarker - Enter Animation', () => {
    let mockAMap, markerInstances, mockMap

    beforeEach(() => {
        const mock = createMockAMap()
        mockAMap = mock.AMap
        markerInstances = mock.markerInstances
        markerInstances.length = 0
        mockMap = createMockMap()
        window.AMap = mockAMap
        mockFromTo.mockClear()
    })

    afterEach(() => {
        delete window.AMap
    })

    function mountMarker(props = {}) {
        return mount(ViewpointMarker, {
            props: {
                viewpoint: baseViewpoint,
                score: 75,
                selected: false,
                map: mockMap,
                ...props,
            },
            global: {
                provide: {
                    AMapSDK: mockAMap,
                },
            },
        })
    }

    it('calls gsap.fromTo with spring animation when marker is created', () => {
        mountMarker()
        expect(mockFromTo).toHaveBeenCalledTimes(1)
        const [target, fromVars, toVars] = mockFromTo.mock.calls[0]
        // Check from vars
        expect(fromVars).toMatchObject({
            y: 30,
            scale: 0,
            opacity: 0,
        })
        // Check to vars
        expect(toVars).toMatchObject({
            y: 0,
            scale: 1,
            opacity: 1,
            duration: 0.6,
            ease: 'back.out(1.7)',
        })
    })

    it('applies stagger delay based on enterDelay prop', () => {
        mountMarker({ enterDelay: 0.24 }) // 3rd marker: 0.08 * 3 = 0.24
        expect(mockFromTo).toHaveBeenCalledTimes(1)
        const [, , toVars] = mockFromTo.mock.calls[0]
        expect(toVars.delay).toBe(0.24)
    })

    it('uses zero delay when enterDelay is not provided', () => {
        mountMarker()
        expect(mockFromTo).toHaveBeenCalledTimes(1)
        const [, , toVars] = mockFromTo.mock.calls[0]
        expect(toVars.delay).toBe(0)
    })

    it('animates the content element returned by marker.getContentElement()', () => {
        mountMarker()
        expect(mockFromTo).toHaveBeenCalledTimes(1)
        const [target] = mockFromTo.mock.calls[0]
        // Target should be a DOM element (from getContentElement)
        expect(target).toBeInstanceOf(HTMLElement)
    })

    it('includes pulse-glow animation in selected marker content', () => {
        mountMarker({ selected: true, score: 75 })
        const content = markerInstances[0].content
        expect(content).toContain('pulse-glow')
    })
})
