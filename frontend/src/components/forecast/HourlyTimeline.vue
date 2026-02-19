<template>
  <div class="hourly-timeline">
    <div class="hourly-timeline__scroll" ref="scrollRef">
      <div class="hourly-timeline__track">
        <!-- 时间刻度 -->
        <div class="hourly-timeline__hours">
          <div
            v-for="h in hourly"
            :key="h.hour"
            class="hourly-timeline__hour-tick"
            :class="{
              'hourly-timeline__hour-tick--unsafe': !h.safety_passed,
              'hourly-timeline__hour-tick--current': h.hour === cachedCurrentHour,
            }"
          >
            {{ h.hour }}
          </div>
        </div>

        <!-- 事件区间条 -->
        <div
          v-for="(lane, idx) in eventLanes"
          :key="idx"
          class="hourly-timeline__lane"
        >
          <div class="hourly-timeline__lane-label">{{ lane.label }}</div>
          <div class="hourly-timeline__lane-bar">
            <div
              v-for="seg in lane.segments"
              :key="seg.startHour"
              class="hourly-timeline__segment"
              :style="{
                left: `${segmentLeft(seg.startHour)}%`,
                width: `${segmentWidth(seg.startHour, seg.endHour)}%`,
                backgroundColor: seg.color,
              }"
              :title="`${lane.label} ${seg.startHour}:00-${seg.endHour}:00 (${seg.score}分)`"
            />
          </div>
        </div>

        <!-- 当前时刻指示线 -->
        <div
          v-if="cachedCurrentHour >= minHour && cachedCurrentHour < maxHour"
          class="hourly-timeline__now-line"
          :style="{ left: `${nowLinePosition}%` }"
        />
      </div>
    </div>

    <!-- 天气概要 -->
    <div v-if="weatherSummary" class="hourly-timeline__weather">
      {{ weatherSummary }}
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { EVENT_COLORS, EVENT_NAMES } from '@/constants/eventMeta'

const props = defineProps({
  hourly: { type: Array, default: () => [] },
})

const scrollRef = ref(null)

// 缓存当前小时值，避免重复创建 Date 对象
const cachedCurrentHour = new Date().getHours()

/** 从 hourly 数据中提取事件连续区间 */
const eventLanes = computed(() => {
  if (!props.hourly.length) return []

  // 收集所有出现过的 event_type
  const typeMap = new Map()
  props.hourly.forEach(h => {
    ;(h.events_active || []).forEach(e => {
      if (!typeMap.has(e.event_type)) {
        typeMap.set(e.event_type, [])
      }
      typeMap.get(e.event_type).push({ hour: h.hour, score: e.score })
    })
  })

  // 为每个类型生成连续区间
  const lanes = []
  typeMap.forEach((hourEntries, type) => {
    const segments = []
    hourEntries.sort((a, b) => a.hour - b.hour)

    let start = hourEntries[0].hour
    let end = hourEntries[0].hour
    let maxScore = hourEntries[0].score

    for (let i = 1; i < hourEntries.length; i++) {
      if (hourEntries[i].hour === end + 1) {
        end = hourEntries[i].hour
        maxScore = Math.max(maxScore, hourEntries[i].score)
      } else {
        segments.push({ startHour: start, endHour: end + 1, score: maxScore, color: EVENT_COLORS[type] || '#9CA3AF' })
        start = hourEntries[i].hour
        end = hourEntries[i].hour
        maxScore = hourEntries[i].score
      }
    }
    segments.push({ startHour: start, endHour: end + 1, score: maxScore, color: EVENT_COLORS[type] || '#9CA3AF' })

    lanes.push({
      type,
      label: EVENT_NAMES[type] || type,
      segments,
    })
  })

  return lanes
})

/** 小时范围 */
const minHour = computed(() => props.hourly.length ? props.hourly[0].hour : 0)
const maxHour = computed(() => props.hourly.length ? props.hourly[props.hourly.length - 1].hour + 1 : 24)
const totalHours = computed(() => maxHour.value - minHour.value)

function segmentLeft(startHour) {
  return totalHours.value > 0 ? ((startHour - minHour.value) / totalHours.value) * 100 : 0
}

function segmentWidth(startHour, endHour) {
  return totalHours.value > 0 ? ((endHour - startHour) / totalHours.value) * 100 : 0
}

const nowLinePosition = computed(() => {
  const h = cachedCurrentHour
  return totalHours.value > 0 ? ((h - minHour.value) / totalHours.value) * 100 : 0
})

/** 云量 → 天气图标映射 */
function weatherIcon(cloudCover) {
  if (cloudCover === undefined || cloudCover === null) return ''
  if (cloudCover <= 20) return '☀️'
  if (cloudCover <= 50) return '⛅'
  if (cloudCover <= 80) return '🌥️'
  return '☁️'
}

/** 云量 → 中文描述 */
function cloudDesc(cloudCover) {
  if (cloudCover === undefined || cloudCover === null) return ''
  if (cloudCover <= 10) return '晴'
  if (cloudCover <= 30) return '少云'
  if (cloudCover <= 60) return '多云'
  if (cloudCover <= 80) return '阴'
  return '密云'
}

/** 天气概要 (取中间时刻) */
const weatherSummary = computed(() => {
  if (!props.hourly.length) return ''
  const mid = props.hourly[Math.floor(props.hourly.length / 2)]
  if (!mid?.weather) return ''
  const w = mid.weather
  const temp = w.temperature_2m !== undefined ? `${Math.round(w.temperature_2m)}°C` : ''
  const icon = weatherIcon(w.cloud_cover_total)
  const cloud = cloudDesc(w.cloud_cover_total)
  const parts = [temp, icon, cloud].filter(Boolean)
  return parts.length ? `天气: ${parts.join(' ')}` : ''
})
</script>

<style scoped>
.hourly-timeline {
  padding: 12px 0;
}

.hourly-timeline__scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.hourly-timeline__track {
  position: relative;
  min-width: 600px;
  padding: 0 16px;
}

.hourly-timeline__hours {
  display: flex;
  border-bottom: 1px solid #E5E7EB;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.hourly-timeline__hour-tick {
  flex: 1;
  text-align: center;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 0;
}

/* 移动端：每隔一个显示时间刻度文字，避免水平重叠 */
@media (max-width: 640px) {
  .hourly-timeline__hour-tick:nth-child(odd) {
    font-size: 0;           /* 隐藏奇数刻度文字 */
  }
}

.hourly-timeline__hour-tick--unsafe {
  color: var(--text-muted);
  opacity: 0.5;
}

.hourly-timeline__hour-tick--current {
  color: var(--color-primary);
  font-weight: 700;
}

.hourly-timeline__lane {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.hourly-timeline__lane-label {
  width: 64px;
  flex-shrink: 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-align: right;
  padding-right: 8px;
}

.hourly-timeline__lane-bar {
  flex: 1;
  position: relative;
  height: 16px;
  background: #F3F4F6;
  border-radius: var(--radius-sm);
}

.hourly-timeline__segment {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: var(--radius-sm);
  opacity: 0.75;
}

.hourly-timeline__now-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-primary);
  z-index: 1;
}

.hourly-timeline__weather {
  margin-top: 8px;
  padding: 0 16px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
</style>
