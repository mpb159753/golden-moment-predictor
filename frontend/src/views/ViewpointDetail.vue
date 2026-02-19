<template>
  <div class="viewpoint-detail" ref="screenshotArea">
    <!-- 顶栏 -->
    <header class="detail-header">
      <button @click="$router.back()" class="back-btn">← 返回</button>
      <h1>{{ viewpoint?.name }}</h1>
      <button class="header-screenshot-btn" @click="handleHeaderScreenshot" title="截图">📷</button>
    </header>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-spinner">加载中...</div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <!-- 主内容 -->
    <main v-else>
      <UpdateBanner :meta="store.meta" />

      <TrendChart
        :daily="forecast?.daily ?? []"
        :selectedDate="selectedDate"
        @select="onDateSelect"
      />

      <!-- 当日摘要 -->
      <section v-if="currentDay">
        <DaySummary :day="currentDay" :clickable="false" />
      </section>

      <!-- 0 分事件拒绝原因 -->
      <div v-if="zeroScoreReasons.length" class="reject-reasons">
        <div v-for="(evt, idx) in zeroScoreReasons" :key="idx" class="reject-reason">
          <EventIcon :event-type="evt.event_type" :size="16" />
          <span>{{ evt.reject_reason }}</span>
        </div>
      </div>

      <!-- 时段评分 -->
      <section v-if="timeline">
        <TimePeriodBar :periods="periodScores" />
      </section>

      <!-- 事件列表 -->
      <section>
        <h2>景观预测</h2>
        <EventList :events="currentDay?.events ?? []" showBreakdown />
      </section>

      <!-- 逐时天气表 -->
      <section v-if="timeline">
        <HourlyWeatherTable :hourly="timeline.hourly" />
      </section>

      <!-- 底部操作 -->
      <div class="detail-actions">
        <ScreenshotBtn :target="screenshotArea" />
        <button @click="showShareCard = true" class="share-btn">分享</button>
      </div>
    </main>

    <!-- 分享卡片 -->
    <ShareCard
      :visible="showShareCard"
      :viewpoint="viewpoint"
      :day="currentDay"
      @close="showShareCard = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useViewpointStore } from '@/stores/viewpoints'
import { useScreenshot } from '@/composables/useScreenshot'
import { useTimePeriod } from '@/composables/useTimePeriod'
import UpdateBanner from '@/components/layout/UpdateBanner.vue'
import TrendChart from '@/components/forecast/TrendChart.vue'
import DaySummary from '@/components/forecast/DaySummary.vue'
import EventList from '@/components/event/EventList.vue'
import EventIcon from '@/components/event/EventIcon.vue'
import TimePeriodBar from '@/components/forecast/TimePeriodBar.vue'
import HourlyWeatherTable from '@/components/forecast/HourlyWeatherTable.vue'
import ScreenshotBtn from '@/components/export/ScreenshotBtn.vue'
import ShareCard from '@/components/export/ShareCard.vue'

const props = defineProps({
  id: { type: String, required: true },
  date: { type: String, default: null },
})

const store = useViewpointStore()
const screenshotArea = ref(null)
const showShareCard = ref(false)
const { capture } = useScreenshot()
const { getPeriodScores } = useTimePeriod()

async function handleHeaderScreenshot() {
  const el = screenshotArea.value
  if (el) await capture(el, `gmp-${props.id}.png`)
}

// 计算属性
const viewpoint = computed(() => store.currentViewpoint)
const forecast = computed(() => store.currentForecast)
const loading = computed(() => store.loading)
const error = computed(() => store.error)
const timeline = computed(() => store.currentTimeline)

const selectedDate = computed({
  get: () => store.selectedDate,
  set: (val) => store.selectDate(val),
})

const currentDay = computed(() =>
  forecast.value?.daily?.find(d => d.date === selectedDate.value)
)

// 0 分事件拒绝原因
const zeroScoreReasons = computed(() =>
  (currentDay.value?.events ?? [])
    .filter(e => e.score === 0 && e.reject_reason)
    .slice(0, 3)
)

// 时段评分
const periodScores = computed(() => {
  if (!timeline.value?.hourly) return []
  return getPeriodScores(timeline.value.hourly)
})

// 初始化
onMounted(async () => {
  await store.selectViewpoint(props.id)
  if (props.date) {
    await store.selectDate(props.date)
  }
})

// 监听路由参数变化
watch(() => props.id, async (newId) => {
  await store.selectViewpoint(newId)
})

function onDateSelect(date) {
  store.selectDate(date)
}
</script>

<style scoped>
.viewpoint-detail {
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

.header-screenshot-btn {
  background: none;
  border: none;
  font-size: var(--text-lg);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}

.header-screenshot-btn:hover {
  background: var(--bg-overlay);
}

.back-btn {
  background: none;
  border: none;
  font-size: var(--text-base);
  color: var(--color-primary);
  cursor: pointer;
}

section {
  margin-bottom: 24px;
}

section h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.reject-reasons {
  margin-bottom: 16px;
}

.reject-reason {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: var(--text-sm);
  color: var(--text-secondary, #9CA3AF);
}

.detail-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 20px 0;
}

.share-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  font-size: var(--text-sm);
}
</style>
