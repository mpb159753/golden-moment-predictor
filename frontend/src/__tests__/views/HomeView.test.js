import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HomeView from '@/views/HomeView.vue'

// --- Mock stores ---
const mockInit = vi.fn()
const mockSelectViewpoint = vi.fn()
const mockClearSelection = vi.fn()
const mockSelectDate = vi.fn()
const mockEnsureForecast = vi.fn()

const mockVpState = {
    index: [
        { id: 'niubei', name: '牛背山', location: { lon: 102.5, lat: 29.8 }, capabilities: ['golden_mountain'] },
        { id: 'zheduo', name: '折多山', location: { lon: 101.8, lat: 30.1 }, capabilities: ['cloud_sea'] },
    ],
    selectedId: null,
    selectedDate: '2026-02-12',
    forecasts: {},
    currentViewpoint: null,
    currentForecast: null,
    currentDay: null,
    currentTimeline: null,
    loading: false,
    error: null,
    init: mockInit,
    selectViewpoint: mockSelectViewpoint,
    clearSelection: mockClearSelection,
    selectDate: mockSelectDate,
    ensureForecast: mockEnsureForecast,
}

vi.mock('@/stores/viewpoints', () => ({
    useViewpointStore: () => mockVpState,
}))

const mockRouteInit = vi.fn()
const mockRouteState = {
    index: [],
    init: mockRouteInit,
}

vi.mock('@/stores/routes', () => ({
    useRouteStore: () => mockRouteState,
}))

vi.mock('@/stores/app', () => ({
    useAppStore: () => ({ isMobile: true }),
}))

// Stub all child components
const globalConfig = {
    stubs: {
        AMapContainer: {
            name: 'AMapContainer',
            template: '<div class="amap-container-stub"><slot /></div>',
            props: ['height', 'mapOptions'],
            emits: ['ready'],
        },
        ViewpointMarker: {
            name: 'ViewpointMarker',
            template: '<div class="viewpoint-marker-stub" />',
            props: ['viewpoint', 'score', 'bestEvent', 'selected', 'zoom'],
            emits: ['click'],
        },
        RouteLine: {
            name: 'RouteLine',
            template: '<div class="route-line-stub" />',
            props: ['stops'],
        },
        MapTopBar: {
            name: 'MapTopBar',
            template: '<div class="map-top-bar-stub" />',
            props: ['viewpoints', 'selectedDate', 'availableDates', 'activeFilters'],
            emits: ['search', 'filter', 'date-change', 'toggle-route'],
        },
        BottomSheet: {
            name: 'BottomSheet',
            template: `<div class="bottom-sheet-stub">
                <slot name="collapsed" />
                <slot name="half" />
                <slot name="full" />
            </div>`,
            props: ['state'],
            emits: ['state-change'],
        },
        BestRecommendList: {
            name: 'BestRecommendList',
            template: '<div class="best-recommend-stub" />',
            props: ['recommendations'],
            emits: ['select'],
        },
        DaySummary: {
            template: '<div class="day-summary-stub" />',
            props: ['day', 'clickable'],
            emits: ['click'],
        },
        EventList: {
            template: '<div class="event-list-stub" />',
            props: ['events', 'showBreakdown'],
        },
        WeekTrend: {
            template: '<div class="week-trend-stub" />',
            props: ['daily'],
            emits: ['select'],
        },
        HourlyTimeline: {
            template: '<div class="hourly-timeline-stub" />',
            props: ['hourly'],
        },
        ScreenshotBtn: {
            template: '<div class="screenshot-btn-stub" />',
            props: ['target', 'filename', 'beforeCapture', 'afterCapture', 'label'],
        },
        RoutePanel: {
            name: 'RoutePanel',
            template: '<div class="route-panel-stub" />',
            props: ['route', 'selectedStopId'],
            emits: ['close', 'select-stop'],
        },
        TimePeriodBar: {
            name: 'TimePeriodBar',
            template: '<div class="time-period-bar-stub" />',
            props: ['periods'],
        },
        MiniTrend: {
            name: 'MiniTrend',
            template: '<div class="mini-trend-stub" />',
            props: ['daily', 'selectedDate'],
            emits: ['select'],
        },
    },
}

describe('HomeView', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        mockInit.mockClear()
        mockSelectViewpoint.mockClear()
        mockClearSelection.mockClear()
        mockSelectDate.mockClear()
        mockEnsureForecast.mockClear()
        mockRouteInit.mockClear()

        // Reset mutable state
        mockVpState.index = [
            { id: 'niubei', name: '牛背山', location: { lon: 102.5, lat: 29.8 }, capabilities: ['golden_mountain'] },
            { id: 'zheduo', name: '折多山', location: { lon: 101.8, lat: 30.1 }, capabilities: ['cloud_sea'] },
        ]
        mockVpState.selectedId = null
        mockVpState.selectedDate = '2026-02-12'
        mockVpState.forecasts = {}
        mockVpState.currentViewpoint = null
        mockVpState.currentForecast = null
        mockVpState.currentDay = null
        mockVpState.currentTimeline = null
        mockVpState.loading = false
        mockVpState.error = null
        mockRouteState.index = []
    })

    function mountHome() {
        const wrapper = mount(HomeView, {
            global: {
                ...globalConfig,
                mocks: {
                    $router: { push: vi.fn() },
                },
            },
        })
        return wrapper
    }

    async function mountHomeWithMap() {
        const wrapper = mountHome()
        // Simulate map ready to enable markers/routes rendering
        const mapContainer = wrapper.findComponent({ name: 'AMapContainer' })
        const fakeMap = {
            on: vi.fn(),
            setZoomAndCenter: vi.fn(),
            getZoom: vi.fn(() => 8),
        }
        await mapContainer.vm.$emit('ready', fakeMap)
        await wrapper.vm.$nextTick()
        return wrapper
    }

    // --- 布局结构 ---
    it('renders the home-view wrapper as full viewport', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.home-view').exists()).toBe(true)
    })

    it('renders AMapContainer', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.amap-container-stub').exists()).toBe(true)
    })

    it('renders MapTopBar', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.map-top-bar-stub').exists()).toBe(true)
    })

    it('renders BottomSheet', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.bottom-sheet-stub').exists()).toBe(true)
    })

    it('renders ScreenshotBtn', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.screenshot-btn-stub').exists()).toBe(true)
    })

    // --- 初始化 ---
    it('calls vpStore.init and routeStore.init on mount', async () => {
        mountHome()
        await flushPromises()
        expect(mockInit).toHaveBeenCalled()
        expect(mockRouteInit).toHaveBeenCalled()
    })

    // --- 筛选 ---
    it('renders markers for all viewpoints when map is ready', async () => {
        const wrapper = await mountHomeWithMap()
        const markers = wrapper.findAll('.viewpoint-marker-stub')
        expect(markers.length).toBe(2)
    })

    it('filters viewpoints by activeFilters', async () => {
        const wrapper = await mountHomeWithMap()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('filter', ['golden_mountain'])
        await wrapper.vm.$nextTick()
        const markers = wrapper.findAll('.viewpoint-marker-stub')
        expect(markers.length).toBe(1)
    })

    // --- 搜索 ---
    it('handles search event by selecting viewpoint', async () => {
        const wrapper = mountHome()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('search', 'niubei')
        expect(mockSelectViewpoint).toHaveBeenCalledWith('niubei')
    })

    // --- 日期切换 ---
    it('handles date-change event', async () => {
        const wrapper = mountHome()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('date-change', '2026-02-13')
        expect(mockSelectDate).toHaveBeenCalledWith('2026-02-13')
    })

    // --- BottomSheet 内容 ---
    it('renders BestRecommendList in collapsed slot', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.best-recommend-stub').exists()).toBe(true)
    })

    it('shows half content when viewpoint is selected', async () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            summary: '日照金山',
            best_event: { event_type: 'golden_mountain', score: 90 },
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.half-content').exists()).toBe(true)
        expect(wrapper.find('.half-title-row').exists()).toBe(true)
    })

    it('shows full content with WeekTrend when forecast exists', async () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            summary: '日照金山',
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        mockVpState.currentForecast = {
            daily: [{ date: '2026-02-12' }, { date: '2026-02-13' }],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.full-content').exists()).toBe(true)
        expect(wrapper.find('.week-trend-stub').exists()).toBe(true)
    })

    it('renders full report button in full content', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = { date: '2026-02-12', events: [] }
        mockVpState.currentForecast = { daily: [] }
        const wrapper = mountHome()
        expect(wrapper.find('.full-report-btn').exists()).toBe(true)
    })

    // --- 线路模式 ---
    it('does not render RouteLine when routeMode is off', async () => {
        mockRouteState.index = [{ id: 'route1', stops: [] }]
        const wrapper = await mountHomeWithMap()
        expect(wrapper.find('.route-line-stub').exists()).toBe(false)
    })

    it('renders RouteLine when routeMode is enabled', async () => {
        mockRouteState.index = [{ id: 'route1', stops: [] }]
        const wrapper = await mountHomeWithMap()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('toggle-route', true)
        await wrapper.vm.$nextTick()
        expect(wrapper.find('.route-line-stub').exists()).toBe(true)
    })

    // --- 线路模式集成 ---
    it('auto-expands BottomSheet to half when route mode enabled', async () => {
        mockRouteState.index = [{ id: 'route1', name: '理小路', stops: [] }]
        const wrapper = await mountHomeWithMap()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('toggle-route', true)
        await wrapper.vm.$nextTick()
        const sheet = wrapper.findComponent({ name: 'BottomSheet' })
        expect(sheet.props('state')).toBe('half')
    })

    it('renders RoutePanel in half slot when route mode is on', async () => {
        mockRouteState.index = [{ id: 'route1', name: '理小路', stops: [] }]
        const wrapper = await mountHomeWithMap()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('toggle-route', true)
        await wrapper.vm.$nextTick()
        expect(wrapper.find('.route-panel-stub').exists()).toBe(true)
    })

    it('collapses BottomSheet when route mode disabled', async () => {
        mockRouteState.index = [{ id: 'route1', name: '理小路', stops: [] }]
        const wrapper = await mountHomeWithMap()
        const topbar = wrapper.findComponent({ name: 'MapTopBar' })
        await topbar.vm.$emit('toggle-route', true)
        await wrapper.vm.$nextTick()
        await topbar.vm.$emit('toggle-route', false)
        await wrapper.vm.$nextTick()
        const sheet = wrapper.findComponent({ name: 'BottomSheet' })
        expect(sheet.props('state')).toBe('collapsed')
    })

    // --- 水印 ---
    it('renders map watermark', () => {
        const wrapper = mountHome()
        expect(wrapper.find('.map-watermark').exists()).toBe(true)
        expect(wrapper.find('.map-watermark').text()).toContain('GMP')
    })

    // --- bestEvent prop 传递 ---
    it('passes bestEvent to ViewpointMarker when forecast has best_event', async () => {
        mockVpState.forecasts = {
            niubei: {
                daily: [{
                    date: '2026-02-12',
                    best_event: { event_type: 'cloud_sea', score: 92 },
                    events: [{ event_type: 'cloud_sea', score: 92 }],
                }],
            },
        }
        const wrapper = await mountHomeWithMap()
        const markers = wrapper.findAllComponents({ name: 'ViewpointMarker' })
        const niubeiMarker = markers.find(m => m.props('viewpoint').id === 'niubei')
        expect(niubeiMarker.props('bestEvent')).toBe('cloud_sea')
    })

    it('passes null bestEvent when forecast has no best_event', async () => {
        mockVpState.forecasts = {
            niubei: {
                daily: [{
                    date: '2026-02-12',
                    events: [{ event_type: 'clear_sky', score: 50 }],
                }],
            },
        }
        const wrapper = await mountHomeWithMap()
        const markers = wrapper.findAllComponents({ name: 'ViewpointMarker' })
        const niubeiMarker = markers.find(m => m.props('viewpoint').id === 'niubei')
        expect(niubeiMarker.props('bestEvent')).toBeNull()
    })

    // --- BottomSheet 半展态重构 ---
    it('half-state shows viewpoint name and best score in title row', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'cloud_sea', score: 92 },
            events: [{ event_type: 'cloud_sea', score: 92 }],
        }
        const wrapper = mountHome()
        const halfContent = wrapper.find('.half-content')
        expect(halfContent.exists()).toBe(true)
        expect(halfContent.text()).toContain('牛背山')
        expect(halfContent.text()).toContain('92')
    })

    it('half-state shows reject reasons for zero-score events', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'clear_sky', score: 75 },
            events: [
                { event_type: 'clear_sky', score: 75 },
                { event_type: 'stargazing', score: 0, reject_reason: '月相不佳' },
                { event_type: 'sunrise_golden_mountain', score: 0, reject_reason: '山顶云量过高' },
            ],
        }
        const wrapper = mountHome()
        const halfContent = wrapper.find('.half-content')
        expect(halfContent.text()).toContain('月相不佳')
        expect(halfContent.text()).toContain('山顶云量过高')
    })

    it('half-state shows TimePeriodBar when timeline data exists', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'clear_sky', score: 75 },
            events: [],
        }
        mockVpState.currentTimeline = {
            hourly: [
                { hour: 6, events_active: [{ event_type: 'clear_sky', score: 70, status: 'Active' }] },
                { hour: 10, events_active: [{ event_type: 'clear_sky', score: 80, status: 'Active' }] },
            ],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.time-period-bar-stub').exists()).toBe(true)
    })

    it('half-state shows MiniTrend when forecast daily data exists', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'clear_sky', score: 75 },
            events: [],
        }
        mockVpState.currentForecast = {
            daily: [
                { date: '2026-02-12', best_event: { event_type: 'clear_sky', score: 75 } },
                { date: '2026-02-13', best_event: { event_type: 'cloud_sea', score: 90 } },
            ],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.mini-trend-stub').exists()).toBe(true)
    })

    it('MiniTrend select event changes selectedDate', async () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = { date: '2026-02-12', events: [], best_event: { score: 75, event_type: 'clear_sky' } }
        mockVpState.currentForecast = {
            daily: [
                { date: '2026-02-12', best_event: { event_type: 'clear_sky', score: 75 } },
                { date: '2026-02-13', best_event: { event_type: 'cloud_sea', score: 90 } },
            ],
        }
        const wrapper = mountHome()
        const miniTrend = wrapper.findComponent({ name: 'MiniTrend' })
        await miniTrend.vm.$emit('select', '2026-02-13')
        expect(mockSelectDate).toHaveBeenCalledWith('2026-02-13')
    })

    // --- P1-1: 关闭按钮 ---
    it('half-state renders a close button (.sheet-close-btn)', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'golden_mountain', score: 90 },
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.half-content .sheet-close-btn').exists()).toBe(true)
    })

    it('full-state renders a close button (.sheet-close-btn--full)', () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            summary: '日照金山',
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        mockVpState.currentForecast = {
            daily: [{ date: '2026-02-12', events: [] }],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.full-content .sheet-close-btn--full').exists()).toBe(true)
    })

    it('clicking close button sets sheetState to collapsed and clears selection', async () => {
        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'golden_mountain', score: 90 },
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        const wrapper = mountHome()
        const closeBtn = wrapper.find('.half-content .sheet-close-btn')
        await closeBtn.trigger('click')
        const sheet = wrapper.findComponent({ name: 'BottomSheet' })
        expect(sheet.props('state')).toBe('collapsed')
        expect(mockClearSelection).toHaveBeenCalled()
    })

    // --- P1-2: 设备自适应文案 ---
    it('shows PC hint text on non-touch devices', () => {
        // 模拟非触屏设备：删除 ontouchstart（in 检查的是属性是否存在）
        delete window.ontouchstart
        Object.defineProperty(navigator, 'maxTouchPoints', { value: 0, configurable: true })

        mockVpState.currentViewpoint = { id: 'niubei', name: '牛背山' }
        mockVpState.currentDay = {
            date: '2026-02-12',
            best_event: { event_type: 'golden_mountain', score: 90 },
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        const wrapper = mountHome()
        const hint = wrapper.find('.half-expand-hint')
        expect(hint.text()).toContain('点击查看完整报告')
        expect(hint.text()).not.toContain('上拉')
    })
})

