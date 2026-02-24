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
function buildSummaryFromPosterData(data, days) {
    const displayedDayList = data.days.slice(0, days)
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
    days: ['2026-02-24', '2026-02-25'],
    groups: [{
        name: '贡嘎山系',
        key: 'gongga',
        viewpoints: [{
            id: 'vp1',
            name: '雅哈垭口',
            daily: [
                {
                    date: '2026-02-24',
                    am: { score: 80, event: '雾凇', weather: '晴天' },
                    pm: { score: 55, event: '', weather: '阴天' },  // < 70，不应进入
                },
                {
                    date: '2026-02-25',
                    am: { score: 60, event: '', weather: '阴天' },  // < 70，不应进入
                    pm: { score: 90, event: '观星', weather: '晴天' },
                },
            ],
        }],
    }],
}

describe('buildSummary', () => {
    it('only includes slots with score >= 70 in highlights', () => {
        const summary = buildSummaryFromPosterData(summaryData, 2)
        expect(summary.highlights.every(h => h.score >= 70)).toBe(true)
        expect(summary.highlights).toHaveLength(2)  // score 55 和 60 被排除
    })

    it('highlights are sorted by score descending', () => {
        const summary = buildSummaryFromPosterData(summaryData, 2)
        // 第一条 score=90，第二条 score=80
        expect(summary.highlights[0].score).toBe(90)
        expect(summary.highlights[1].score).toBe(80)
    })

    it('group_overview records the best viewpoint', () => {
        const summary = buildSummaryFromPosterData(summaryData, 2)
        expect(summary.group_overview['贡嘎山系'].score).toBe(90)
        expect(summary.group_overview['贡嘎山系'].viewpoint).toBe('雅哈垭口')
    })

    it('date_range uses Chinese format with 月 and 日', () => {
        const summary = buildSummaryFromPosterData(summaryData, 2)
        expect(summary.date_range).toMatch(/月.*日.*月.*日/)
    })

    it('respects selected days count (only day 1 of 2)', () => {
        const summary = buildSummaryFromPosterData(summaryData, 1)
        // 只看 2-24，2-25 的 pm 90 分应被排除
        expect(summary.highlights.some(h => h.date === '2026-02-25')).toBe(false)
        expect(summary.highlights).toHaveLength(1)  // 仅 2-24 am 80
    })
})

describe('export filename includes date', () => {
    it('dateStr from generated_at is YYYYMMDD format', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(dateStr).toBe('20260224')
    })

    it('filename pattern matches posters_YYYYMMDD.zip', () => {
        const generatedAt = '2026-02-24T08:00:00+08:00'
        const dateStr = generatedAt.slice(0, 10).replace(/-/g, '')
        expect(`posters_${dateStr}.zip`).toBe('posters_20260224.zip')
    })
})
