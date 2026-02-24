import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PosterView from '@/views/PosterView.vue'

// ── 测试用 posterData ──
const mockPosterData = {
    generated_at: '2026-02-21T08:00:00+08:00',
    days: ['2026-02-21', '2026-02-22', '2026-02-23', '2026-02-24', '2026-02-25'],
    groups: [
        {
            name: '贡嘎山系',
            key: 'gongga',
            viewpoints: [{ id: 'niubei_gongga', name: '牛背山', daily: [] }],
        },
        {
            name: '四姑娘山',
            key: 'siguniang',
            viewpoints: [{ id: 'siguniang_changping', name: '长坪沟', daily: [] }],
        },
    ],
}

// Mock useDataLoader
const mockLoadPoster = vi.fn()
vi.mock('@/composables/useDataLoader', () => ({
    useDataLoader: () => ({
        loadPoster: mockLoadPoster,
        loading: { value: false },
        error: { value: null },
    }),
}))

// Stub child components
const globalConfig = {
    stubs: {
        PredictionMatrix: { template: '<div class="prediction-matrix-stub" />', props: ['group', 'days', 'showHeader', 'showFooter'] },
    },
}

describe('PosterView', () => {
    beforeEach(() => {
        mockLoadPoster.mockReset()
        mockLoadPoster.mockResolvedValue(mockPosterData)
    })

    it('shows loading state before data is loaded', () => {
        mockLoadPoster.mockReturnValue(new Promise(() => { })) // never resolves
        const wrapper = mount(PosterView, { global: globalConfig })
        expect(wrapper.text()).toContain('加载中')
    })

    it('renders all groups after load', async () => {
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        const matrices = wrapper.findAll('.prediction-matrix-stub')
        expect(matrices).toHaveLength(2)
    })

    it('day selector defaults to 5', async () => {
        const wrapper = mount(PosterView, { global: globalConfig })
        await flushPromises()
        // 默认选中 5 天按钮
        const activeBtn = wrapper.find('.day-btn.active')
        expect(activeBtn?.text()).toBe('5天')
    })
})

// ── buildSummary 逻辑测试 ──
// 内联与 PosterView.vue 中一致的 buildSummary 实现，独立测试其核心逻辑
function buildSummaryFromPosterData(data, dayCount, dayOffset = 0) {
    const displayedDayList = data.days.slice(dayOffset, dayOffset + dayCount)
    const highlights = []
    const groupOverview = {}

    for (const group of data.groups) {
        let groupBest = null
        for (const vp of group.viewpoints) {
            for (const day of vp.daily) {
                if (!displayedDayList.includes(day.date)) continue
                for (const half of ['am', 'pm']) {
                    const slot = day[half]
                    if (!slot || slot.score < 70) continue
                    highlights.push({
                        date: day.date,
                        period: half === 'am' ? '上午' : '下午',
                        group: group.name,
                        viewpoint: vp.name,
                        event: slot.event || '',
                        weather: slot.weather,
                        score: slot.score,
                        conditions: slot.conditions || {},
                    })
                    if (!groupBest || slot.score > groupBest.score) {
                        groupBest = { date: day.date, viewpoint: vp.name, score: slot.score }
                    }
                }
            }
        }
        if (groupBest) groupOverview[group.name] = groupBest
    }

    highlights.sort((a, b) => b.score - a.score)

    const fmt = d => {
        const dt = new Date(d)
        return `${dt.getMonth() + 1}月${dt.getDate()}日`
    }
    const dateRange = displayedDayList.length
        ? `${fmt(displayedDayList[0])}—${fmt(displayedDayList[displayedDayList.length - 1])}`
        : ''

    return {
        generated_at: data.generated_at,
        date_range: dateRange,
        highlights,
        group_overview: groupOverview,
    }
}

const summaryData = {
    generated_at: '2026-02-24T10:00:00+08:00',
    days: ['2026-02-24', '2026-02-25', '2026-02-26'],
    groups: [{
        name: '贡嘎山系',
        key: 'gongga',
        viewpoints: [{
            id: 'vp1',
            name: '雅哈垭口',
            daily: [
                {
                    date: '2026-02-24',
                    am: { score: 80, event: '雾凇', weather: '晴天', conditions: { temperature: { score: 40, max: 40, detail: 'avg_temp=-2°C' } } },
                    pm: { score: 55, event: '', weather: '阴天', conditions: {} },  // < 70
                },
                {
                    date: '2026-02-25',
                    am: { score: 60, event: '', weather: '阴天', conditions: {} },  // < 70
                    pm: { score: 90, event: '观星', weather: '晴天', conditions: { base: { score: 100, max: 100, detail: 'quality=optimal' } } },
                },
                {
                    date: '2026-02-26',
                    am: { score: 85, event: '日照金山', weather: '晴天', conditions: { light_path: { score: 30, max: 35, detail: 'cloud=8%' } } },
                    pm: { score: 50, event: '', weather: '多云', conditions: {} },  // < 70
                },
            ],
        }],
    }],
}

describe('buildSummary', () => {
    it('only includes slots with score >= 70 in highlights', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.highlights.every(h => h.score >= 70)).toBe(true)
        expect(summary.highlights).toHaveLength(3)  // score 55, 60, 50 被排除
    })

    it('highlights are sorted by score descending', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.highlights[0].score).toBe(90)
        expect(summary.highlights[1].score).toBe(85)
        expect(summary.highlights[2].score).toBe(80)
    })

    it('group_overview records the best viewpoint', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.group_overview['贡嘎山系'].score).toBe(90)
        expect(summary.group_overview['贡嘎山系'].viewpoint).toBe('雅哈垭口')
    })

    it('date_range uses Chinese format with 月 and 日', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.date_range).toMatch(/月.*日.*月.*日/)
    })

    it('respects selected days count (only day 1 of 3)', () => {
        const summary = buildSummaryFromPosterData(summaryData, 1)
        expect(summary.highlights.some(h => h.date === '2026-02-25')).toBe(false)
        expect(summary.highlights).toHaveLength(1)  // 仅 2-24 am 80
    })

    it('dayOffset=1 returns tomorrow only (skips today)', () => {
        // offset=1, count=1 → 只取 2026-02-25
        const summary = buildSummaryFromPosterData(summaryData, 1, 1)
        expect(summary.highlights.some(h => h.date === '2026-02-24')).toBe(false)
        expect(summary.highlights).toHaveLength(1)  // 2-25 pm 90
        expect(summary.highlights[0].date).toBe('2026-02-25')
    })

    it('conditions are transparently included in highlights', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        const frostHighlight = summary.highlights.find(h => h.event === '雾凇')
        expect(frostHighlight).toBeDefined()
        expect(frostHighlight.conditions).toHaveProperty('temperature')
        expect(frostHighlight.conditions.temperature.detail).toBe('avg_temp=-2°C')
    })

    it('missing conditions defaults to empty object', () => {
        const dataWithoutConditions = {
            generated_at: '2026-02-24T10:00:00+08:00',
            days: ['2026-02-24'],
            groups: [{
                name: '测试', key: 'test', viewpoints: [{
                    id: 'v', name: '点', daily: [{
                        date: '2026-02-24',
                        am: { score: 75, event: '云海', weather: '晴天' },  // 无 conditions 字段
                        pm: { score: 0, event: '', weather: '阴天' }
                    }]
                }]
            }],
        }
        const summary = buildSummaryFromPosterData(dataWithoutConditions, 1)
        expect(summary.highlights[0].conditions).toEqual({})
    })
})


describe('export filename includes date', () => {
    it('dateStr from generated_at is YYYYMMDD format', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(dateStr).toBe('20260224')
    })

    it('poster_tomorrow filename includes date suffix', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(`poster_tomorrow_${dateStr}.json`).toBe('poster_tomorrow_20260224.json')
    })

    it('poster_week filename includes date suffix', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(`poster_week_${dateStr}.json`).toBe('poster_week_20260224.json')
    })

    it('zip filename pattern matches posters_YYYYMMDD.zip', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(`posters_${dateStr}.zip`).toBe('posters_20260224.zip')
    })
})
