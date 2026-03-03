import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RouteDetail from '@/views/RouteDetail.vue'

// --- Mock route store ---
const mockSelectRoute = vi.fn()
const mockRouteStoreState = {
    loading: false,
    error: null,
    currentRoute: { id: 'lixiao', name: '理小路' },
    currentForecast: {
        route_id: 'lixiao',
        route_name: '理小路',
        stops: [
            {
                viewpoint_id: 'zheduo',
                viewpoint_name: '折多山',
                order: 1,
                stay_note: '建议停留2小时观赏日出金山',
                location: { lon: 101.8, lat: 30.1 },
                forecast: {
                    viewpoint_id: 'zheduo',
                    daily: [
                        {
                            date: '2026-02-18',
                            summary: '🌄 日照金山',
                            best_event: { event_type: 'sunrise_golden_mountain', score: 75, status: 'Possible' },
                            events: [{ event_type: 'sunrise_golden_mountain', score: 75, status: 'Possible' }],
                        },
                        {
                            date: '2026-02-19',
                            summary: '☁️ 云海',
                            best_event: { event_type: 'cloud_sea', score: 60, status: 'Possible' },
                            events: [{ event_type: 'cloud_sea', score: 60, status: 'Possible' }],
                        },
                    ],
                },
            },
            {
                viewpoint_id: 'niubei',
                viewpoint_name: '牛背山',
                order: 2,
                stay_note: '建议停留3小时，云海+金山绝佳组合',
                location: { lon: 102.4, lat: 29.8 },
                forecast: {
                    viewpoint_id: 'niubei',
                    daily: [
                        {
                            date: '2026-02-18',
                            summary: '🌄☁️ 日照金山+壮观云海',
                            best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                            events: [
                                { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                                { event_type: 'cloud_sea', score: 90, status: 'Recommended' },
                            ],
                        },
                        {
                            date: '2026-02-19',
                            summary: '⭐ 观星',
                            best_event: { event_type: 'stargazing', score: 80, status: 'Recommended' },
                            events: [{ event_type: 'stargazing', score: 80, status: 'Recommended' }],
                        },
                    ],
                },
            },
        ],
    },
    selectRoute: mockSelectRoute,
}

vi.mock('@/stores/routes', () => ({
    useRouteStore: () => mockRouteStoreState,
}))

const mockRouter = { push: vi.fn(), back: vi.fn() }
vi.mock('vue-router', () => ({
    useRouter: () => mockRouter,
    RouterLink: { template: '<a><slot /></a>' },
}))

// Stub child components
const globalConfig = {
    stubs: {
        DaySummary: { template: '<div class="day-summary-stub" />', props: ['day', 'clickable'] },
        WeekTrend: { template: '<div class="week-trend-stub" />', props: ['daily'], emits: ['select'] },
        ScreenshotBtn: { template: '<div class="screenshot-btn-stub" />', props: ['target', 'filename'] },
        AMapContainer: { template: '<div class="amap-container-stub"><slot /></div>', props: ['height'], emits: ['ready'] },
        RouteLine: { template: '<div class="route-line-stub" />', props: ['stops', 'map'] },
        ViewpointMarker: { template: '<div class="viewpoint-marker-stub" />', props: ['viewpoint', 'score', 'map', 'selected'], emits: ['click'] },
        RouterLink: { template: '<a class="router-link-stub"><slot /></a>', props: ['to'] },
    },
}

describe('RouteDetail', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        mockSelectRoute.mockClear()
        mockRouter.push.mockClear()
        mockRouter.back.mockClear()
        // Reset mutable state
        mockRouteStoreState.loading = false
        mockRouteStoreState.error = null
        mockRouteStoreState.currentRoute = { id: 'lixiao', name: '理小路' }
        mockRouteStoreState.currentForecast = {
            route_id: 'lixiao',
            route_name: '理小路',
            stops: [
                {
                    viewpoint_id: 'zheduo',
                    viewpoint_name: '折多山',
                    order: 1,
                    stay_note: '建议停留2小时观赏日出金山',
                    location: { lon: 101.8, lat: 30.1 },
                    forecast: {
                        viewpoint_id: 'zheduo',
                        daily: [{
                            date: '2026-02-18',
                            summary: '🌄 日照金山',
                            best_event: { event_type: 'sunrise_golden_mountain', score: 75, status: 'Possible' },
                            events: [{ event_type: 'sunrise_golden_mountain', score: 75, status: 'Possible' }],
                        }, {
                            date: '2026-02-19',
                            summary: '☁️ 云海',
                            best_event: { event_type: 'cloud_sea', score: 60, status: 'Possible' },
                            events: [{ event_type: 'cloud_sea', score: 60, status: 'Possible' }],
                        }],
                    },
                },
                {
                    viewpoint_id: 'niubei',
                    viewpoint_name: '牛背山',
                    order: 2,
                    stay_note: '建议停留3小时，云海+金山绝佳组合',
                    location: { lon: 102.4, lat: 29.8 },
                    forecast: {
                        viewpoint_id: 'niubei',
                        daily: [{
                            date: '2026-02-18',
                            summary: '🌄☁️ 日照金山+壮观云海',
                            best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                            events: [
                                { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                                { event_type: 'cloud_sea', score: 90, status: 'Recommended' },
                            ],
                        }, {
                            date: '2026-02-19',
                            summary: '⭐ 观星',
                            best_event: { event_type: 'stargazing', score: 80, status: 'Recommended' },
                            events: [{ event_type: 'stargazing', score: 80, status: 'Recommended' }],
                        }],
                    },
                },
            ],
        }
    })

    function mountDetail(props = {}) {
        return mount(RouteDetail, {
            props: { id: 'lixiao', ...props },
            global: {
                ...globalConfig,
                mocks: {
                    $router: { back: vi.fn(), push: vi.fn() },
                },
            },
        })
    }

    // --- Header ---
    it('renders route name in header', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.detail-header h1').text()).toBe('理小路')
    })

    it('renders back button that calls router.back', async () => {
        const wrapper = mountDetail()
        const backBtn = wrapper.find('.back-btn')
        expect(backBtn.exists()).toBe(true)
        await backBtn.trigger('click')
        expect(mockRouter.back).toHaveBeenCalled()
    })

    // --- Loading state ---
    it('shows loading spinner when loading', () => {
        mockRouteStoreState.loading = true
        const wrapper = mountDetail()
        expect(wrapper.find('.loading-spinner').exists()).toBe(true)
    })

    // --- Error state ---
    it('shows error message when error occurs', () => {
        mockRouteStoreState.error = '网络错误'
        const wrapper = mountDetail()
        expect(wrapper.find('.error-message').text()).toContain('网络错误')
    })

    // --- Map section ---
    it('renders AMapContainer in route map section', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.amap-container-stub').exists()).toBe(true)
    })

    it('renders RouteLine inside map', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.route-line-stub').exists()).toBe(true)
    })

    it('renders ViewpointMarker for each stop with location', () => {
        const wrapper = mountDetail()
        const markers = wrapper.findAll('.viewpoint-marker-stub')
        expect(markers).toHaveLength(2)
    })

    // --- Stops rendering ---
    it('renders a stop section for each stop', () => {
        const wrapper = mountDetail()
        const stops = wrapper.findAll('.route-stop')
        expect(stops).toHaveLength(2)
    })

    it('displays stop name and order', () => {
        const wrapper = mountDetail()
        const stops = wrapper.findAll('.route-stop')
        expect(stops[0].find('.route-stop__title').text()).toContain('折多山')
        expect(stops[0].find('.route-stop__order').text()).toContain('1')
        expect(stops[1].find('.route-stop__title').text()).toContain('牛背山')
        expect(stops[1].find('.route-stop__order').text()).toContain('2')
    })

    it('displays stay note for each stop', () => {
        const wrapper = mountDetail()
        const stops = wrapper.findAll('.route-stop')
        expect(stops[0].find('.route-stop__note').text()).toContain('建议停留2小时')
        expect(stops[1].find('.route-stop__note').text()).toContain('建议停留3小时')
    })

    it('renders DaySummary for today for each stop', () => {
        const wrapper = mountDetail()
        const summaries = wrapper.findAll('.day-summary-stub')
        expect(summaries).toHaveLength(2)
    })

    // --- WeekTrend ---
    it('renders WeekTrend for each stop when multi-day data exists', () => {
        const wrapper = mountDetail()
        const trends = wrapper.findAll('.week-trend-stub')
        expect(trends).toHaveLength(2)
    })

    it('shows trend section title', () => {
        const wrapper = mountDetail()
        const section = wrapper.find('.route-trend-section')
        expect(section.exists()).toBe(true)
        expect(section.find('h2').text()).toBe('七日趋势对比')
    })

    // --- Link to viewpoint detail ---
    it('renders link to viewpoint detail for each stop', () => {
        const wrapper = mountDetail()
        const links = wrapper.findAll('.router-link-stub')
        expect(links.length).toBeGreaterThanOrEqual(2)
    })

    // --- Init behavior ---
    it('calls selectRoute on mount', async () => {
        mountDetail()
        await flushPromises()
        expect(mockSelectRoute).toHaveBeenCalledWith('lixiao')
    })

    // --- ScreenshotBtn ---
    it('renders ScreenshotBtn in header', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.screenshot-btn-stub').exists()).toBe(true)
    })
})
