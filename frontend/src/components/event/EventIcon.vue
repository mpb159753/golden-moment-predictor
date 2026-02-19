<template>
  <span
    class="event-icon"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      color: colored ? eventColor : 'currentColor',
    }"
    :title="eventName"
  >
    <component :is="iconComponent" v-if="iconComponent" />
  </span>
</template>

<script setup>
import { computed } from 'vue'

import SunriseGoldenMountain from '@/assets/icons/sunrise-golden-mountain.svg'
import SunsetGoldenMountain from '@/assets/icons/sunset-golden-mountain.svg'
import CloudSea from '@/assets/icons/cloud-sea.svg'
import Stargazing from '@/assets/icons/stargazing.svg'
import Frost from '@/assets/icons/frost.svg'
import SnowTree from '@/assets/icons/snow-tree.svg'
import IceIcicle from '@/assets/icons/ice-icicle.svg'
import ClearSky from '@/assets/icons/clear-sky.svg'

const props = defineProps({
  eventType: { type: String, required: true },
  size: { type: Number, default: 24 },
  colored: { type: Boolean, default: true },
})

/**
 * event_type → 配置映射
 */
const EVENT_CONFIG = {
  sunrise_golden_mountain: { color: '#FF8C00', name: '日出金山', icon: SunriseGoldenMountain },
  sunset_golden_mountain:  { color: '#FF4500', name: '日落金山', icon: SunsetGoldenMountain },
  cloud_sea:               { color: '#87CEEB', name: '云海',     icon: CloudSea },
  stargazing:              { color: '#4A0E8F', name: '观星',     icon: Stargazing },
  frost:                   { color: '#B0E0E6', name: '雾凇',     icon: Frost },
  snow_tree:               { color: '#E0E8EF', name: '树挂积雪', icon: SnowTree },
  ice_icicle:              { color: '#ADD8E6', name: '冰挂',     icon: IceIcicle },
  clear_sky:               { color: '#FFB300', name: '晴天',     icon: ClearSky },
}

const config = computed(() => EVENT_CONFIG[props.eventType] ?? { color: '#9CA3AF', name: props.eventType, icon: null })
const eventColor = computed(() => config.value.color)
const eventName = computed(() => config.value.name)
const iconComponent = computed(() => config.value.icon)
</script>

<style scoped>
.event-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.event-icon :deep(svg) {
  width: 100%;
  height: 100%;
}
</style>
