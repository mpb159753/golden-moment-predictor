<template>
  <div class="breakdown-bar" v-if="segments.length > 0">
    <div class="breakdown-bar__track">
      <div
        v-for="(seg, idx) in segments"
        :key="seg.key"
        class="breakdown-bar__segment"
        :style="{ width: seg.widthPct + '%' }"
        :title="`${seg.label} ${seg.score}/${seg.max}`"
      >
        <div
          class="breakdown-bar__fill"
          :style="{ width: seg.fillPct + '%', backgroundColor: seg.color }"
        />
        <span v-if="seg.showLabel" class="breakdown-bar__label">
          {{ seg.label }} {{ seg.score }}
        </span>
      </div>
    </div>
    <span class="breakdown-bar__total">{{ totalScore }}/{{ totalMax }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  breakdown: { type: Object, required: true },
  labelMap: { type: Object, default: () => ({}) },
  total: { type: Number, default: 0 },
})

const segmentColors = [
  'hsl(210, 75%, 45%)',  // 蓝（深）
  'hsl(150, 65%, 38%)',  // 绿（深）
  'hsl(35, 80%, 42%)',   // 橙（深）
  'hsl(280, 60%, 45%)',  // 紫（深）
  'hsl(0, 70%, 45%)',    // 红（深）
]

const totalMax = computed(() => {
  if (props.total > 0) return props.total
  return Object.values(props.breakdown).reduce((sum, item) => sum + item.max, 0)
})

const totalScore = computed(() =>
  Object.values(props.breakdown).reduce((sum, item) => sum + item.score, 0)
)

const segments = computed(() => {
  const entries = Object.entries(props.breakdown)
  const maxSum = totalMax.value
  if (maxSum === 0) return []

  return entries.map(([key, item], idx) => {
    const widthPct = (item.max / maxSum) * 100
    const fillPct = item.max > 0 ? (item.score / item.max) * 100 : 0
    const label = props.labelMap[key] ?? key
    return {
      key,
      label,
      score: item.score,
      max: item.max,
      widthPct,
      fillPct,
      color: segmentColors[idx % segmentColors.length],
      showLabel: true,
    }
  })
})
</script>

<style scoped>
.breakdown-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breakdown-bar__track {
  flex: 1;
  display: flex;
  height: 20px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-secondary, #F3F4F6);
}

.breakdown-bar__segment {
  position: relative;
  height: 100%;
  border-right: 1px solid rgba(255, 255, 255, 0.3);
}

.breakdown-bar__fill {
  height: 100%;
  transition: width 0.6s var(--ease-out-expo);
}

.breakdown-bar__label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: white;
  text-shadow:
    0 0 3px rgba(0, 0, 0, 0.6),
    0 1px 2px rgba(0, 0, 0, 0.5),
    1px 0 2px rgba(0, 0, 0, 0.3),
    -1px 0 2px rgba(0, 0, 0, 0.3);
  white-space: nowrap;
  overflow: hidden;
}

.breakdown-bar__total {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
</style>
