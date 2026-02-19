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
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.trend-icon-cell.selected {
  background-color: rgba(255, 215, 0, 0.15);
  box-shadow: 0 0 0 1.5px rgba(255, 215, 0, 0.4);
}

.trend-icon-cell:hover {
  background-color: rgba(255, 255, 255, 0.08);
}
</style>
