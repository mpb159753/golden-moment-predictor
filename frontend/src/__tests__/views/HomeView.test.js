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
            props: ['viewpoint', 'score', 'selected', 'zoom'],
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
            events: [{ event_type: 'golden_mountain', score: 90 }],
        }
        const wrapper = mountHome()
        expect(wrapper.find('.half-content').exists()).toBe(true)
        expect(wrapper.find('.day-summary-stub').exists()).toBe(true)
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
})

