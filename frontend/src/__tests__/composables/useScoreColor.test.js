import { describe, it, expect } from 'vitest'
import { useScoreColor } from '@/composables/useScoreColor'

describe('useScoreColor', () => {
    describe('getScoreColor', () => {
        const { getScoreColor } = useScoreColor()

        it('returns Not Recommended for score 0', () => {
            const result = getScoreColor(0)
            expect(result.status).toBe('Not Recommended')
            expect(result.statusCn).toBe('不推荐')
            expect(result.color).toBe('#9CA3AF')
            expect(result.cssVar).toBe('--score-not-recommended')
            expect(result.gradient).toBeNull()
        })

        it('returns Not Recommended for score 49', () => {
            const result = getScoreColor(49)
            expect(result.status).toBe('Not Recommended')
        })

        it('returns Possible for score 50', () => {
            const result = getScoreColor(50)
            expect(result.status).toBe('Possible')
            expect(result.statusCn).toBe('一般')
            expect(result.color).toBe('#F59E0B')
            expect(result.cssVar).toBe('--score-possible')
            expect(result.gradient).toBeNull()
        })

        it('returns Possible for score 79', () => {
            const result = getScoreColor(79)
            expect(result.status).toBe('Possible')
        })

        it('returns Recommended for score 80', () => {
            const result = getScoreColor(80)
            expect(result.status).toBe('Recommended')
            expect(result.statusCn).toBe('推荐')
            expect(result.color).toBe('#10B981')
            expect(result.cssVar).toBe('--score-recommended')
            expect(result.gradient).toBeNull()
        })

        it('returns Recommended for score 94', () => {
            const result = getScoreColor(94)
            expect(result.status).toBe('Recommended')
        })

        it('returns Perfect for score 95 with gradient', () => {
            const result = getScoreColor(95)
            expect(result.status).toBe('Perfect')
            expect(result.statusCn).toBe('完美')
            expect(result.color).toBe('#FFD700')
            expect(result.cssVar).toBe('--score-perfect')
            expect(result.gradient).toBe('linear-gradient(135deg, #FFD700, #FF8C00)')
        })

        it('returns Perfect for score 100', () => {
            const result = getScoreColor(100)
            expect(result.status).toBe('Perfect')
            expect(result.gradient).not.toBeNull()
        })
    })

    describe('getStatusColor', () => {
        const { getStatusColor } = useScoreColor()

        it('returns gold for Perfect status', () => {
            expect(getStatusColor('Perfect')).toBe('#FFD700')
        })

        it('returns green for Recommended status', () => {
            expect(getStatusColor('Recommended')).toBe('#10B981')
        })

        it('returns amber for Possible status', () => {
            expect(getStatusColor('Possible')).toBe('#F59E0B')
        })

        it('returns gray for Not Recommended status', () => {
            expect(getStatusColor('Not Recommended')).toBe('#9CA3AF')
        })

        it('returns gray for unknown status', () => {
            expect(getStatusColor('Unknown')).toBe('#9CA3AF')
        })
    })
})
