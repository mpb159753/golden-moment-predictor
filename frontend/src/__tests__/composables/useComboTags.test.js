import { describe, it, expect } from 'vitest'
import { useComboTags } from '@/composables/useComboTags'

describe('useComboTags', () => {
    const { computeTags } = useComboTags()

    it('returns empty array for empty events', () => {
        expect(computeTags([])).toEqual([])
    })

    it('returns empty array for single event with score 90', () => {
        const events = [{ event_type: 'sunrise_golden_mountain', score: 90 }]
        expect(computeTags(events)).toEqual([])
    })

    it('returns combo_day for two events both score >= 80', () => {
        const events = [
            { event_type: 'sunrise_golden_mountain', score: 85 },
            { event_type: 'cloud_sea', score: 80 },
        ]
        const tags = computeTags(events)
        expect(tags).toHaveLength(2) // combo_day + photographer_pick
        expect(tags.find(t => t.type === 'combo_day')).toEqual({
            type: 'combo_day', label: '组合日', icon: '🎯',
        })
    })

    it('returns photographer_pick for golden_mountain + cloud_sea both >= 80', () => {
        const events = [
            { event_type: 'sunrise_golden_mountain', score: 90 },
            { event_type: 'cloud_sea', score: 85 },
        ]
        const tags = computeTags(events)
        expect(tags.find(t => t.type === 'photographer_pick')).toEqual({
            type: 'photographer_pick', label: '摄影师推荐', icon: '📸',
        })
    })

    it('returns photographer_pick for sunset_golden_mountain + cloud_sea', () => {
        const events = [
            { event_type: 'sunset_golden_mountain', score: 90 },
            { event_type: 'cloud_sea', score: 85 },
        ]
        const tags = computeTags(events)
        expect(tags.find(t => t.type === 'photographer_pick')).toBeTruthy()
    })

    it('returns perfect_day for single event with score 95', () => {
        const events = [{ event_type: 'stargazing', score: 95 }]
        const tags = computeTags(events)
        expect(tags).toHaveLength(1)
        expect(tags[0]).toEqual({
            type: 'perfect_day', label: '完美之日', icon: '✨',
        })
    })

    it('returns all three tags when conditions met', () => {
        const events = [
            { event_type: 'sunrise_golden_mountain', score: 96 },
            { event_type: 'cloud_sea', score: 97 },
        ]
        const tags = computeTags(events)
        expect(tags).toHaveLength(3)
        expect(tags.map(t => t.type)).toEqual([
            'combo_day', 'photographer_pick', 'perfect_day',
        ])
    })

    it('returns empty array when all events score < 80', () => {
        const events = [
            { event_type: 'sunrise_golden_mountain', score: 70 },
            { event_type: 'cloud_sea', score: 60 },
        ]
        expect(computeTags(events)).toEqual([])
    })
})
