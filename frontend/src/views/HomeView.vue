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
        v-for="(vp, idx) in filteredViewpoints"
        :key="vp.id"
        :viewpoint="vp"
        :score="getBestScore(vp.id)"
        :selected="selectedId === vp.id"
        :zoom="currentZoom"
        :map="mapInstance"
        :loading="!vpStore.forecasts[vp.id]"
        :enter-delay="idx * 0.08"
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

      <!-- 半展态: 线路模式/选中观景台当日预测 -->
      <template #half>
        <RoutePanel
          v-if="routeMode && selectedRoute"
          :route="selectedRoute"
          :selected-stop-id="selectedId"
          @close="routeMode = false; sheetState = 'collapsed'"
          @select-stop="onRouteStopClick"
        />
        <div v-else-if="currentViewpoint" class="half-content">
          <DaySummary :day="currentDay" @click="expandSheet" />
          <EventList :events="currentDay?.events ?? []" />
        </div>
      </template>

      <!-- 全展态: 七日预测 -->
      <template #full>
        <div v-if="currentViewpoint" ref="sheetContentRef" class="full-content">
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
          <div class="full-actions">
            <button class="full-report-btn" @click="goToDetail">
              查看完整报告 →
            </button>
            <ScreenshotBtn
              :target="sheetContentRef"
              filename="gmp-prediction.png"
              label="📸 截图分享"
            />
          </div>
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

    <!-- GMP Logo 水印 -->
    <div class="map-watermark">
      <span class="watermark-text">GMP 川西景观预测</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useViewpointStore } from '@/stores/viewpoints'
import { useRouteStore } from '@/stores/routes'
import AMapContainer from '@/components/map/AMapContainer.vue'
import ViewpointMarker from '@/components/map/ViewpointMarker.vue'
import RouteLine from '@/components/map/RouteLine.vue'
import MapTopBar from '@/components/scheme-a/MapTopBar.vue'
import BottomSheet from '@/components/scheme-a/BottomSheet.vue'
import RoutePanel from '@/components/scheme-a/RoutePanel.vue'
import BestRecommendList from '@/components/scheme-a/BestRecommendList.vue'
import DaySummary from '@/components/forecast/DaySummary.vue'
import EventList from '@/components/event/EventList.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'
import HourlyTimeline from '@/components/forecast/HourlyTimeline.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'

const router = useRouter()
const vpStore = useViewpointStore()
const routeStore = useRouteStore()

const mapRef = ref(null)
const sheetRef = ref(null)
const sheetContentRef = ref(null)
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
const selectedRoute = computed(() => routes.value[0] ?? null)
const selectedId = computed(() => vpStore.selectedId)
const selectedDate = computed(() => vpStore.selectedDate)
const currentViewpoint = computed(() => vpStore.currentViewpoint)
const currentForecast = computed(() => vpStore.currentForecast)
const currentDay = computed(() => vpStore.currentDay)
const currentTimeline = computed(() => vpStore.currentTimeline)

const availableDates = computed(() => {
  // 优先用当前选中观景台的预测日期，否则用任一已加载的 forecast
  const forecast = currentForecast.value
    || Object.values(vpStore.forecasts)[0]
    || null
  return forecast?.daily?.map(d => d.date) ?? []
})

// 筛选后的观景台列表
const filteredViewpoints = computed(() => {
  if (activeFilters.value.length === 0) return viewpoints.value
  return viewpoints.value.filter(vp =>
    vp.capabilities?.some(cap =>
      activeFilters.value.some(f => cap.includes(f))
    )
  )
})

// 当日最佳推荐 (前3个最高分)
const bestRecommendations = computed(() => {
  const results = []
  for (const vp of viewpoints.value) {
    const forecast = vpStore.forecasts[vp.id]
    if (!forecast) continue
    const day = forecast.daily?.find(d => d.date === selectedDate.value)
      ?? forecast.daily?.[0]
    if (!day) continue
    const bestEvent = day.best_event || day.events?.[0]
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

// 获取某个观景台在选中日期的最佳评分
function getBestScore(vpId) {
  const forecast = vpStore.forecasts[vpId]
  if (!forecast) return 0
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
  const map = mapRef.value?.getMap?.()
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
  if (enabled) {
    sheetState.value = 'half'
  } else {
    sheetState.value = 'collapsed'
  }
}

function onRouteStopClick(stop) {
  const vp = viewpoints.value.find(v => v.id === stop.viewpoint_id)
  if (vp) onMarkerClick(vp)
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
onActivated(() => {
  sheetState.value = 'collapsed'
  vpStore.clearSelection()
})

// 截图辅助
function hideUIForScreenshot() {
  if (sheetRef.value) sheetRef.value.$el.style.display = 'none'
  document.querySelector('.map-top-bar')?.style?.setProperty('display', 'none')
}

function restoreUI() {
  if (sheetRef.value) sheetRef.value.$el.style.display = ''
  document.querySelector('.map-top-bar')?.style?.setProperty('display', '')
}

// === 初始化 ===

onMounted(async () => {
  await vpStore.init()
  await routeStore.init()

  // 懒加载: 先加载前3个观景台的预测 (参考 §10.A.10)
  const first3 = viewpoints.value.slice(0, 3)
  await Promise.all(first3.map(vp => vpStore.ensureForecast(vp.id)))

  // 后台静默加载剩余观景台 (低优先级)
  const rest = viewpoints.value.slice(3)
  for (const vp of rest) {
    requestIdleCallback(() => {
      vpStore.ensureForecast(vp.id)
    })
  }
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

@media (min-width: 1024px) {
  .home-view {
    display: grid;
    grid-template-columns: 1fr 380px;
  }
}

.full-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  align-items: center;
}

.full-actions .full-report-btn {
  flex: 1;
  margin-top: 0;
}

.map-watermark {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 80;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  backdrop-filter: blur(4px);
}
</style>
