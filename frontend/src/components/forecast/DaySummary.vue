<template>
  <div
    class="day-summary"
    :class="{ 'day-summary--clickable': clickable }"
    @click="clickable && $emit('select', day.date)"
  >
    <!-- 日期 -->
    <div class="day-summary__date">
      {{ formatDate(day.date) }}
    </div>

    <!-- 摘要文字 -->
    <div class="day-summary__text">{{ day.summary }}</div>

    <!-- 事件评分网格 -->
    <div class="day-summary__events">
      <div
        v-for="event in day.events"
        :key="event.event_type"
        class="day-summary__event-chip"
      >
        <EventIcon :eventType="event.event_type" :size="20" />
        <ScoreRing :score="event.score" size="sm" />
        <StatusBadge :status="event.status" />
      </div>
    </div>

    <!-- 组合推荐标签 -->
    <div v-if="comboTags.length" class="day-summary__tags">
      <span v-for="tag in comboTags" :key="tag.type" class="day-summary__tag">
        {{ tag.icon }} {{ tag.label }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useComboTags } from '@/composables/useComboTags'
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import StatusBadge from '@/components/score/StatusBadge.vue'

const props = defineProps({
  day: { type: Object, required: true },
  clickable: { type: Boolean, default: true },
})

defineEmits(['select'])

const { computeTags } = useComboTags()
const comboTags = computed(() => computeTags(props.day.events))

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00+08:00')
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`
}
</script>

<style scoped>
.day-summary {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
}

.day-summary--clickable {
  cursor: pointer;
  transition: box-shadow var(--duration-fast) var(--ease-out-expo);
}

.day-summary--clickable:hover {
  box-shadow: var(--shadow-elevated);
}

.day-summary__date {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.day-summary__text {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.day-summary__events {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.day-summary__event-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
}

.day-summary__tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.day-summary__tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  background: rgba(245, 158, 11, 0.1);
  color: var(--color-accent);
  font-weight: 500;
}
</style>
