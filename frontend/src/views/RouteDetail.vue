<template>
  <div class="route-detail" ref="screenshotArea">
    <!-- 顶栏 -->
    <header class="detail-header">
      <button @click="router.back()" class="back-btn">← 返回</button>
      <h1>{{ route?.name }}</h1>
      <ScreenshotBtn :target="screenshotArea" :filename="`gmp-route-${id}.png`" />
    </header>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-spinner">加载中...</div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <!-- 主内容 -->
    <main v-else-if="routeForecast">
      <!-- 地图: 线路全貌 + 各站标记 -->
      <section class="route-map-section">
        <AMapContainer
          ref="mapRef"
          height="260px"
          @ready="onMapReady"
        >
          <RouteLine :stops="mapStops" :map="mapInstance" />
          <ViewpointMarker
            v-for="stop in mapStops"
            :key="stop.viewpoint_id"
            :viewpoint="{ ...stop, location: stop.location, name: stop.viewpoint_name }"
            :score="getStopBestScore(stop)"
            :map="mapInstance"
            @click="goToViewpoint(stop.viewpoint_id)"
          />
        </AMapContainer>
      </section>

      <!-- 站点列表 -->
      <section v-for="stop in routeForecast.stops" :key="stop.viewpoint_id" class="route-stop">
        <div class="route-stop__header">
          <span class="route-stop__order">{{ stop.order }}</span>
          <RouterLink
            :to="{ name: 'viewpoint-detail', params: { id: stop.viewpoint_id } }"
            class="route-stop__title"
          >
            {{ stop.viewpoint_name }}
          </RouterLink>
        </div>
        <p v-if="stop.stay_note" class="route-stop__note">{{ stop.stay_note }}</p>

        <!-- 当日摘要 (取 forecast.daily 第一天) -->
        <DaySummary
          v-if="getTodayForecast(stop)"
          :day="getTodayForecast(stop)"
          :clickable="true"
          @select="goToViewpoint(stop.viewpoint_id, $event)"
        />
      </section>

      <!-- 七日趋势: 各站对比 -->
      <section v-if="hasWeekData" class="route-trend-section">
        <h2>七日趋势对比</h2>
        <div v-for="stop in routeForecast.stops" :key="`trend-${stop.viewpoint_id}`" class="route-trend-item">
          <h3>{{ stop.viewpoint_name }}</h3>
          <WeekTrend
            :daily="stop.forecast?.daily ?? []"
            @select="(date) => goToViewpoint(stop.viewpoint_id, date)"
          />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useRouteStore } from '@/stores/routes'
import DaySummary from '@/components/forecast/DaySummary.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'
import AMapContainer from '@/components/map/AMapContainer.vue'
import RouteLine from '@/components/map/RouteLine.vue'
import ViewpointMarker from '@/components/map/ViewpointMarker.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const store = useRouteStore()
const screenshotArea = ref(null)
const mapRef = ref(null)
const mapInstance = ref(null)

const route = computed(() => store.currentRoute)
const routeForecast = computed(() => store.currentForecast)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

// 地图站点数据 (需要 location 字段)
const mapStops = computed(() =>
  routeForecast.value?.stops?.filter(s => s.location) ?? []
)

// 是否有七日数据
const hasWeekData = computed(() =>
  routeForecast.value?.stops?.some(s => s.forecast?.daily?.length > 1)
)

function getTodayForecast(stop) {
  const today = new Date().toISOString().split('T')[0]
  return stop.forecast?.daily?.find(d => d.date === today) ?? stop.forecast?.daily?.[0] ?? null
}

function getStopBestScore(stop) {
  const day = getTodayForecast(stop)
  return day?.best_event?.score ?? 0
}

function goToViewpoint(viewpointId, date) {
  if (date) {
    router.push({ name: 'viewpoint-date', params: { id: viewpointId, date } })
  } else {
    router.push({ name: 'viewpoint-detail', params: { id: viewpointId } })
  }
}

function onMapReady(map) {
  mapInstance.value = map
}

onMounted(async () => {
  await store.selectRoute(props.id)
})

watch(() => props.id, async (newId) => {
  await store.selectRoute(newId)
})
</script>

<style scoped>
.route-detail {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
}

.detail-header h1 {
  font-size: var(--text-xl);
  font-weight: 700;
}

.back-btn {
  background: none;
  border: none;
  font-size: var(--text-base);
  color: var(--color-primary);
  cursor: pointer;
}

.route-map-section {
  margin-bottom: 24px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.route-stop {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.route-stop__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.route-stop__order {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: white;
  font-weight: 700;
  font-size: var(--text-sm);
}

.route-stop__title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
}

.route-stop__title:hover {
  text-decoration: underline;
}

.route-stop__note {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.route-trend-section {
  margin-bottom: 24px;
}

.route-trend-section h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.route-trend-item {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.route-trend-item h3 {
  font-size: var(--text-base);
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}
</style>
