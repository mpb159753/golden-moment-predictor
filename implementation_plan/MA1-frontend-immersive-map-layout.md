# MA1: A 方案 — 沉浸地图首页布局

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 A 方案 (Immersive Map) 的首页布局，包含全屏地图 + 毛玻璃搜索栏 + Bottom Sheet 三层结构。

**依赖模块:** M16 (项目初始化), M17 (数据层), M18 (composables), M19-M21 (公共组件), M22 (地图组件)

---

## 背景

A 方案的核心理念是"地图即一切"。用户通过全屏地图探索川西各观景台，所有信息通过 Bottom Sheet 面板渐进展示。首页由三层组成：底层全屏地图 + 中间浮动搜索栏 + 上层 Bottom Sheet。

### 设计参考

- [10-frontend-A-immersive-map.md §10.A.2 页面结构](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)
- [10-frontend-A-immersive-map.md §10.A.3 交互逻辑](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)
- [10-frontend-A-immersive-map.md §10.A.5 顶部搜索/筛选栏](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)
- [10-frontend-A-immersive-map.md §10.A.9 组件树](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-A-immersive-map.md)

### 组件树 (方案 A 首页)

```
App.vue
└── HomeView.vue (方案A首页)
    ├── MapTopBar.vue          # 搜索 + 筛选 + 日期
    ├── AMapContainer.vue      # 全屏地图 [公共]
    │   ├── ViewpointMarker.vue × N   [公共]
    │   └── RouteLine.vue      [公共]
    ├── BottomSheet.vue        # ★ 方案A核心组件 ★  → MA2
    │   ├── BestRecommendList.vue     → MA3
    │   ├── DaySummary.vue     [公共]
    │   ├── EventList.vue      [公共]
    │   ├── WeekTrend.vue      [公共]
    │   └── HourlyTimeline.vue [公共]
    └── ScreenshotBtn.vue      [公共]
```

---

## Task 1: MapTopBar 搜索/筛选栏

**Files:**
- Create: `frontend/src/components/scheme-a/MapTopBar.vue`

> [!NOTE]
> A 方案专有组件统一放在 `components/scheme-a/` 目录下，与公共组件隔离。

### Props

| Prop | Type | Default | 说明 |
|------|------|---------|------|
| `viewpoints` | Array | [] | 所有观景台 (用于搜索匹配) |
| `selectedDate` | String | — | 当前选中日期 |
| `availableDates` | Array | [] | 可选日期列表 |
| `activeFilters` | Array | [] | 当前激活的事件类型筛选 |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `search` | viewpointId | 搜索选中某个观景台 |
| `filter` | filterTypes[] | 事件类型筛选变更 |
| `date-change` | dateString | 日期切换 |
| `toggle-route` | boolean | 切换线路模式 |

### 实现

```vue
<!-- frontend/src/components/scheme-a/MapTopBar.vue -->
<template>
  <div class="map-top-bar">
    <!-- 搜索框 -->
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索观景台"
        @input="onSearch"
      />
      <!-- 搜索结果下拉 -->
      <ul v-if="searchResults.length" class="search-results">
        <li
          v-for="vp in searchResults"
          :key="vp.id"
          @click="selectResult(vp)"
        >
          {{ vp.name }}
        </li>
      </ul>
    </div>

    <!-- 事件类型筛选 Chips -->
    <div class="filter-chips">
      <button
        v-for="filter in filterOptions"
        :key="filter.type"
        :class="['chip', { active: activeFilters.includes(filter.type) }]"
        @click="toggleFilter(filter.type)"
      >
        {{ filter.icon }}
      </button>
    </div>

    <!-- 日期切换 -->
    <button class="date-btn" @click="showDatePicker = !showDatePicker">
      📅 {{ formatDate(selectedDate) }}
    </button>

    <!-- 线路模式切换 -->
    <button
      :class="['route-btn', { active: routeMode }]"
      @click="toggleRouteMode"
    >
      🛤️
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  viewpoints: { type: Array, default: () => [] },
  selectedDate: { type: String, default: '' },
  availableDates: { type: Array, default: () => [] },
  activeFilters: { type: Array, default: () => [] },
})

const emit = defineEmits(['search', 'filter', 'date-change', 'toggle-route'])

const searchQuery = ref('')
const routeMode = ref(false)
const showDatePicker = ref(false)

const filterOptions = [
  { type: 'golden_mountain', icon: '🏔️' },
  { type: 'cloud_sea', icon: '☁️' },
  { type: 'stargazing', icon: '⭐' },
  { type: 'frost', icon: '❄️' },
]

const searchResults = computed(() => {
  if (!searchQuery.value) return []
  return props.viewpoints.filter(vp =>
    vp.name.includes(searchQuery.value)
  ).slice(0, 5)
})

function selectResult(vp) {
  searchQuery.value = ''
  emit('search', vp.id)
}

function onSearch() {
  // 搜索逻辑由 computed 自动处理
}

function toggleFilter(type) {
  const current = [...props.activeFilters]
  const index = current.indexOf(type)
  if (index >= 0) {
    current.splice(index, 1)
  } else {
    current.push(type)
  }
  emit('filter', current)
}

function toggleRouteMode() {
  routeMode.value = !routeMode.value
  emit('toggle-route', routeMode.value)
}

function formatDate(dateStr) {
  if (!dateStr) return '今天'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.map-top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top));
  background: var(--bg-overlay);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.search-box {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-full);
  padding: 6px 12px;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

.search-icon {
  margin-right: 6px;
  font-size: var(--text-sm);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-elevated);
  list-style: none;
  padding: 4px 0;
  z-index: 10;
}

.search-results li {
  padding: 8px 16px;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.search-results li:hover {
  background: var(--bg-primary);
}

.filter-chips {
  display: flex;
  gap: 4px;
}

.chip {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast);
}

.chip.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.date-btn,
.route-btn {
  height: 32px;
  padding: 0 10px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  font-size: var(--text-xs);
  white-space: nowrap;
  transition: all var(--duration-fast);
}

.route-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}
</style>
```

**Step 1: 创建目录和文件**

```bash
mkdir -p /Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-a
```

然后创建 `MapTopBar.vue`。

**Step 2: 提交**

```bash
git add frontend/src/components/scheme-a/
git commit -m "feat(frontend-a): add MapTopBar with search, filter, date picker"
```

---

## Task 2: HomeView 首页布局

**Files:**
- Modify: `frontend/src/views/HomeView.vue` (替换占位)

### 页面结构

```
┌────────────────────────────┐
│ 🔍 搜索 / 筛选  📅 日期    │  ← MapTopBar (悬浮顶栏)
│                            │
│       全   屏   地   图     │  ← AMapContainer (100vh)
│   ●98 牛背山               │  ← ViewpointMarker × N
│              ●45 折多山     │
│     ●90 磐羊湖             │
│                            │
├────────────────────────────┤
│  ≡ 今日最佳推荐            │  ← BottomSheet (默认20%)
│  🏔️ 牛背山 98分 → 日出金山 │
│  ☁️ 磐羊湖 90分 → 云海     │
└────────────────────────────┘
```

### 实现

```vue
<!-- frontend/src/views/HomeView.vue -->
<template>
  <div class="home-view">
    <!-- 全屏地图 -->
    <AMapContainer
      ref="mapRef"
      height="100vh"
      :map-options="mapOptions"
      @ready="onMapReady"
    />

    <!-- 地图标记 -->
    <template v-if="mapInstance">
      <ViewpointMarker
        v-for="vp in filteredViewpoints"
        :key="vp.id"
        :viewpoint="vp"
        :score="getBestScore(vp.id)"
        :selected="selectedId === vp.id"
        :zoom="currentZoom"
        @click="onMarkerClick(vp)"
      />
      <!-- 线路模式 -->
      <RouteLine
        v-if="routeMode"
        v-for="route in routes"
        :key="route.id"
        :stops="route.stops"
      />
    </template>

    <!-- 顶部搜索/筛选栏 -->
    <MapTopBar
      :viewpoints="viewpoints"
      :selected-date="selectedDate"
      :available-dates="availableDates"
      :active-filters="activeFilters"
      @search="onSearch"
      @filter="onFilter"
      @date-change="onDateChange"
      @toggle-route="onToggleRoute"
    />

    <!-- Bottom Sheet -->
    <BottomSheet
      ref="sheetRef"
      :state="sheetState"
      @state-change="onSheetStateChange"
    >
      <!-- 收起态: 今日最佳推荐 -->
      <template #collapsed>
        <BestRecommendList
          :recommendations="bestRecommendations"
          @select="onRecommendSelect"
        />
      </template>

      <!-- 半展态: 选中观景台当日预测 -->
      <template #half>
        <div v-if="currentViewpoint" class="half-content">
          <DaySummary :day="currentDay" @click="expandSheet" />
          <EventList :events="currentDay?.events ?? []" />
        </div>
      </template>

      <!-- 全展态: 七日预测 -->
      <template #full>
        <div v-if="currentViewpoint" class="full-content">
          <DaySummary :day="currentDay" :clickable="false" />
          <EventList :events="currentDay?.events ?? []" showBreakdown />
          <WeekTrend
            v-if="currentForecast"
            :daily="currentForecast.daily"
            @select="onTrendDateSelect"
          />
          <HourlyTimeline
            v-if="currentTimeline"
            :hourly="currentTimeline.hourly"
          />
          <button class="full-report-btn" @click="goToDetail">
            查看完整报告 →
          </button>
        </div>
      </template>
    </BottomSheet>

    <!-- 截图按钮 (地图右下角) -->
    <ScreenshotBtn
      class="map-screenshot-btn"
      :target="$el"
      filename="gmp-overview.png"
      :before-capture="hideUIForScreenshot"
      :after-capture="restoreUI"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useViewpointStore } from '@/stores/viewpoints'
import { useRouteStore } from '@/stores/routes'
import { useAppStore } from '@/stores/app'
import AMapContainer from '@/components/map/AMapContainer.vue'
import ViewpointMarker from '@/components/map/ViewpointMarker.vue'
import RouteLine from '@/components/map/RouteLine.vue'
import MapTopBar from '@/components/scheme-a/MapTopBar.vue'
import BottomSheet from '@/components/scheme-a/BottomSheet.vue'
import BestRecommendList from '@/components/scheme-a/BestRecommendList.vue'
import DaySummary from '@/components/forecast/DaySummary.vue'
import EventList from '@/components/event/EventList.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'
import HourlyTimeline from '@/components/forecast/HourlyTimeline.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'

const router = useRouter()
const vpStore = useViewpointStore()
const routeStore = useRouteStore()
const appStore = useAppStore()

const mapRef = ref(null)
const sheetRef = ref(null)
const mapInstance = ref(null)

// 地图默认配置 (川西中心)
const mapOptions = {
  zoom: 8,
  center: [102.0, 30.5],
  mapStyle: 'amap://styles/light',
  zooms: [6, 15],
}

// 状态
const sheetState = ref('collapsed')   // 'collapsed' | 'half' | 'full'
const activeFilters = ref([])
const routeMode = ref(false)

// 计算属性
const viewpoints = computed(() => vpStore.index)
const routes = computed(() => routeStore.index)
const selectedId = computed(() => vpStore.selectedId)
const selectedDate = computed(() => vpStore.selectedDate)
const currentViewpoint = computed(() => vpStore.currentViewpoint)
const currentForecast = computed(() => vpStore.currentForecast)
const currentDay = computed(() => vpStore.currentDay)
const currentTimeline = computed(() => vpStore.currentTimeline)

const availableDates = computed(() =>
  currentForecast.value?.daily?.map(d => d.date) ?? []
)

// 筛选后的观景台列表
const filteredViewpoints = computed(() => {
  if (activeFilters.value.length === 0) return viewpoints.value
  return viewpoints.value.filter(vp =>
    vp.capabilities?.some(cap =>
      activeFilters.value.some(f => cap.includes(f))
    )
  )
})

// 今日最佳推荐 (前3个最高分)
const bestRecommendations = computed(() => {
  const results = []
  for (const vp of viewpoints.value) {
    const forecast = vpStore.forecasts[vp.id]
    if (!forecast) continue
    const today = forecast.daily?.[0]
    if (!today) continue
    const bestEvent = today.best_event || today.events?.[0]
    if (bestEvent) {
      results.push({
        viewpoint: vp,
        event: bestEvent,
        score: bestEvent.score,
      })
    }
  }
  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
})

// 获取某个观景台在选中日期的最佳评分 (修复: 不再硬编码 daily[0])
function getBestScore(vpId) {
  const forecast = vpStore.forecasts[vpId]
  if (!forecast) return 0
  // 优先匹配 selectedDate，fallback 到第一天
  const day = forecast.daily?.find(d => d.date === selectedDate.value)
    ?? forecast.daily?.[0]
  return day?.best_event?.score ?? day?.events?.[0]?.score ?? 0
}

// === 事件处理 ===

function onMapReady(map) {
  mapInstance.value = map
}

async function onMarkerClick(vp) {
  // 选中观景台 → 地图飞行 → Bottom Sheet 弹至半展
  await vpStore.selectViewpoint(vp.id)
  const map = mapRef.value?.getMap()
  if (map) {
    map.setZoomAndCenter(12, [vp.location.lon, vp.location.lat], true, 800)
  }
  sheetState.value = 'half'
}

function onRecommendSelect(rec) {
  onMarkerClick(rec.viewpoint)
}

function expandSheet() {
  sheetState.value = 'full'
}

function onSheetStateChange(newState) {
  sheetState.value = newState
  // 拖拽地图时自动收起
  if (newState === 'collapsed') {
    vpStore.clearSelection()
  }
}

function onSearch(vpId) {
  const vp = viewpoints.value.find(v => v.id === vpId)
  if (vp) onMarkerClick(vp)
}

function onFilter(filters) {
  activeFilters.value = filters
}

function onDateChange(date) {
  vpStore.selectDate(date)
}

function onToggleRoute(enabled) {
  routeMode.value = enabled
}

function onTrendDateSelect(date) {
  vpStore.selectDate(date)
}

function goToDetail() {
  if (selectedId.value) {
    router.push(`/viewpoint/${selectedId.value}`)
  }
}

// === 详情页返回后状态恢复 (§10.A.3 S4→S1) ===
import { onActivated } from 'vue'
onActivated(() => {
  // 从详情页返回时，重置 BottomSheet 到收起态、清除选中
  sheetState.value = 'collapsed'
  vpStore.clearSelection()
})

// 截图辅助
function hideUIForScreenshot() {
  if (sheetRef.value) sheetRef.value.$el.style.display = 'none'
  document.querySelector('.map-top-bar')?.style.setProperty('display', 'none')
}

function restoreUI() {
  if (sheetRef.value) sheetRef.value.$el.style.display = ''
  document.querySelector('.map-top-bar')?.style.setProperty('display', '')
}

// === 初始化 ===

onMounted(async () => {
  await vpStore.loadIndex()
  await routeStore.loadIndex()

  // 懒加载: 先加载前3个观景台的预测 (参考 §10.A.10)
  const first3 = viewpoints.value.slice(0, 3)
  await Promise.all(first3.map(vp => vpStore.loadForecast(vp.id)))
})

// 监听地图拖拽 → 收起 Bottom Sheet
// 监听缩放变化 → 切换 Marker 缩略模式 (§10.A.3 "双指缩放")
const currentZoom = ref(mapOptions.zoom)

watch(mapInstance, (map) => {
  if (map) {
    map.on('dragstart', () => {
      if (sheetState.value !== 'collapsed') {
        sheetState.value = 'collapsed'
      }
    })
    map.on('zoomchange', () => {
      currentZoom.value = map.getZoom()
    })
  }
})
</script>

<style scoped>
.home-view {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.map-screenshot-btn {
  position: fixed;
  right: 16px;
  bottom: 28%;
  z-index: 90;
}

.half-content,
.full-content {
  padding: 16px;
}

.full-report-btn {
  width: 100%;
  padding: 12px;
  margin-top: 16px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.full-report-btn:hover {
  background: #2563EB;
}
</style>
```

### 横屏适配 (Desktop)

在 `style` 中追加媒体查询，横屏时 BottomSheet 变为右侧面板:

```css
@media (min-width: 1024px) {
  .home-view {
    display: grid;
    grid-template-columns: 1fr 380px;
  }

  /* 此处 BottomSheet 在 MA2 中通过 prop 控制为侧边栏模式 */
}
```

**Step 1: 替换 HomeView.vue**

**Step 2: 提交**

```bash
git add frontend/src/views/HomeView.vue
git commit -m "feat(frontend-a): implement immersive map HomeView layout"
```

---

## Task 3: Marker 交互增强

**Files:**
- Modify: `frontend/src/components/map/ViewpointMarker.vue`

### 三种 Marker 状态 (参考 §10.A.4)

设计文档定义了三种 Marker 状态:

| 状态 | 条件 | 样式 |
|------|------|------|
| **默认** | 常态 | 圆角矩形，图标 + 评分，背景色 = scoreColor |
| **选中** | selected=true | 展开名称，弹跳动画，白色外描边发光，z-index 提升 |
| **缩略** | zoom < 9 | 仅圆点，颜色 = scoreColor |

### Marker 聚类

当 zoom 较低时使用高德 MarkerCluster 插件，需提供**自定义渲染模板**展示聚合数量和最高分 (参考 §10.A.4):

```javascript
// 在 HomeView 的 onMapReady 中启用聚类
import AMapLoader from '@amap/amap-jsapi-loader'

function onMapReady(map) {
  mapInstance.value = map
  // 加载聚类插件
  map.plugin(['AMap.MarkerCluster'], () => {
    const cluster = new AMap.MarkerCluster(map, [], {
      gridSize: 80,
      renderClusterMarker(context) {
        // 计算聚合内最高分
        const points = context.clusterData
        const maxScore = Math.max(...points.map(p => p.score || 0))
        const count = context.count
        // 自定义渲染: 显示聚合数量 + 最高分
        context.marker.setContent(
          `<div class="cluster-marker">
             <div class="cluster-count">${count}个点</div>
             <div class="cluster-best">最高${maxScore}</div>
           </div>`
        )
      },
    })
  })
}
```

### 自定义 Marker DOM (在 ViewpointMarker 中)

```html
<!-- 默认 Marker -->
<div class="vp-marker" :class="{ selected, 'zoom-mini': isZoomMini }">
  <template v-if="isZoomMini">
    <div class="marker-dot" :style="{ background: scoreColor }" />
  </template>
  <template v-else-if="selected">
    <div class="marker-expanded" :style="{ background: scoreColor }">
      <div class="marker-name">{{ viewpoint.name }}</div>
      <div class="marker-score">{{ eventIcon }} {{ score }} {{ statusLabel }}</div>
    </div>
    <div class="marker-arrow" />
  </template>
  <template v-else>
    <div class="marker-default" :style="{ background: scoreColor }">
      <span>{{ eventIcon }} {{ score }}</span>
    </div>
    <div class="marker-arrow" />
  </template>
</div>
```

**Step 1: 增强 ViewpointMarker 组件**

在 M22 的基础上添加三种状态支持和缩放监听。

**Step 2: 提交**

```bash
git add frontend/src/components/map/ViewpointMarker.vue
git commit -m "feat(frontend-a): enhance ViewpointMarker with 3-state design"
```

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm run dev
```

手动验证:
1. 访问首页 → 全屏地图加载，顶部显示毛玻璃搜索栏
2. 地图上显示所有观景台 Marker (颜色反映评分)
3. 搜索框输入"牛背" → 下拉显示匹配结果
4. 点击事件类型筛选 Chip → 地图标记过滤
5. 日期切换 → Marker 颜色更新
6. 点击 Marker → 地图飞行至该点
7. Bottom Sheet 平时显示"今日最佳推荐"

```bash
# 确认构建不报错
npm run build
```
