/**
 * useCoordConvert — WGS-84 → GCJ-02 坐标转换工具
 *
 * 使用高德地图 AMap.convertFrom API 将 GPS (WGS-84) 坐标
 * 转换为高德地图 (GCJ-02) 坐标。内置内存缓存以避免重复网络请求。
 *
 * 背景: 后端配置文件使用 WGS-84 坐标 (Open-Meteo 天气 API 所需),
 * 但高德地图底图使用 GCJ-02 坐标系, 直接传入 WGS-84 会导致
 * 标记偏移约 300-500 米。
 */

/** @type {Map<string, [number, number]>} 坐标缓存 key: "lon,lat" → [gcjLon, gcjLat] */
const cache = new Map()

/**
 * 将单个 WGS-84 坐标转换为 GCJ-02 坐标
 *
 * @param {Object} AMap - 高德地图 SDK 对象
 * @param {number} lon - WGS-84 经度
 * @param {number} lat - WGS-84 纬度
 * @returns {Promise<[number, number]>} [gcjLon, gcjLat]
 */
export function convertToGCJ02(AMap, lon, lat) {
    const key = `${lon},${lat}`

    // 缓存命中
    if (cache.has(key)) {
        return Promise.resolve(cache.get(key))
    }

    // AMap SDK 不可用时降级为原始坐标
    if (!AMap || !AMap.convertFrom) {
        return Promise.resolve([lon, lat])
    }

    return new Promise((resolve) => {
        AMap.convertFrom([lon, lat], 'gps', (status, result) => {
            if (status === 'complete' && result.info === 'ok' && result.locations?.length) {
                const loc = result.locations[0]
                const converted = [loc.getLng(), loc.getLat()]
                cache.set(key, converted)
                resolve(converted)
            } else {
                // 转换失败时降级为原始坐标
                resolve([lon, lat])
            }
        })
    })
}

/**
 * 批量将 WGS-84 坐标转换为 GCJ-02 坐标
 *
 * @param {Object} AMap - 高德地图 SDK 对象
 * @param {Array<{lon: number, lat: number}>} locations - WGS-84 坐标数组
 * @returns {Promise<Array<[number, number]>>} GCJ-02 坐标数组 [[gcjLon, gcjLat], ...]
 */
export function batchConvertToGCJ02(AMap, locations) {
    if (!locations || locations.length === 0) {
        return Promise.resolve([])
    }

    return Promise.all(
        locations.map(loc => convertToGCJ02(AMap, loc.lon, loc.lat))
    )
}

/**
 * 清除坐标转换缓存 (主要用于测试)
 */
export function clearConvertCache() {
    cache.clear()
}
