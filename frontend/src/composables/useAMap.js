import AMapLoader from '@amap/amap-jsapi-loader'
import { useScoreColor } from './useScoreColor'
import { convertToGCJ02, batchConvertToGCJ02 } from './useCoordConvert'

/**
 * 生成评分标记的 HTML 内容
 * @param {number} score - 评分值
 * @param {string} background - CSS background 值 (颜色或渐变)
 * @returns {string} HTML 字符串
 */
function createMarkerContent(score, background) {
    return `<div style="
        width: 40px; height: 40px; border-radius: 50%;
        background: ${background};
        color: white; display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        cursor: pointer;
    ">${score}</div>`
}

/**
 * 高德地图封装 composable。
 *
 * 初始化参数 (来自设计文档 10-frontend-common.md §10.0.5):
 * - 默认中心: [102.0, 30.5] (川西中心)
 * - 默认缩放: 8
 * - 风格: 浅色主题
 * - 缩放范围: [6, 15]
 *
 * @param {string} containerId - 地图容器 DOM 元素 ID
 */
export function useAMap(containerId) {
    let map = null
    let AMap = null

    /**
     * 初始化地图
     * @param {Object} options - 覆盖默认选项
     * @returns {Promise<{ success: boolean, error?: Error }>}
     */
    async function init(options = {}) {
        try {
            // 安全配置必须在 SDK 加载之前设置
            window._AMapSecurityConfig = {
                securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE,
            }

            AMap = await AMapLoader.load({
                key: import.meta.env.VITE_AMAP_KEY,
                version: '2.0',
                plugins: ['AMap.Scale', 'AMap.ToolBar'],
            })

            map = new AMap.Map(containerId, {
                zoom: 8,
                center: [102.0, 30.5],
                mapStyle: 'amap://styles/light',
                zooms: [6, 15],
                ...options,
            })

            return { success: true }
        } catch (error) {
            console.error('[useAMap] 地图初始化失败:', error)
            AMap = null
            map = null
            return { success: false, error }
        }
    }

    /**
     * 飞行到指定坐标
     * @param {number} lon - 经度
     * @param {number} lat - 纬度
     * @param {number} zoom - 缩放级别
     */
    async function flyTo(lon, lat, zoom = 12) {
        if (!map) return
        const [gcjLon, gcjLat] = await convertToGCJ02(AMap, lon, lat)
        map.setZoomAndCenter(zoom, [gcjLon, gcjLat], true, 800)
    }

    /**
     * 添加观景台标记
     * @param {Object} viewpoint - { id, name, location: {lat, lon} }
     * @param {number} score - 最佳评分
     * @param {Function} onClick - 点击回调
     * @returns {AMap.Marker}
     */
    async function addMarker(viewpoint, score, onClick) {
        if (!AMap || !map) return null

        const { getScoreColor } = useScoreColor()
        const colorInfo = getScoreColor(score)

        const [gcjLon, gcjLat] = await convertToGCJ02(
            AMap, viewpoint.location.lon, viewpoint.location.lat
        )

        const marker = new AMap.Marker({
            position: [gcjLon, gcjLat],
            content: createMarkerContent(score, colorInfo.gradient || colorInfo.color),
            offset: new AMap.Pixel(-20, -20),
            title: viewpoint.name,
        })

        if (onClick) {
            marker.on('click', () => onClick(viewpoint))
        }

        map.add(marker)
        return marker
    }

    /**
     * 添加线路连线
     * @param {Array<{location: {lat, lon}}>} stops - 线路站点数组
     * @returns {AMap.Polyline}
     */
    async function addRouteLine(stops) {
        if (!AMap || !map) return null

        const locations = stops.map(s => s.location)
        const path = await batchConvertToGCJ02(AMap, locations)

        const polyline = new AMap.Polyline({
            path,
            strokeColor: '#3B82F6',
            strokeWeight: 3,
            strokeStyle: 'dashed',
            showDir: true,
        })

        map.add(polyline)
        return polyline
    }

    /**
     * 自适应视野
     * @param {Array<{location: {lat, lon}}>} viewpoints - 观景台数组
     */
    function fitBounds(viewpoints) {
        if (!map || viewpoints.length === 0) return
        map.setFitView(null, false, [50, 50, 50, 50])
    }

    /**
     * 销毁地图实例
     */
    function destroy() {
        if (map) {
            map.destroy()
            map = null
        }
    }

    return { init, flyTo, addMarker, addRouteLine, fitBounds, destroy, map: () => map, getAMapModule: () => AMap }
}
