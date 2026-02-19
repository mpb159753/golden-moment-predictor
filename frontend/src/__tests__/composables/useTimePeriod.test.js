import { describe, it, expect } from 'vitest'
import { useTimePeriod } from '@/composables/useTimePeriod'

describe('useTimePeriod', () => {
    const { periods, getPeriodScores } = useTimePeriod()

    describe('periods', () => {
        it('returns 4 periods', () => {
            expect(periods).toHaveLength(4)
        })

        it('covers sunrise, daytime, sunset, night', () => {
            const ids = periods.map(p => p.id)
            expect(ids).toEqual(['sunrise', 'daytime', 'sunset', 'night'])
        })
    })

    describe('getPeriodScores', () => {
        it('returns bestEvent correctly for sunrise period with active event', () => {
            const hourly = [
                { hour: 6, events_active: [{ event_type: 'sunrise_golden_mountain', score: 85, status: 'Active' }] },
                { hour: 7, events_active: [{ event_type: 'sunrise_golden_mountain', score: 90, status: 'Active' }] },
            ]
            const result = getPeriodScores(hourly)
            const sunrise = result.find(p => p.id === 'sunrise')
            expect(sunrise.bestScore).toBe(90)
            expect(sunrise.bestEvent).toBe('sunrise_golden_mountain')
        })

        it('returns bestScore=0 and bestEvent=null for empty hourly data', () => {
            const result = getPeriodScores([])
            for (const period of result) {
                expect(period.bestScore).toBe(0)
                expect(period.bestEvent).toBeNull()
            }
        })

        it('handles night period spanning midnight (19-5)', () => {
            const hourly = [
                { hour: 2, events_active: [{ event_type: 'stargazing', score: 70, status: 'Active' }] },
                { hour: 20, events_active: [{ event_type: 'stargazing', score: 60, status: 'Active' }] },
            ]
            const result = getPeriodScores(hourly)
            const night = result.find(p => p.id === 'night')
            // hour 2 (0-4) and hour 20 (19-23) both belong to night
            expect(night.bestScore).toBe(70)
            expect(night.bestEvent).toBe('stargazing')
        })

        it('collects events from the period', () => {
            const hourly = [
                {
                    hour: 10, events_active: [
                        { event_type: 'clear_sky', score: 80, status: 'Active' },
                        { event_type: 'frost', score: 60, status: 'Active' },
                    ]
                },
            ]
            const result = getPeriodScores(hourly)
            const daytime = result.find(p => p.id === 'daytime')
            expect(daytime.events).toHaveLength(2)
            expect(daytime.bestScore).toBe(80)
            expect(daytime.bestEvent).toBe('clear_sky')
        })
    })
})
