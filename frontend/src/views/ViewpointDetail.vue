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

      <DatePicker
        v-model="selectedDate"
        :dates="availableDates"
      />

      <!-- 当日摘要 -->
      <section v-if="currentDay">
        <DaySummary :day="currentDay" :clickable="false" />
      </section>

      <!-- 事件列表 -->
      <section>
        <h2>景观预测</h2>
        <EventList :events="currentDay?.events ?? []" showBreakdown />
      </section>

      <!-- 逐时时间线 -->
      <section v-if="timeline">
        <h2>逐时详情</h2>
        <HourlyTimeline :hourly="timeline.hourly" />
      </section>

      <!-- 七日趋势 -->
      <section v-if="forecast">
        <h2>七日趋势</h2>
        <WeekTrend :daily="forecast.daily" @select="onDateSelect" />
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
import UpdateBanner from '@/components/layout/UpdateBanner.vue'
import DatePicker from '@/components/layout/DatePicker.vue'
import DaySummary from '@/components/forecast/DaySummary.vue'
import EventList from '@/components/event/EventList.vue'
import HourlyTimeline from '@/components/forecast/HourlyTimeline.vue'
import WeekTrend from '@/components/forecast/WeekTrend.vue'
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

const availableDates = computed(() =>
  forecast.value?.daily?.map(d => d.date) ?? []
)

const currentDay = computed(() =>
  forecast.value?.daily?.find(d => d.date === selectedDate.value)
)

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
