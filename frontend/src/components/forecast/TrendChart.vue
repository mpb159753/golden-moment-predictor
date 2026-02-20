<template>
  <div class="trend-chart">
    <div ref="chartRef" :style="{ width: '100%', height: `${chartHeight}px` }" />
    <div class="trend-icons">
      <div
        v-for="(day, idx) in daily"
        :key="day.date"
        class="trend-icon-cell"
        :class="{ selected: day.date === selectedDate }"
        @click="$emit('select', day.date)"
      >
        <EventIcon
          v-if="day.best_event"
          :event-type="day.best_event.event_type"
          :size="20"
        />
        <span class="trend-icon-date">{{ formatShortDate(day.date) }}</span>
        <span class="trend-icon-score">{{ day.best_event?.score ?? 0 }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useScoreColor } from '@/composables/useScoreColor'
import EventIcon from '@/components/event/EventIcon.vue'

echarts.use([BarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  daily: { type: Array, required: true },
  selectedDate: { type: String, default: '' },
  chartHeight: { type: Number, default: 180 },
})

defineEmits(['select'])

const { getScoreColor } = useScoreColor()

const chartRef = ref(null)
let chart = null
let resizeObserver = null

function formatDateLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const mm = String(d.getMonth() + 1)
  const dd = String(d.getDate())
  return `${mm}/${dd}`
}

function formatShortDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}/${dd}`
}

function buildOption() {
  const dates = props.daily.map(d => formatDateLabel(d.date))
  const scores = props.daily.map(d => d.best_event?.score ?? 0)

  const barColors = scores.map((s, i) => {
    const { color } = getScoreColor(s)
    const isSelected = props.daily[i].date === props.selectedDate
    return isSelected ? color : color + '80' // 80 = 50% alpha hex
  })

  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 10, bottom: 30, left: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
    },
    series: [{
      type: 'bar',
      data: scores.map((s, i) => ({
        value: s,
        itemStyle: { color: barColors[i] },
        label: {
          show: true,
          position: 'top',
          formatter: `${s}`,
          fontSize: 10,
        },
      })),
    }],
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  chart.on('click', params => {
    // This is handled by ECharts click on the bar
  })

  resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  if (chartRef.value) {
    resizeObserver.observe(chartRef.value)
  }
})

watch(
  () => [props.daily, props.selectedDate],
  () => {
    chart?.setOption(buildOption())
  },
  { deep: true }
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style scoped>
.trend-chart {
  width: 100%;
}

.trend-icons {
  display: flex;
  justify-content: space-around;
  padding: 4px 40px 4px 40px;
}

.trend-icon-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 40px;
}

.trend-icon-cell.selected {
  background-color: rgba(255, 215, 0, 0.22);
  box-shadow: 0 0 0 2.5px rgba(255, 215, 0, 0.7);
}

.trend-icon-cell.selected .trend-icon-score {
  color: var(--color-primary);
  font-weight: 700;
}

.trend-icon-cell.selected .trend-icon-date {
  color: var(--color-primary);
  font-weight: 600;
}

.trend-icon-cell:hover {
  background-color: rgba(255, 255, 255, 0.08);
}

.trend-icon-date {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.trend-icon-score {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
</style>
