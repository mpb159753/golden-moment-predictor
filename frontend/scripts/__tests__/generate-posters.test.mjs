import { describe, it, expect } from 'vitest'
import { buildSummary } from '../build-summary.mjs'

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
        const summary = buildSummary(summaryData, 3)
        expect(summary.推荐点位.every(h => h.分数 >= 60)).toBe(true)
        expect(summary.推荐点位).toHaveLength(4)  // score 80, 65, 90, 85
    })

    it('highlights are sorted by score descending', () => {
        const summary = buildSummary(summaryData, 3)
        expect(summary.推荐点位[0].分数).toBe(90)
        expect(summary.推荐点位[1].分数).toBe(85)
        expect(summary.推荐点位[2].分数).toBe(80)
        expect(summary.推荐点位[3].分数).toBe(65)
    })

    it('group_overview records the best viewpoint', () => {
        const summary = buildSummary(summaryData, 3)
        expect(summary.各区概况['贡嘎山系'].分数).toBe(90)
        expect(summary.各区概况['贡嘎山系'].点位).toBe('雅哈垭口')
    })

    it('date_range uses Chinese format with 月 and 日', () => {
        const summary = buildSummary(summaryData, 3)
        expect(summary.适用日期).toMatch(/月.*日.*月.*日/)
    })

    it('respects selected days count (only day 1 of 3)', () => {
        const summary = buildSummary(summaryData, 1)
        expect(summary.推荐点位.some(h => h.日期 === '2026-02-25')).toBe(false)
        expect(summary.推荐点位).toHaveLength(1)  // 仅 2-24 am 80
    })

    it('dayOffset=1 returns tomorrow only (skips today)', () => {
        const summary = buildSummary(summaryData, 1, 1)
        expect(summary.推荐点位.some(h => h.日期 === '2026-02-24')).toBe(false)
        expect(summary.推荐点位).toHaveLength(2)  // 2-25 am 65, pm 90
        expect(summary.推荐点位[0].日期).toBe('2026-02-25')
        expect(summary.推荐点位[1].日期).toBe('2026-02-25')
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
        const summary = buildSummary(allBadData, 1)
        expect(summary.推荐点位).toHaveLength(0)
        expect(summary.各区概况['测试'].分数).toBe(55)
        expect(summary.各区概况['测试'].天气).toBe('阴天')
    })
})
