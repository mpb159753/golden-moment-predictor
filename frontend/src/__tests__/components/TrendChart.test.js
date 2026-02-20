import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock ECharts — canvas-based, won't run in happy-dom
const mockSetOption = vi.fn()
const mockOn = vi.fn()
const mockResize = vi.fn()
const mockDispose = vi.fn()

vi.mock('echarts/core', () => ({
    default: {
        use: vi.fn(),
        init: vi.fn(() => ({
            setOption: mockSetOption,
            on: mockOn,
            resize: mockResize,
            dispose: mockDispose,
        })),
    },
    use: vi.fn(),
    init: vi.fn(() => ({
        setOption: mockSetOption,
        on: mockOn,
        resize: mockResize,
        dispose: mockDispose,
    })),
}))
vi.mock('echarts/charts', () => ({ BarChart: {} }))
vi.mock('echarts/components', () => ({
    TitleComponent: {},
    TooltipComponent: {},
    GridComponent: {},
    LegendComponent: {},
}))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

// Mock SVG icons used by EventIcon
vi.mock('@/assets/icons/sunrise-golden-mountain.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/sunset-golden-mountain.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/cloud-sea.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/stargazing.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/frost.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/snow-tree.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/ice-icicle.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))
vi.mock('@/assets/icons/clear-sky.svg', () => ({ default: { template: '<svg data-testid="svg-icon"></svg>' } }))

import TrendChart from '@/components/forecast/TrendChart.vue'

describe('TrendChart', () => {
    const mockDaily = [
        { date: '2026-02-19', best_event: { event_type: 'clear_sky', score: 30 } },
        { date: '2026-02-20', best_event: { event_type: 'clear_sky', score: 39 } },
        { date: '2026-02-21', best_event: { event_type: 'sunset_golden_mountain', score: 50 } },
        { date: '2026-02-22', best_event: { event_type: 'sunset_golden_mountain', score: 90 } },
        { date: '2026-02-23', best_event: { event_type: 'clear_sky', score: 55 } },
        { date: '2026-02-24', best_event: { event_type: 'clear_sky', score: 30 } },
        { date: '2026-02-25', best_event: { event_type: 'clear_sky', score: 5 } },
    ]

    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders .trend-chart container', () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        expect(wrapper.find('.trend-chart').exists()).toBe(true)
    })

    it('renders .trend-icons icon row', () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        expect(wrapper.find('.trend-icons').exists()).toBe(true)
    })

    it('renders correct number of icon cells', () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        const cells = wrapper.findAll('.trend-icon-cell')
        expect(cells).toHaveLength(7)
    })

    it('applies .selected class to the selected date icon cell', () => {
        const wrapper = mount(TrendChart, {
            props: { daily: mockDaily, selectedDate: '2026-02-22' },
        })
        const cells = wrapper.findAll('.trend-icon-cell')
        expect(cells[3].classes()).toContain('selected')
        expect(cells[0].classes()).not.toContain('selected')
    })

    it('initializes ECharts on mount', () => {
        mount(TrendChart, { props: { daily: mockDaily } })
        expect(mockSetOption).toHaveBeenCalled()
    })

    it('emits select when icon cell is clicked', async () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        const cells = wrapper.findAll('.trend-icon-cell')
        await cells[2].trigger('click')
        expect(wrapper.emitted('select')).toBeTruthy()
        expect(wrapper.emitted('select')[0]).toEqual(['2026-02-21'])
    })

    it('renders date text in each icon cell', () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        const cells = wrapper.findAll('.trend-icon-cell')
        // 2026-02-19 → 02/19
        expect(cells[0].find('.trend-icon-date').text()).toBe('02/19')
        // 2026-02-22 → 02/22
        expect(cells[3].find('.trend-icon-date').text()).toBe('02/22')
    })

    it('renders score in each icon cell', () => {
        const wrapper = mount(TrendChart, { props: { daily: mockDaily } })
        const cells = wrapper.findAll('.trend-icon-cell')
        expect(cells[0].find('.trend-icon-score').text()).toBe('30')
        expect(cells[3].find('.trend-icon-score').text()).toBe('90')
        expect(cells[6].find('.trend-icon-score').text()).toBe('5')
    })
})
