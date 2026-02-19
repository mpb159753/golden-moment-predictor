<template>
  <div ref="chartRef" :style="{ width: '100%', height: `${height}px` }" />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { EVENT_COLORS, EVENT_NAMES } from '@/constants/eventMeta'

echarts.use([LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  daily: { type: Array, default: () => [] },
  height: { type: Number, default: 320 },
})

const emit = defineEmits(['select'])

const chartRef = ref(null)
let chart = null
let resizeObserver = null

/** 日期格式化: YYYY-MM-DD → "MM-DD 周X" */
function formatDateLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}-${dd} ${weekdays[d.getDay()]}`
}

function buildOption() {
  // 收集所有出现过的 event_type
  const eventTypes = new Set()
  props.daily.forEach(day => {
    day.events.forEach(e => eventTypes.add(e.event_type))
  })

  const dates = props.daily.map(d => formatDateLabel(d.date))

  const series = [...eventTypes].map(type => ({
    name: EVENT_NAMES[type] || type,
    type: 'line',
    smooth: true,
    areaStyle: { opacity: 0.1 },
    itemStyle: { color: EVENT_COLORS[type] || '#9CA3AF' },
    data: props.daily.map(day => {
      const event = day.events.find(e => e.event_type === type)
      return event ? event.score : null
    }),
  }))

  return {
    tooltip: { trigger: 'axis' },
    legend: {
      bottom: 0,
      type: 'scroll',        // 可滚动图例，避免多行重叠
      textStyle: { fontSize: 11 },
    },
    grid: { top: 10, right: 20, bottom: 70, left: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 35,           // 倾斜标签避免移动端重叠
        fontSize: 11,
        interval: 0,          // 显示所有标签
      },
    },
    yAxis: { type: 'value', min: 0, max: 100 },
    series,
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  chart.on('click', params => {
    emit('select', props.daily[params.dataIndex]?.date)
  })

  // 监听容器大小变化，自适应图表尺寸
  resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
})

watch(() => props.daily, () => {
  chart?.setOption(buildOption())
}, { deep: true })

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>
