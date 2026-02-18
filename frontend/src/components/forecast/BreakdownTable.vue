<template>
  <div class="breakdown-table">
    <div v-for="(item, key) in breakdown" :key="key" class="breakdown-table__row">
      <ScoreBar
        :label="dimensionName(key)"
        :score="item.score"
        :max="item.max"
      />
    </div>
    <div class="breakdown-table__total">
      <span>总分</span>
      <span class="breakdown-table__total-value">
        {{ totalScore }} / {{ totalMax }}
      </span>
    </div>
  </div>
</template>

<script setup>
import ScoreBar from '@/components/score/ScoreBar.vue'

defineProps({
  breakdown: { type: Object, default: () => ({}) },
  totalScore: { type: Number, default: 0 },
  totalMax: { type: Number, default: 100 },
})

/** 评分维度 key → 中文名映射 */
const DIMENSION_NAMES = {
  light_path: '光路通畅',
  target_visible: '目标可见',
  local_clear: '本地晴朗',
  gap: '海拔差',
  density: '云层厚度',
  wind: '风力条件',
  temperature: '温度条件',
  humidity: '湿度条件',
  stability: '稳定性',
  precipitation: '降水条件',
  moon_phase: '月相',
  visibility: '能见度',
  cloud_cover: '云量',
}

function dimensionName(key) {
  return DIMENSION_NAMES[key] || key
}
</script>

<style scoped>
.breakdown-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.breakdown-table__row {
  padding: 0 4px;
}

.breakdown-table__total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px 0;
  border-top: 1px solid #E5E7EB;
  margin-top: 4px;
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--text-primary);
}

.breakdown-table__total-value {
  font-variant-numeric: tabular-nums;
}
</style>
