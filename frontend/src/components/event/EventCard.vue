<template>
  <div class="event-card">
    <!-- 头部: 图标 + 名称 + 评分环 -->
    <div class="event-card__header">
      <div class="event-card__title">
        <EventIcon :eventType="event.event_type" :size="28" />
        <span class="event-card__name">{{ event.display_name }}</span>
      </div>
      <ScoreRing :score="event.score" size="sm" />
    </div>

    <!-- 时间窗口 -->
    <div class="event-card__time" v-if="event.time_window">
      {{ event.time_window }}
    </div>

    <!-- 状态和置信度标签 -->
    <div class="event-card__badges">
      <StatusBadge :status="event.status" />
      <span v-if="event.confidence" class="event-card__confidence">
        {{ confidenceLabel }}
      </span>
    </div>

    <!-- 天气条件列表 -->
    <ul class="event-card__conditions" v-if="event.conditions?.length">
      <li v-for="(condition, i) in event.conditions" :key="i">
        {{ condition }}
      </li>
    </ul>

    <!-- 评分明细 (可折叠) -->
    <div class="event-card__breakdown" v-if="showBreakdown && event.score_breakdown">
      <div class="event-card__breakdown-title">评分明细</div>
      <ScoreBar
        v-for="(detail, key) in event.score_breakdown"
        :key="key"
        :label="breakdownLabel(key)"
        :score="detail.score"
        :max="detail.max"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'
import ScoreBar from '@/components/score/ScoreBar.vue'

const props = defineProps({
  event: { type: Object, required: true },
  showBreakdown: { type: Boolean, default: false },
})

const confidenceMap = {
  'High': '高置信',
  'Medium': '中置信',
  'Low': '低置信',
}

// 已知评分维度的中文映射；未匹配的 key 将直接显示英文原值作为 fallback
const breakdownLabelMap = {
  light_path: '光路通畅',
  target_visible: '目标可见',
  local_clear: '本地晴朗',
}

const confidenceLabel = computed(() => confidenceMap[props.event.confidence] ?? props.event.confidence)

function breakdownLabel(key) {
  return breakdownLabelMap[key] ?? key
}
</script>

<style scoped>
.event-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-card);
}

.event-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.event-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.event-card__name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.event-card__time {
  margin-top: 4px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.event-card__badges {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.event-card__confidence {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.event-card__conditions {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  border-top: 1px solid var(--border-light, #E5E7EB);
  padding-top: 12px;
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
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light, #E5E7EB);
}

.event-card__breakdown-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
</style>
