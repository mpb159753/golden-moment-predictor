import { describe, it, expect, vi, beforeEach } from 'vitest'
import { convertToGCJ02, batchConvertToGCJ02, clearConvertCache } from '@/composables/useCoordConvert'

/**
 * 创建 AMap.convertFrom 的 mock
 * 模拟偏移: lon + 0.006, lat + 0.003 (近似 GCJ-02 偏移量)
 */
function createMockAMap({ shouldFail = false } = {}) {
    return {
        convertFrom: vi.fn((lnglat, type, callback) => {
            if (shouldFail) {
                callback('error', { info: 'FAILED' })
                return
            }
            const [lon, lat] = lnglat
            const converted = {
                getLng: () => lon + 0.006,
                getLat: () => lat + 0.003,
            }
            callback('complete', {
                info: 'ok',
                locations: [converted],
            })
        }),
    }
}

describe('useCoordConvert', () => {
    beforeEach(() => {
        clearConvertCache()
    })

    describe('convertToGCJ02', () => {
        it('converts WGS-84 to GCJ-02 via AMap.convertFrom', async () => {
            const AMap = createMockAMap()
            const [lon, lat] = await convertToGCJ02(AMap, 102.932, 31.096)

            expect(AMap.convertFrom).toHaveBeenCalledWith(
                [102.932, 31.096],
                'gps',
                expect.any(Function),
            )
            expect(lon).toBeCloseTo(102.938, 3)
            expect(lat).toBeCloseTo(31.099, 3)
        })

        it('returns cached result on second call (no API re-call)', async () => {
            const AMap = createMockAMap()

            const result1 = await convertToGCJ02(AMap, 102.0, 30.5)
            const result2 = await convertToGCJ02(AMap, 102.0, 30.5)

            expect(AMap.convertFrom).toHaveBeenCalledTimes(1)
            expect(result1).toEqual(result2)
        })

        it('falls back to original coords when AMap is null', async () => {
            const [lon, lat] = await convertToGCJ02(null, 102.0, 30.5)
            expect(lon).toBe(102.0)
            expect(lat).toBe(30.5)
        })

        it('falls back to original coords when convertFrom is missing', async () => {
            const AMap = {} // no convertFrom method
            const [lon, lat] = await convertToGCJ02(AMap, 102.0, 30.5)
            expect(lon).toBe(102.0)
            expect(lat).toBe(30.5)
        })

        it('falls back to original coords when API call fails', async () => {
            const AMap = createMockAMap({ shouldFail: true })
            const [lon, lat] = await convertToGCJ02(AMap, 102.0, 30.5)
            expect(lon).toBe(102.0)
            expect(lat).toBe(30.5)
        })
    })

    describe('batchConvertToGCJ02', () => {
        it('converts multiple locations', async () => {
            const AMap = createMockAMap()
            const locations = [
                { lon: 102.0, lat: 30.5 },
                { lon: 103.0, lat: 31.0 },
            ]

            const results = await batchConvertToGCJ02(AMap, locations)

            expect(results).toHaveLength(2)
            expect(results[0][0]).toBeCloseTo(102.006, 3)
            expect(results[0][1]).toBeCloseTo(30.503, 3)
            expect(results[1][0]).toBeCloseTo(103.006, 3)
            expect(results[1][1]).toBeCloseTo(31.003, 3)
        })

        it('returns empty array for empty input', async () => {
            const AMap = createMockAMap()
            const results = await batchConvertToGCJ02(AMap, [])
            expect(results).toEqual([])
        })

        it('returns empty array for null input', async () => {
            const AMap = createMockAMap()
            const results = await batchConvertToGCJ02(AMap, null)
            expect(results).toEqual([])
        })

        it('uses cache for repeated locations', async () => {
            const AMap = createMockAMap()
            const locations = [
                { lon: 102.0, lat: 30.5 },
                { lon: 102.0, lat: 30.5 }, // duplicate
                { lon: 103.0, lat: 31.0 },
            ]

            await batchConvertToGCJ02(AMap, locations)

            // Only 2 unique coords should trigger API calls
            expect(AMap.convertFrom).toHaveBeenCalledTimes(2)
        })
    })

    describe('clearConvertCache', () => {
        it('clears cache so next call hits API again', async () => {
            const AMap = createMockAMap()

            await convertToGCJ02(AMap, 102.0, 30.5)
            expect(AMap.convertFrom).toHaveBeenCalledTimes(1)

            clearConvertCache()

            await convertToGCJ02(AMap, 102.0, 30.5)
            expect(AMap.convertFrom).toHaveBeenCalledTimes(2)
        })
    })
})
