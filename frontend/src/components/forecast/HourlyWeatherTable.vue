<template>
  <div class="hourly-weather-table">
    <div class="collapse-header" @click="expanded = !expanded">
      <span class="collapse-title">逐时天气</span>
      <span class="collapse-arrow" :class="{ open: expanded }">▸</span>
    </div>
    <div v-if="expanded" class="weather-rows">
      <div
        v-for="row in filteredHourly"
        :key="row.hour"
        class="weather-row"
      >
        <span class="weather-time">{{ row.time }}</span>
        <span class="weather-emoji">{{ weatherEmoji(row.weather.weather_icon) }}</span>
        <span class="weather-temp">{{ row.weather.temperature }}°C</span>
        <span class="weather-cloud">云{{ row.weather.cloud_cover }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  hourly: { type: Array, required: true },
})

const expanded = ref(false)

const WEATHER_EMOJI = {
  clear: '☀️',
  partly_cloudy: '⛅',
  cloudy: '☁️',
  rain: '🌧️',
  snow: '❄️',
}

function weatherEmoji(icon) {
  return WEATHER_EMOJI[icon] ?? '🌤️'
}

const filteredHourly = computed(() =>
  props.hourly.filter(h => h.weather && h.weather.weather_icon)
)
</script>

<style scoped>
.hourly-weather-table {
  border-radius: 12px;
  overflow: hidden;
}

.collapse-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.04);
  transition: background 0.2s;
}

.collapse-header:hover {
  background: rgba(255, 255, 255, 0.08);
}

.collapse-arrow {
  transition: transform 0.2s;
  font-size: 12px;
}

.collapse-arrow.open {
  transform: rotate(90deg);
}

.weather-rows {
  padding: 4px 0;
}

.weather-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  font-size: 13px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.weather-row:last-child {
  border-bottom: none;
}

.weather-time {
  width: 50px;
  font-variant-numeric: tabular-nums;
  color: rgba(255, 255, 255, 0.7);
}

.weather-emoji {
  width: 24px;
  text-align: center;
}

.weather-temp {
  width: 60px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.weather-cloud {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}
</style>
