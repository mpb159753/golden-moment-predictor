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
    index: [],
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
            props: ['viewpoint', 'score', 'selected', 'zoom', 'loading', 'enterDelay'],
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

describe('HomeView - Lazy Loading Optimization', () => {
    let requestIdleCallbackCalls

    beforeEach(() => {
        setActivePinia(createPinia())
        mockInit.mockClear()
        mockEnsureForecast.mockClear()
        mockRouteInit.mockClear()
        mockClearSelection.mockClear()
        mockSelectViewpoint.mockClear()
        mockSelectDate.mockClear()

        requestIdleCallbackCalls = []

        // Mock requestIdleCallback
        globalThis.requestIdleCallback = vi.fn((cb) => {
            requestIdleCallbackCalls.push(cb)
            return requestIdleCallbackCalls.length
        })

        // Set up 5 viewpoints (>3 to test lazy loading of remaining ones)
        mockVpState.index = [
            { id: 'vp1', name: 'VP1', location: { lon: 102.0, lat: 30.0 }, capabilities: [] },
            { id: 'vp2', name: 'VP2', location: { lon: 102.1, lat: 30.1 }, capabilities: [] },
            { id: 'vp3', name: 'VP3', location: { lon: 102.2, lat: 30.2 }, capabilities: [] },
            { id: 'vp4', name: 'VP4', location: { lon: 102.3, lat: 30.3 }, capabilities: [] },
            { id: 'vp5', name: 'VP5', location: { lon: 102.4, lat: 30.4 }, capabilities: [] },
        ]
        mockVpState.selectedId = null
        mockVpState.forecasts = {}
        mockVpState.currentViewpoint = null
        mockVpState.currentForecast = null
        mockVpState.currentDay = null
        mockVpState.currentTimeline = null
        mockRouteState.index = []
    })

    function mountHome() {
        return mount(HomeView, {
            global: {
                ...globalConfig,
                mocks: {
                    $router: { push: vi.fn() },
                },
            },
        })
    }

    it('loads first 3 forecasts eagerly on mount', async () => {
        mountHome()
        await flushPromises()

        // First 3 viewpoints should have ensureForecast called eagerly
        expect(mockEnsureForecast).toHaveBeenCalledWith('vp1')
        expect(mockEnsureForecast).toHaveBeenCalledWith('vp2')
        expect(mockEnsureForecast).toHaveBeenCalledWith('vp3')
    })

    it('schedules remaining forecasts via requestIdleCallback', async () => {
        mountHome()
        await flushPromises()

        // requestIdleCallback should have been called for remaining viewpoints
        expect(requestIdleCallbackCalls.length).toBeGreaterThanOrEqual(2) // vp4, vp5
    })

    it('loads remaining forecasts when idle callbacks fire', async () => {
        mountHome()
        await flushPromises()

        // Fire all idle callbacks
        for (const cb of requestIdleCallbackCalls) {
            cb()
        }
        await flushPromises()

        // vp4 and vp5 should now have ensureForecast called
        expect(mockEnsureForecast).toHaveBeenCalledWith('vp4')
        expect(mockEnsureForecast).toHaveBeenCalledWith('vp5')
    })

    it('passes loading prop to ViewpointMarker based on forecast availability', async () => {
        // vp1 has forecast loaded, others don't
        mockVpState.forecasts = { vp1: { daily: [] } }

        const wrapper = mountHome()
        await flushPromises()

        // Simulate map ready
        const mapContainer = wrapper.findComponent({ name: 'AMapContainer' })
        await mapContainer.vm.$emit('ready', {
            on: vi.fn(),
            setZoomAndCenter: vi.fn(),
            getZoom: vi.fn(() => 8),
        })
        await wrapper.vm.$nextTick()

        const markers = wrapper.findAllComponents({ name: 'ViewpointMarker' })
        // vp1 should have loading=false, others loading=true
        const vp1Marker = markers.find(m => m.props('viewpoint').id === 'vp1')
        const vp4Marker = markers.find(m => m.props('viewpoint').id === 'vp4')
        expect(vp1Marker.props('loading')).toBe(false)
        expect(vp4Marker.props('loading')).toBe(true)
    })
})
