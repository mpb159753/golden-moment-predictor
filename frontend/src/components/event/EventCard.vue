<template>
  <div class="event-card">
    <!-- 头部: 单行紧凑布局 -->
    <div class="event-card__header">
      <div class="event-card__meta">
        <EventIcon :eventType="event.event_type" :size="22" />
        <span class="event-card__name">{{ event.display_name }}</span>
        <span class="event-card__time" v-if="event.time_window">{{ event.time_window }}</span>
        <StatusBadge :status="event.status" />
        <span v-if="event.confidence" class="event-card__confidence">
          {{ confidenceLabel }}
        </span>
      </div>
      <ScoreRing :score="event.score" size="sm" />
    </div>

    <!-- 天气条件列表 -->
    <ul class="event-card__conditions" v-if="event.conditions?.length">
      <li v-for="(condition, i) in event.conditions" :key="i">
        {{ condition }}
      </li>
    </ul>

    <!-- 评分明细 (单行叠放柱状图) -->
    <div class="event-card__breakdown" v-if="showBreakdown && event.score_breakdown">
      <div class="event-card__breakdown-title">评分明细</div>
      <BreakdownBar
        :breakdown="event.score_breakdown"
        :label-map="breakdownLabelMap"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import BreakdownBar from '@/components/score/BreakdownBar.vue'

const props = defineProps({
  event: { type: Object, required: true },
  showBreakdown: { type: Boolean, default: false },
})

const confidenceMap = {
  'High': '高置信',
  'Medium': '中置信',
  'Low': '低置信',
}

// 评分维度中文简称映射（缩短以适应柱状图内显示）
const breakdownLabelMap = {
  light_path: '光路',
  target_visible: '目标',
  local_clear: '本地',
  temperature: '温度',
  moisture: '湿度',
  wind: '风力',
  cloud: '云量',
  base: '基础',
  gap: '落差',
  density: '密度',
  mid_structure: '中层',
  cloud_cover: '云量',
  precipitation: '降水',
  visibility: '能见',
  snow_signal: '积雪',
  clear_weather: '晴好',
  stability: '稳定',
  water_input: '水源',
  freeze_strength: '冻结',
  view_quality: '观赏',
}

const confidenceLabel = computed(() => confidenceMap[props.event.confidence] ?? props.event.confidence)
</script>

<style scoped>
.event-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  box-shadow: var(--shadow-card);
}

.event-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.event-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

.event-card__name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.event-card__time {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

.event-card__confidence {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

.event-card__conditions {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  border-top: 1px solid var(--border-light, #E5E7EB);
  padding-top: 8px;
}

.event-card__conditions li {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  padding: 2px 0;
}

.event-card__conditions li::before {
  content: '• ';
  color: var(--text-muted);
}

.event-card__breakdown {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light, #E5E7EB);
}

.event-card__breakdown-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
</style>

