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
        hourly: [{ hour: 6, time: '06:00' }],
    },
    selectViewpoint: mockSelectViewpoint,
    selectDate: mockSelectDate,
}

vi.mock('@/stores/viewpoints', () => ({
    useViewpointStore: () => mockStoreState,
}))

// Stub all child components to isolate ViewpointDetail
const globalConfig = {
    stubs: {
        UpdateBanner: { template: '<div class="update-banner-stub" />', props: ['meta'] },
        DatePicker: {
            template: '<div class="date-picker-stub" />',
            props: ['modelValue', 'dates'],
            emits: ['update:modelValue'],
        },
        DaySummary: { template: '<div class="day-summary-stub" />', props: ['day', 'clickable'] },
        EventList: { template: '<div class="event-list-stub" />', props: ['events', 'showBreakdown'] },
        HourlyTimeline: { template: '<div class="hourly-timeline-stub" />', props: ['hourly'] },
        WeekTrend: {
            template: '<div class="week-trend-stub" />',
            props: ['daily'],
            emits: ['select'],
        },
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
            hourly: [{ hour: 6, time: '06:00' }],
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

    it('renders DatePicker with available dates', () => {
        const wrapper = mountDetail()
        const picker = wrapper.find('.date-picker-stub')
        expect(picker.exists()).toBe(true)
    })

    it('renders DaySummary for current day', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.day-summary-stub').exists()).toBe(true)
    })

    it('renders EventList with current day events', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.event-list-stub').exists()).toBe(true)
    })

    it('renders HourlyTimeline when timeline data exists', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.hourly-timeline-stub').exists()).toBe(true)
    })

    it('renders WeekTrend when forecast data exists', () => {
        const wrapper = mountDetail()
        expect(wrapper.find('.week-trend-stub').exists()).toBe(true)
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
        // After click, ShareCard should become visible
        const shareCard = wrapper.findComponent({ name: 'ShareCard' })
        // Since we're using stubs, check via the wrapper's showShareCard state
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
