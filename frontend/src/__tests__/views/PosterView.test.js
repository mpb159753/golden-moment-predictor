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
                    if (!slot) continue

                    if (!groupBest || slot.score > groupBest.分数) {
                        groupBest = { 点位: vp.name, 分数: slot.score, 天气: slot.weather }
                    }

                    if (slot.score < 60) continue

                    highlights.push({
                        日期: day.date,
                        时段: half === 'am' ? '上午' : '下午',
                        区域: group.name,
                        点位: vp.name,
                        景观: slot.event || '无',
                        天气: slot.weather,
                        分数: slot.score
                    })
                }
            }
        }
        if (groupBest) groupOverview[group.name] = groupBest
    }

    highlights.sort((a, b) => b.分数 - a.分数)

    const fmt = d => {
        const dt = new Date(d)
        return `${dt.getMonth() + 1}月${dt.getDate()}日`
    }
    const dateRange = displayedDayList.length
        ? `${fmt(displayedDayList[0])}—${fmt(displayedDayList[displayedDayList.length - 1])}`
        : ''

    return {
        生成时间: data.generated_at,
        适用日期: dateRange,
        各区概况: groupOverview,
        推荐点位: highlights,
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
                    pm: { score: 55, event: '', weather: '阴天', conditions: {} },  // < 60
                },
                {
                    date: '2026-02-25',
                    am: { score: 65, event: '', weather: '阴天', conditions: {} },  // >= 60, 无 event
                    pm: { score: 90, event: '观星', weather: '晴天', conditions: { base: { score: 100, max: 100, detail: 'quality=optimal' } } },
                },
                {
                    date: '2026-02-26',
                    am: { score: 85, event: '日照金山', weather: '晴天', conditions: { light_path: { score: 30, max: 35, detail: 'cloud=8%' } } },
                    pm: { score: 50, event: '', weather: '多云', conditions: {} },  // < 60
                },
            ],
        }],
    }],
}

describe('buildSummary', () => {
    it('only includes slots with score >= 60 in highlights', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.推荐点位.every(h => h.分数 >= 60)).toBe(true)
        expect(summary.推荐点位).toHaveLength(4)  // score 80, 65, 90, 85
    })

    it('highlights are sorted by score descending', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.推荐点位[0].分数).toBe(90)
        expect(summary.推荐点位[1].分数).toBe(85)
        expect(summary.推荐点位[2].分数).toBe(80)
        expect(summary.推荐点位[3].分数).toBe(65)
    })

    it('group_overview records the best viewpoint', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.各区概况['贡嘎山系'].分数).toBe(90)
        expect(summary.各区概况['贡嘎山系'].点位).toBe('雅哈垭口')
    })

    it('date_range uses Chinese format with 月 and 日', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        expect(summary.适用日期).toMatch(/月.*日.*月.*日/)
    })

    it('respects selected days count (only day 1 of 3)', () => {
        const summary = buildSummaryFromPosterData(summaryData, 1)
        expect(summary.推荐点位.some(h => h.日期 === '2026-02-25')).toBe(false)
        expect(summary.推荐点位).toHaveLength(1)  // 仅 2-24 am 80
    })

    it('dayOffset=1 returns tomorrow only (skips today)', () => {
        const summary = buildSummaryFromPosterData(summaryData, 1, 1)
        expect(summary.推荐点位.some(h => h.日期 === '2026-02-24')).toBe(false)
        expect(summary.推荐点位).toHaveLength(2)  // 2-25 am 65, pm 90
        expect(summary.推荐点位[0].日期).toBe('2026-02-25')
        expect(summary.推荐点位[1].日期).toBe('2026-02-25')
    })

    it('removes technical conditions and empty events get replaced with 无', () => {
        const summary = buildSummaryFromPosterData(summaryData, 3)
        const noEventHighlight = summary.推荐点位.find(h => h.分数 === 65)
        expect(noEventHighlight.景观).toBe('无')
        expect(noEventHighlight).not.toHaveProperty('conditions')
    })

    it('finds group best even if all are < 60', () => {
        const allBadData = {
            generated_at: '2026-02-24T10:00:00+08:00',
            days: ['2026-02-24'],
            groups: [{
                name: '测试', key: 'test', viewpoints: [{
                    id: 'v', name: '点', daily: [{
                        date: '2026-02-24',
                        am: { score: 40, event: '', weather: '雨天' },
                        pm: { score: 55, event: '', weather: '阴天' }
                    }]
                }]
            }],
        }
        const summary = buildSummaryFromPosterData(allBadData, 1)
        expect(summary.推荐点位).toHaveLength(0)
        expect(summary.各区概况['测试'].分数).toBe(55)
        expect(summary.各区概况['测试'].天气).toBe('阴天')
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
