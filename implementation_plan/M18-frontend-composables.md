# M18: 前端 Composables (组合式函数)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 4 个核心 composable 函数：`useScoreColor`、`useComboTags`、`useAMap`、`useScreenshot`。

**依赖模块:** M16 (项目初始化), M17 (数据层 — useDataLoader 已在 M17 实现)

---

## 背景

Composables 是 Vue 3 Composition API 的复用逻辑单元，所有组件共享调用。这些函数封装了：
- 评分→颜色映射 (ScoreRing/StatusBadge 等公共组件依赖)
- 组合推荐标签计算 (前端自行计算，见 [05-api.md 注释](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md))
- 高德地图初始化和操作封装
- 截图导出功能

### 设计参考

- [10-frontend-common.md §10.0.3 ScoreRing 颜色映射](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend-common.md §10.0.4 组合推荐标签](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend-common.md §10.0.5 地图公共层](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [10-frontend-common.md §10.0.6 截图导出](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)

---

## Task 1: useScoreColor

**Files:**
- Create: `frontend/src/composables/useScoreColor.js`
- Test: `frontend/src/__tests__/composables/useScoreColor.test.js`

### 实现

```javascript
// frontend/src/composables/useScoreColor.js

/**
 * 评分→颜色/状态映射。
 *
 * 映射规则 (来自设计文档 10-frontend-common.md §10.0.3):
 *
 * | 范围    | CSS 变量                   | 状态              | 颜色描述   |
 * |---------|----------------------------|--------------------|------------|
 * | 95-100  | --score-perfect            | Perfect            | 金色渐变   |
 * | 80-94   | --score-recommended        | Recommended        | 翠绿       |
 * | 50-79   | --score-possible           | Possible           | 琥珀       |
 * | 0-49    | --score-not-recommended    | Not Recommended    | 灰色       |
 */
export function useScoreColor() {
  /**
   * 获取评分对应的颜色信息
   * @param {number} score - 0-100 评分
   * @returns {{ color: string, gradient: string|null, status: string, statusCn: string, cssVar: string }}
   */
  function getScoreColor(score) {
    if (score >= 95) return {
      color: '#FFD700',
      gradient: 'linear-gradient(135deg, #FFD700, #FF8C00)',
      status: 'Perfect',
      statusCn: '完美',
      cssVar: '--score-perfect',
    }
    if (score >= 80) return {
      color: '#10B981',
      gradient: null,
      status: 'Recommended',
      statusCn: '推荐',
      cssVar: '--score-recommended',
    }
    if (score >= 50) return {
      color: '#F59E0B',
      gradient: null,
      status: 'Possible',
      statusCn: '一般',
      cssVar: '--score-possible',
    }
    return {
      color: '#9CA3AF',
      gradient: null,
      status: 'Not Recommended',
      statusCn: '不推荐',
      cssVar: '--score-not-recommended',
    }
  }

  /**
   * 获取状态文字对应的颜色 (用于从 API status 字段映射)
   * @param {string} status - 'Perfect' | 'Recommended' | 'Possible' | 'Not Recommended'
   */
  function getStatusColor(status) {
    const map = {
      'Perfect': '#FFD700',
      'Recommended': '#10B981',
      'Possible': '#F59E0B',
      'Not Recommended': '#9CA3AF',
    }
    return map[status] ?? '#9CA3AF'
  }

  return { getScoreColor, getStatusColor }
}
```

### 应测试的内容

- 边界值: `getScoreColor(0)` → Not Recommended
- 边界值: `getScoreColor(49)` → Not Recommended
- 边界值: `getScoreColor(50)` → Possible
- 边界值: `getScoreColor(79)` → Possible
- 边界值: `getScoreColor(80)` → Recommended
- 边界值: `getScoreColor(94)` → Recommended
- 边界值: `getScoreColor(95)` → Perfect (含 gradient)
- 边界值: `getScoreColor(100)` → Perfect
- `getStatusColor('Perfect')` → '#FFD700'

---

## Task 2: useComboTags

**Files:**
- Create: `frontend/src/composables/useComboTags.js`
- Test: `frontend/src/__tests__/composables/useComboTags.test.js`

### 实现

```javascript
// frontend/src/composables/useComboTags.js

/**
 * 组合推荐标签计算 (前端自行计算)。
 *
 * 组合规则 (来自设计文档 10-frontend-common.md §10.0.4):
 *
 * | 标签类型          | 触发条件                                      | 显示文字     |
 * |-------------------|----------------------------------------------|-------------|
 * | combo_day         | 同日 2+ 个 score≥80 的事件                    | 组合日      |
 * | photographer_pick | 金山(sunrise/sunset) + cloud_sea 同日均 ≥80  | 摄影师推荐  |
 * | perfect_day       | 任一事件 score≥95                              | 完美之日    |
 */
export function useComboTags() {
  /**
   * @param {Array<{event_type: string, score: number}>} dayEvents - 某日的事件数组
   * @returns {Array<{type: string, label: string, icon: string}>} 标签列表
   */
  function computeTags(dayEvents) {
    const tags = []
    const recommended = dayEvents.filter(e => e.score >= 80)

    // combo_day: 同日 2+ 个 Recommended 以上事件
    if (recommended.length >= 2) {
      tags.push({ type: 'combo_day', label: '组合日', icon: '🎯' })
    }

    // photographer_pick: 金山+云海同日
    const hasGoldenMountain = recommended.some(e =>
      e.event_type.includes('golden_mountain')
    )
    const hasCloudSea = recommended.some(e =>
      e.event_type === 'cloud_sea'
    )
    if (hasGoldenMountain && hasCloudSea) {
      tags.push({ type: 'photographer_pick', label: '摄影师推荐', icon: '📸' })
    }

    // perfect_day: 有任一事件 95+
    if (dayEvents.some(e => e.score >= 95)) {
      tags.push({ type: 'perfect_day', label: '完美之日', icon: '✨' })
    }

    return tags
  }

  return { computeTags }
}
```

### 应测试的内容

- 空数组 → `[]`
- 单事件 score=90 → `[]` (不足 2 个)
- 两个事件均 score≥80 → `[combo_day]`
- 金山 90 + cloud_sea 85 → `[combo_day, photographer_pick]`
- sunset_golden_mountain 90 + cloud_sea 85 → 也触发 photographer_pick
- 单事件 score=95 → `[perfect_day]`
- 金山 96 + cloud_sea 97 → `[combo_day, photographer_pick, perfect_day]`
- 所有事件 score<80 → `[]`

---

## Task 3: useAMap

**Files:**
- Create: `frontend/src/composables/useAMap.js`
- Test: (不做单元测试，依赖浏览器 + AMap SDK；M22 地图组件中集成测试)

### 实现

```javascript
// frontend/src/composables/useAMap.js
import AMapLoader from '@amap/amap-jsapi-loader'

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
      strokeColor: '#3B82F6',  // --color-primary (AMap 不支持 CSS 变量)
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
```

> [!NOTE]
> `useAMap` 依赖浏览器环境和高德地图 SDK，不做纯单元测试。在 M22 (地图组件) 中通过浏览器集成测试验证。

---

## Task 4: useScreenshot

**Files:**
- Create: `frontend/src/composables/useScreenshot.js`
- Test: `frontend/src/__tests__/composables/useScreenshot.test.js`

### 实现

```javascript
// frontend/src/composables/useScreenshot.js
import html2canvas from 'html2canvas'

/**
 * 截图导出 composable。
 *
 * 策略 (来自设计文档 10-frontend-common.md §10.0.6):
 * - 使用 html2canvas 进行 DOM 区域截图
 * - 2x 分辨率 (Retina 友好)
 * - 支持透明背景 (方案 C 卡片流需要)
 *
 * 各组件通过 ref="screenshotArea" 标记可截图区域。
 */
export function useScreenshot() {
  /**
   * 截取指定 DOM 元素为图片并下载
   * @param {HTMLElement} element - 要截取的 DOM 元素
   * @param {string} filename - 下载文件名
   * @param {Object} options - html2canvas 额外选项
   */
  async function capture(element, filename = 'gmp-prediction.png', options = {}) {
    if (!element) {
      throw new Error('Screenshot target element is required')
    }

    const canvas = await html2canvas(element, {
      scale: 2,
      backgroundColor: null,
      useCORS: true,
      ...options,
    })

    const link = document.createElement('a')
    link.download = filename
    link.href = canvas.toDataURL('image/png')
    link.click()

    return canvas
  }

  /**
   * 截取并返回 canvas (不自动下载，供 ShareCard 合成使用)
   * @param {HTMLElement} element
   * @returns {Promise<HTMLCanvasElement>}
   */
  async function captureToCanvas(element, options = {}) {
    return html2canvas(element, {
      scale: 2,
      backgroundColor: null,
      useCORS: true,
      ...options,
    })
  }

  return { capture, captureToCanvas }
}
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/composables/
```
