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
        :best-event="getBestEvent(vp.id)"
        :selected="selectedId === vp.id"
        :zoom="currentZoom"
        :rank="vpRankMap[vp.id] || 'low'"
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
        <div v-else-if="currentViewpoint" class="half-content" @click="expandSheet">
          <!-- ① 标题行: 景点名 + 最高分 + 图标 -->
          <div class="half-title-row">
            <span class="half-vp-name">{{ currentViewpoint.name }}</span>
            <div class="half-title-right">
              <span class="half-best-score">
                <EventIcon v-if="currentDay?.best_event?.event_type" :event-type="currentDay.best_event.event_type" :size="18" />
                {{ currentDay?.best_event?.score ?? 0 }}
              </span>
              <button class="sheet-close-btn" @click.stop="onCloseSheet" aria-label="关闭">✕</button>
            </div>
          </div>
          <!-- ② 0分事件拒绝原因 (去重) -->
          <div v-if="zeroScoreReasons.length" class="half-reject-reasons">
            <span
              v-for="(reason, idx) in zeroScoreReasons"
              :key="idx"
              class="reject-tag"
            >❌ {{ reason }}</span>
          </div>
          <!-- ③ 四段时段评分 -->
          <TimePeriodBar
            v-if="periodScores.length"
            :periods="periodScores"
          />
          <!-- ④ 七日迷你趋势 -->
          <MiniTrend
            v-if="currentForecast?.daily"
            :daily="currentForecast.daily"
            :selected-date="selectedDate"
            @select="onTrendDateSelect"
          />
          <!-- ⑤ 当日事件摘要 + 上拉提示 -->
          <div v-if="currentDay?.events?.length" class="half-events-summary">
            <div v-for="evt in activeEvents" :key="evt.event_type" class="half-event-chip">
              <EventIcon :event-type="evt.event_type" :size="16" />
              <span class="chip-name">{{ evt.display_name || evt.event_type }}</span>
              <span class="chip-score">{{ evt.score }}</span>
            </div>
          </div>
          <div class="half-expand-hint">{{ isTouchDevice ? '↑ 上拉查看完整报告' : '点击查看完整报告' }}</div>
        </div>
      </template>

      <!-- 全展态: 七日预测 -->
      <template #full>
        <div v-if="currentViewpoint" ref="sheetContentRef" class="full-content">
          <!-- 紧凑头部: 景点名 + 日期 + 摘要 + 事件徽章 -->
          <div class="full-header">
            <div class="full-header__top">
              <h2 class="full-vp-name">{{ currentViewpoint.name }}</h2>
              <span class="full-date">{{ formatFullDate(currentDay?.date) }}</span>
              <button class="sheet-close-btn sheet-close-btn--full" @click.stop="onCloseSheet" aria-label="关闭">✕</button>
            </div>
            <div class="full-header__summary" v-if="currentDay?.summary">{{ currentDay.summary }}</div>
            <div class="full-header__chips" v-if="currentDay?.events?.length">
              <div v-for="evt in currentDay.events" :key="evt.event_type" class="full-chip">
                <EventIcon :event-type="evt.event_type" :size="16" />
                <ScoreRing :score="evt.score" size="sm" />
                <StatusBadge :status="evt.status" />
              </div>
            </div>
          </div>
          <!-- 日期导航条 -->
          <MiniTrend
            v-if="currentForecast?.daily"
            :daily="currentForecast.daily"
            :selected-date="selectedDate"
            @select="onTrendDateSelect"
          />
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
import { ref, computed, onMounted, watch, onActivated, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useViewpointStore } from '@/stores/viewpoints'
import { useRouteStore } from '@/stores/routes'
import { convertToGCJ02 } from '@/composables/useCoordConvert'
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
import TimePeriodBar from '@/components/forecast/TimePeriodBar.vue'
import MiniTrend from '@/components/forecast/MiniTrend.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import { useTimePeriod } from '@/composables/useTimePeriod'

function formatFullDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`
}


const router = useRouter()
const vpStore = useViewpointStore()
const routeStore = useRouteStore()

const mapRef = ref(null)
const sheetRef = ref(null)
const sheetContentRef = ref(null)
const mapInstance = ref(null)

// 地图默认配置 (川西中心, 手机端缩小一级确保所有景点可见)
const isMobileViewport = window.innerWidth < 768
const mapOptions = {
  zoom: isMobileViewport ? 7 : 8,
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

// 四段时段评分
const { getPeriodScores } = useTimePeriod()

// reject_reason 英译中映射
const REASON_ZH_MAP = {
  'cloud': '云量',
  'avg_cloud': '平均云量',
  'cloud_base': '云底',
  'temp': '温度',
  'precip': '降水',
  'wind': '风速',
  'visibility': '能见度',
}

function translateReason(raw) {
  // 将 "cloud=68%" 转为 "云量=68%"
  return raw.replace(/^(\w+)=/, (_, key) => {
    return (REASON_ZH_MAP[key] || key) + '='
  })
}

// 0 分事件拒绝原因 (去重 + 中文化，最多 3 个)
const zeroScoreReasons = computed(() => {
  const reasons = (currentDay.value?.events ?? [])
    .filter(e => e.score === 0 && e.reject_reason)
    .map(e => e.reject_reason)
  // 去重
  const unique = [...new Set(reasons)]
  return unique.slice(0, 3).map(translateReason)
})

// 时段评分 (依赖 timeline)
const periodScores = computed(() => {
  if (!currentTimeline.value?.hourly) return []
  return getPeriodScores(currentTimeline.value.hourly)
})

// 当日活跃事件 (分数 > 0，供半展态摘要)
const activeEvents = computed(() =>
  (currentDay.value?.events ?? [])
    .filter(e => e.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
)


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

// 观景台排名等级映射 (Top/标准/低优先级)
const vpRankMap = computed(() => {
  const ranked = filteredViewpoints.value
    .map(vp => ({ id: vp.id, score: getBestScore(vp.id) }))
    .sort((a, b) => b.score - a.score)
  const map = {}
  ranked.forEach((item, idx) => {
    if (idx < 5 || item.score >= 80) map[item.id] = 'top'
    else if (item.score >= 50) map[item.id] = 'standard'
    else map[item.id] = 'low'
  })
  return map
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
    .slice(0, 5)
})

// 获取某个观景台在选中日期的最佳评分
function getBestScore(vpId) {
  const forecast = vpStore.forecasts[vpId]
  if (!forecast) return 0
  const day = forecast.daily?.find(d => d.date === selectedDate.value)
    ?? forecast.daily?.[0]
  return day?.best_event?.score ?? day?.events?.[0]?.score ?? 0
}

// 获取某个观景台在选中日期的最佳事件类型
function getBestEvent(vpId) {
  const forecast = vpStore.forecasts[vpId]
  if (!forecast) return null
  const day = forecast.daily?.find(d => d.date === selectedDate.value)
    ?? forecast.daily?.[0]
  return day?.best_event?.event_type ?? null
}

// === 事件处理 ===

function onMapReady(map) {
  mapInstance.value = map
}

async function onMarkerClick(vp) {
  // 选中观景台 → 地图飞行 → Bottom Sheet 弹至半展
  await vpStore.selectViewpoint(vp.id)
  // 自动加载当前日期的 timeline 数据
  if (vpStore.selectedDate) {
    await vpStore.selectDate(vpStore.selectedDate)
  }

  // 先切换到半展态，让 BottomSheet 测量内容高度
  sheetState.value = 'half'

  // 等待 nextTick 让 BottomSheet 完成高度测量
  await nextTick()

  const map = mapRef.value?.getMap?.()
  if (map) {
    const AMap = window.AMap
    const [gcjLon, gcjLat] = await convertToGCJ02(AMap, vp.location.lon, vp.location.lat)
    const vh = window.innerHeight
    // 获取 header 实际高度
    const headerEl = document.querySelector('.map-top-bar')
    const headerHeight = headerEl?.offsetHeight ?? 56
    // 获取 sheet 实际高度（半展态，通过 expose 获取）
    const sheetHeight = sheetRef.value?.currentHeight ?? vh * 0.35
    // 可见地图区域 = 视口 - header - sheet
    const visibleHeight = vh - headerHeight - sheetHeight
    // 标记应在可见区域的垂直中心
    // 可见区域中心相对于视口中心的偏移
    const visibleCenterY = headerHeight + visibleHeight / 2
    const viewportCenterY = vh / 2
    const offsetPixels = viewportCenterY - visibleCenterY
    // 在目标缩放级别下计算经纬度偏移
    const targetZoom = 12
    // 高德地图在 zoom 级别下每像素对应的纬度近似值
    const latPerPixel = 360 / (256 * Math.pow(2, targetZoom))
    const latOffset = offsetPixels * latPerPixel
    map.setZoomAndCenter(targetZoom, [gcjLon, gcjLat - latOffset], true, 800)
  }
}

function onRecommendSelect(rec) {
  onMarkerClick(rec.viewpoint)
}

const isTouchDevice = computed(() => 'ontouchstart' in window || navigator.maxTouchPoints > 0)

function onCloseSheet() {
  sheetState.value = 'collapsed'
  vpStore.clearSelection()
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
  bottom: calc(20vh + 16px);
  z-index: 90;
}

@media (max-width: 767px) {
  .map-screenshot-btn {
    right: 12px;
    bottom: calc(20vh + 12px);
  }
}

.half-content,
.full-content {
  padding: 16px;
}

.full-header {
  margin-bottom: 12px;
}

.full-header__top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.full-vp-name {
  font-size: var(--text-lg, 18px);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.full-date {
  font-size: var(--text-sm, 14px);
  color: var(--text-secondary);
  white-space: nowrap;
}

.full-header__summary {
  font-size: var(--text-sm, 14px);
  font-weight: 500;
  color: var(--text-primary);
  margin-top: 4px;
}

.full-header__chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.full-chip {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary, #F9FAFB);
  font-size: var(--text-xs);
}

.half-content {
  cursor: pointer;
}

.half-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.half-vp-name {
  font-weight: 700;
  font-size: var(--text-base, 16px);
  color: var(--color-text-dark, #374151);
}

.half-title-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.half-best-score {
  font-weight: 700;
  font-size: var(--text-lg, 18px);
}

.sheet-close-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full, 9999px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(0, 0, 0, 0.05);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary, #6B7280);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast, 0.15s);
  flex-shrink: 0;
}

.sheet-close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--text-primary, #374151);
}

.sheet-close-btn--full {
  margin-left: auto;
}

.half-reject-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.reject-tag {
  font-size: var(--text-xs, 12px);
  color: var(--color-text-secondary, #9CA3AF);
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 8px;
  border-radius: 4px;
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

/* 不再需要 grid 布局 — BottomSheet 是 position: fixed，
   不参与正常文档流，map 应全屏 */

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

.half-events-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.half-event-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  font-size: var(--text-xs, 12px);
}

.chip-name {
  color: var(--text-primary, #E5E7EB);
}

.chip-score {
  font-weight: 700;
  color: var(--color-primary, #3B82F6);
}

.half-expand-hint {
  text-align: center;
  margin-top: 16px;
  font-size: var(--text-xs, 12px);
  color: var(--text-muted, #94A3B8);
  opacity: 0.6;
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
