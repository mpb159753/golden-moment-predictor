<template>
  <div class="score-ring" :class="[`score-ring--${size}`]">
    <svg :width="diameter" :height="diameter" :viewBox="`0 0 ${diameter} ${diameter}`">
      <!-- 背景环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        stroke="#E5E7EB"
        :stroke-width="strokeWidth"
      />
      <!-- 评分环 -->
      <circle
        :cx="center" :cy="center" :r="radius"
        fill="none"
        :stroke="colorInfo.gradient ? `url(#scoreGradient-${uid})` : colorInfo.color"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        :style="animated ? { transition: 'stroke-dashoffset 1s var(--ease-out-expo)' } : {}"
        :transform="`rotate(-90, ${center}, ${center})`"
      />
      <!-- 渐变定义 (仅 Perfect 使用) -->
      <defs v-if="colorInfo.gradient">
        <linearGradient :id="`scoreGradient-${uid}`" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#FFD700" />
          <stop offset="100%" stop-color="#FF8C00" />
        </linearGradient>
      </defs>
    </svg>
    <!-- 中心数字 -->
    <span v-if="showLabel" class="score-ring__label" :style="{ fontSize: labelSize }">
      {{ score }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
  score: { type: Number, default: 0 },
  size: { type: String, default: 'md', validator: v => ['sm', 'md', 'lg', 'xl'].includes(v) },
  showLabel: { type: Boolean, default: true },
  animated: { type: Boolean, default: true },
})

const { getScoreColor } = useScoreColor()

// 每个实例唯一 ID，避免多实例渐变 ID 冲突
const uid = Math.random().toString(36).slice(2, 8)

const sizeMap = {
  sm:  { diameter: 32, strokeWidth: 3, labelSize: '12px' },
  md:  { diameter: 48, strokeWidth: 4, labelSize: '16px' },
  lg:  { diameter: 72, strokeWidth: 5, labelSize: '24px' },
  xl:  { diameter: 120, strokeWidth: 6, labelSize: '48px' },
}

const config = computed(() => sizeMap[props.size])
const diameter = computed(() => config.value.diameter)
const strokeWidth = computed(() => config.value.strokeWidth)
const labelSize = computed(() => config.value.labelSize)
const center = computed(() => diameter.value / 2)
const radius = computed(() => center.value - strokeWidth.value)
const circumference = computed(() => 2 * Math.PI * radius.value)
const clampedScore = computed(() => Math.max(0, Math.min(100, props.score)))
const dashOffset = computed(() => circumference.value * (1 - clampedScore.value / 100))
const colorInfo = computed(() => getScoreColor(clampedScore.value))
</script>

<style scoped>
.score-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.score-ring__label {
  position: absolute;
  font-weight: 700;
  color: var(--text-primary);
}
</style>
