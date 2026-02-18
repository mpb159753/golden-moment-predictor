import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
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

describe('ViewpointMarker', () => {
    let mockAMap, markerInstances, mockMap

    beforeEach(() => {
        const mock = createMockAMap()
        mockAMap = mock.AMap
        markerInstances = mock.markerInstances
        markerInstances.length = 0
        mockMap = createMockMap()
        // 注入 AMap SDK 到 window
        window.AMap = mockAMap
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

    // --- 基本渲染 ---
    it('creates a marker on the map when mounted', () => {
        mountMarker()
        expect(mockMap.add).toHaveBeenCalled()
        expect(markerInstances.length).toBe(1)
    })

    it('positions marker at viewpoint coordinates', () => {
        mountMarker()
        expect(markerInstances[0].position).toEqual([102.5, 29.8])
    })

    it('renders score in default marker content', () => {
        mountMarker({ score: 80 })
        const content = markerInstances[0].content
        expect(content).toContain('80')
    })

    // --- 三种状态 ---
    it('renders default state: circle with score number', () => {
        mountMarker({ score: 75, selected: false, zoom: 10 })
        const content = markerInstances[0].content
        expect(content).toContain('75')
        // 默认标记不应包含观景台名称
        expect(content).not.toContain('牛背山')
    })

    it('renders selected state: expanded with viewpoint name', () => {
        mountMarker({ score: 90, selected: true, zoom: 10 })
        const content = markerInstances[0].content
        // 选中态应包含名称
        expect(content).toContain('牛背山')
        expect(content).toContain('90')
        // 选中态应有 scale
        expect(content).toContain('scale(1.2)')
    })

    it('renders mini state when zoom < 9', () => {
        mountMarker({ score: 85, selected: false, zoom: 7 })
        const content = markerInstances[0].content
        // 缩略态应该只有简单圆点，不包含分数
        expect(content).toContain('marker-dot')
        // 不应包含分数文字
        expect(content).not.toContain('85')
    })

    it('selected state overrides mini state even at low zoom', () => {
        mountMarker({ score: 85, selected: true, zoom: 7 })
        const content = markerInstances[0].content
        // 即使 zoom 低，选中态也应该显示名称
        expect(content).toContain('牛背山')
    })

    // --- 样式 ---
    it('applies bounce animation when selected', () => {
        mountMarker({ selected: true })
        const content = markerInstances[0].content
        expect(content).toContain('marker-bounce')
    })

    it('applies pulse animation for score >= 95', () => {
        mountMarker({ score: 98 })
        const content = markerInstances[0].content
        expect(content).toContain('marker-pulse')
    })

    it('does not apply pulse animation for score < 95', () => {
        mountMarker({ score: 80 })
        const content = markerInstances[0].content
        expect(content).not.toContain('marker-pulse')
    })

    // --- 事件 ---
    it('emits click when marker is clicked', () => {
        const wrapper = mountMarker()
        expect(markerInstances[0].on).toHaveBeenCalledWith('click', expect.any(Function))
        // Simulate click
        const clickHandler = markerInstances[0].on.mock.calls[0][1]
        clickHandler()
        expect(wrapper.emitted('click')).toBeTruthy()
        expect(wrapper.emitted('click')[0]).toEqual([baseViewpoint])
    })

    // --- 更新 ---
    it('updates marker content when score changes', async () => {
        const wrapper = mountMarker({ score: 60 })
        await wrapper.setProps({ score: 95 })
        expect(markerInstances[0].setContent).toHaveBeenCalled()
        const newContent = markerInstances[0].setContent.mock.calls[0][0]
        expect(newContent).toContain('95')
    })

    it('updates marker content when selected changes', async () => {
        const wrapper = mountMarker({ selected: false })
        await wrapper.setProps({ selected: true })
        expect(markerInstances[0].setContent).toHaveBeenCalled()
    })

    // --- 清理 ---
    it('removes marker from map on unmount', () => {
        const wrapper = mountMarker()
        wrapper.unmount()
        expect(mockMap.remove).toHaveBeenCalled()
    })
})
