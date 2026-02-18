import AMapLoader from '@amap/amap-jsapi-loader'
import { useScoreColor } from './useScoreColor'

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
     * @returns {Promise<void>}
     */
    async function init(options = {}) {
        AMap = await AMapLoader.load({
            key: import.meta.env.VITE_AMAP_KEY,
            version: '2.0',
            plugins: ['AMap.Scale', 'AMap.ToolBar'],
        })

        // 安全配置
        window._AMapSecurityConfig = {
            securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE,
        }

        map = new AMap.Map(containerId, {
            zoom: 8,
            center: [102.0, 30.5],
            mapStyle: 'amap://styles/light',
            zooms: [6, 15],
            ...options,
        })
    }

    /**
     * 飞行到指定坐标
     * @param {number} lon - 经度
     * @param {number} lat - 纬度
     * @param {number} zoom - 缩放级别
     */
    function flyTo(lon, lat, zoom = 12) {
        if (!map) return
        map.setZoomAndCenter(zoom, [lon, lat], true, 800)
    }

    /**
     * 添加观景台标记
     * @param {Object} viewpoint - { id, name, location: {lat, lon} }
     * @param {number} score - 最佳评分
     * @param {Function} onClick - 点击回调
     * @returns {AMap.Marker}
     */
    function addMarker(viewpoint, score, onClick) {
        if (!AMap || !map) return null

        const { getScoreColor } = useScoreColor()
        const colorInfo = getScoreColor(score)

        const marker = new AMap.Marker({
            position: [viewpoint.location.lon, viewpoint.location.lat],
            content: `
        <div style="
          width: 40px; height: 40px; border-radius: 50%;
          background: ${colorInfo.gradient || colorInfo.color};
          color: white; display: flex; align-items: center; justify-content: center;
          font-weight: 700; font-size: 14px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
          cursor: pointer;
        ">${score}</div>
      `,
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
    function addRouteLine(stops) {
        if (!AMap || !map) return null

        const path = stops.map(s => [s.location.lon, s.location.lat])

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

    return { init, flyTo, addMarker, addRouteLine, fitBounds, destroy, map: () => map }
}
