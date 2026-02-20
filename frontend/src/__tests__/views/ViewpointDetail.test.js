import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ViewpointDetail from '@/views/ViewpointDetail.vue'

// --- Mock stores ---
const mockSelectViewpoint = vi.fn()
const mockSelectDate = vi.fn()
const mockStoreState = {
    loading: false,
    error: null,
    meta: { generated_at: '2026-02-18T05:00:00+08:00' },
    selectedDate: '2026-02-18',
    currentViewpoint: { id: 'niubei_gongga', name: '牛背山' },
    currentForecast: {
        viewpoint_id: 'niubei_gongga',
        daily: [
            {
                date: '2026-02-18',
                summary: '🌄☁️ 日照金山+壮观云海',
                best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                events: [
                    { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                    { event_type: 'cloud_sea', score: 85, status: 'Recommended' },
                ],
            },
            {
                date: '2026-02-19',
                summary: '⭐ 观星',
                best_event: { event_type: 'stargazing', score: 60, status: 'Possible' },
                events: [
                    { event_type: 'stargazing', score: 60, status: 'Possible' },
                ],
            },
        ],
    },
    currentTimeline: {
        viewpoint_id: 'niubei_gongga',
        date: '2026-02-18',
        hourly: [{ hour: 6, time: '06:00', events_active: [{ event_type: 'sunrise_golden_mountain', score: 90 }] }],
    },
    selectViewpoint: mockSelectViewpoint,
    selectDate: mockSelectDate,
}

vi.mock('@/stores/viewpoints', () => ({
    useViewpointStore: () => mockStoreState,
}))

vi.mock('@/composables/useTimePeriod', () => ({
    useTimePeriod: () => ({
        periods: [
            { id: 'sunrise', label: '日出', icon: '🌄', start: 5, end: 8 },
            { id: 'daytime', label: '白天', icon: '☀️', start: 8, end: 16 },
            { id: 'sunset', label: '日落', icon: '🌅', start: 16, end: 19 },
            { id: 'night', label: '夜晚', icon: '⭐', start: 19, end: 5 },
        ],
        getPeriodScores: (hourly) => [
            { id: 'sunrise', label: '日出', icon: '🌄', start: 5, end: 8, bestScore: 90, bestEvent: 'sunrise_golden_mountain', events: [] },
            { id: 'daytime', label: '白天', icon: '☀️', start: 8, end: 16, bestScore: 0, bestEvent: null, events: [] },
            { id: 'sunset', label: '日落', icon: '🌅', start: 16, end: 19, bestScore: 0, bestEvent: null, events: [] },
            { id: 'night', label: '夜晚', icon: '⭐', start: 19, end: 5, bestScore: 0, bestEvent: null, events: [] },
        ],
    }),
}))

// Stub all child components to isolate ViewpointDetail
const globalConfig = {
    stubs: {
        UpdateBanner: { template: '<div class="update-banner-stub" />', props: ['meta'] },
        TrendChart: {
            name: 'TrendChart',
            template: '<div class="trend-chart-stub" />',
            props: ['daily', 'selectedDate'],
            emits: ['select'],
        },
        DaySummary: { template: '<div class="day-summary-stub" />', props: ['day', 'clickable'] },
        EventList: { template: '<div class="event-list-stub" />', props: ['events', 'showBreakdown'] },
        TimePeriodBar: { template: '<div class="time-period-bar-stub" />', props: ['periods'] },
        HourlyWeatherTable: { template: '<div class="hourly-weather-table-stub" />', props: ['hourly'] },
        EventIcon: { template: '<span class="event-icon-stub" />', props: ['eventType', 'size'] },
        ScreenshotBtn: { template: '<div class="screenshot-btn-stub" />', props: ['target', 'filename'] },
        ShareCard: {
            template: '<div class="share-card-stub" />',
            props: ['visible', 'viewpoint', 'day'],
            emits: ['close'],
        },
    },
}

describe('ViewpointDetail', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        mockSelectViewpoint.mockClear()
        mockSelectDate.mockClear()
        // Reset mutable state
        mockStoreState.loading = false
        mockStoreState.error = null
        mockStoreState.currentViewpoint = { id: 'niubei_gongga', name: '牛背山' }
        mockStoreState.currentForecast = {
            viewpoint_id: 'niubei_gongga',
            daily: [
                {
                    date: '2026-02-18',
                    summary: '🌄☁️ 日照金山+壮观云海',
                    best_event: { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                    events: [
                        { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
                        { event_type: 'cloud_sea', score: 85, status: 'Recommended' },
                    ],
                },
                {
                    date: '2026-02-19',
                    summary: '⭐ 观星',
                    best_event: { event_type: 'stargazing', score: 60, status: 'Possible' },
                    events: [
                        { event_type: 'stargazing', score: 60, status: 'Possible' },
                    ],
                },
            ],
        }
        mockStoreState.currentTimeline = {
            viewpoint_id: 'niubei_gongga',
            date: '2026-02-18',
            hourly: [{ hour: 6, time: '06:00', events_active: [{ event_type: 'sunrise_golden_mountain', score: 90 }] }],
        }
    })

    function mountDetail(props = {}) {
        return mount(ViewpointDetail, {
            props: { id: 'niubei_gongga', ...props },
            global: {
                ...globalConfig,
                mocks: {
                    $router: { back: vi.fn() },
                },
            },
        })
    }

    // --- Header ---
    it('renders viewpoint name in header', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.detail-header h1').text()).toBe('牛背山')
    })

    it('renders back button that calls router.back', async () => {
        const wrapper = mountDetail()
        const backBtn = wrapper.find('.back-btn')
        expect(backBtn.exists()).toBe(true)
        await backBtn.trigger('click')
        expect(wrapper.vm.$router.back).toHaveBeenCalled()
    })

    // --- Loading state ---
    it('shows loading spinner when loading', () => {
        mockStoreState.loading = true
        const wrapper = mountDetail()
        expect(wrapper.find('.loading-spinner').exists()).toBe(true)
    })

    // --- Error state ---
    it('shows error message when error', () => {
        mockStoreState.error = '网络错误'
        const wrapper = mountDetail()
        expect(wrapper.find('.error-message').text()).toContain('网络错误')
    })

    // --- Main content ---
    it('renders UpdateBanner with meta', () => {
        const wrapper = mountDetail()
        const banner = wrapper.find('.update-banner-stub')
        expect(banner.exists()).toBe(true)
    })

    // --- MG5B: TrendChart replaces DatePicker ---
    it('renders TrendChart instead of DatePicker', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.trend-chart-stub').exists()).toBe(true)
        expect(wrapper.find('.date-picker-stub').exists()).toBe(false)
    })

    it('renders DaySummary for current day', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.day-summary-stub').exists()).toBe(true)
    })

    it('renders EventList with current day events', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.event-list-stub').exists()).toBe(true)
    })

    // --- MG5B: TimePeriodBar when timeline exists ---
    it('renders TimePeriodBar when timeline data exists', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.time-period-bar-stub').exists()).toBe(true)
    })

    it('does not render TimePeriodBar when no timeline data', () => {
        mockStoreState.currentTimeline = null
        const wrapper = mountDetail()
        expect(wrapper.find('.time-period-bar-stub').exists()).toBe(false)
    })

    // --- MG5B: HourlyWeatherTable replaces HourlyTimeline ---
    it('renders HourlyWeatherTable when timeline data exists', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.hourly-weather-table-stub').exists()).toBe(true)
        expect(wrapper.find('.hourly-timeline-stub').exists()).toBe(false)
    })

    // --- MG5B: Reject reasons for zero-score events ---
    it('shows reject reasons for zero-score events', () => {
        mockStoreState.currentForecast.daily[0].events = [
            { event_type: 'sunrise_golden_mountain', score: 90, status: 'Recommended' },
            { event_type: 'frost', score: 0, reject_reason: '温度过高，无法形成霜冻' },
            { event_type: 'clear_sky', score: 0, reject_reason: '云量过高' },
        ]
        const wrapper = mountDetail()
        const reasons = wrapper.findAll('.reject-reason')
        expect(reasons.length).toBe(2)
        expect(reasons[0].text()).toContain('温度过高，无法形成霜冻')
        expect(reasons[1].text()).toContain('云量过高')
    })

    it('translates English reject reason keys to Chinese', () => {
        mockStoreState.currentForecast.daily[0].events = [
            { event_type: 'sunrise_golden_mountain', score: 0, reject_reason: 'cloud=74%' },
            { event_type: 'frost', score: 0, reject_reason: 'wind=85%' },
        ]
        const wrapper = mountDetail()
        const reasons = wrapper.findAll('.reject-reason')
        expect(reasons.length).toBe(2)
        expect(reasons[0].text()).toContain('云量=74%')
        expect(reasons[1].text()).toContain('风速=85%')
    })

    it('does not show reject reasons when no zero-score events', () => {
        const wrapper = mountDetail()
        expect(wrapper.findAll('.reject-reason').length).toBe(0)
    })

    // --- MG5B: TrendChart select triggers date switch ---
    it('clicking TrendChart emits select to switch date', async () => {
        const wrapper = mountDetail()
        const trendChart = wrapper.findComponent({ name: 'TrendChart' })
        expect(trendChart.exists()).toBe(true)
        await trendChart.vm.$emit('select', '2026-02-19')
        expect(mockSelectDate).toHaveBeenCalledWith('2026-02-19')
    })

    // --- No WeekTrend or HourlyTimeline ---
    it('does not render WeekTrend', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.week-trend-stub').exists()).toBe(false)
    })

    // --- Actions ---
    it('renders icon screenshot button in header', () => {
        const wrapper = mountDetail()
        const headerBtn = wrapper.find('.header-screenshot-btn')
        expect(headerBtn.exists()).toBe(true)
        expect(headerBtn.text()).toContain('📷')
    })

    it('renders ScreenshotBtn in actions area', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.detail-actions .screenshot-btn-stub').exists()).toBe(true)
    })

    it('renders share button that opens ShareCard', async () => {
        const wrapper = mountDetail()
        const shareBtn = wrapper.find('.share-btn')
        expect(shareBtn.exists()).toBe(true)
        await shareBtn.trigger('click')
        expect(wrapper.find('.share-card-stub').exists()).toBe(true)
    })

    // --- Init behavior ---
    it('calls selectViewpoint on mount', async () => {
        mountDetail()
        await flushPromises()
        expect(mockSelectViewpoint).toHaveBeenCalledWith('niubei_gongga')
    })

    it('calls selectDate on mount when date prop is provided', async () => {
        mountDetail({ date: '2026-02-19' })
        await flushPromises()
        expect(mockSelectDate).toHaveBeenCalledWith('2026-02-19')
    })

    it('does not call selectDate on mount when no date prop', async () => {
        mountDetail()
        await flushPromises()
        expect(mockSelectDate).not.toHaveBeenCalled()
    })
})
