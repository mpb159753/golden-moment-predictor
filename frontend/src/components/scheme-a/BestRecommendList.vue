<template>
  <div class="best-recommend">
    <h3 class="section-title">
      <span class="title-icon">≡</span>
      今日最佳推荐
    </h3>
    <ul class="recommend-list">
      <li
        v-for="rec in recommendations"
        :key="rec.viewpoint.id"
        class="recommend-item"
        @click="emit('select', rec)"
      >
        <EventIcon :event-type="rec.event.event_type" :size="16" />
        <span class="vp-name">{{ rec.viewpoint.name }}</span>
        <ScoreRing :score="rec.score" size="sm" :showLabel="true" />
        <span class="event-label">{{ rec.event.event_label }}</span>
        <span class="arrow">→</span>
      </li>
    </ul>
    <p v-if="recommendations.length === 0" class="empty-hint">
      暂无推荐，数据加载中...
    </p>
  </div>
</template>

<script setup>
import EventIcon from '@/components/event/EventIcon.vue'
import ScoreRing from '@/components/score/ScoreRing.vue'

const props = defineProps({
  recommendations: { type: Array, default: () => [] },
})

const emit = defineEmits(['select'])
</script>

<style scoped>
.best-recommend {
  padding: 0 16px;
}

.section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-icon {
  font-size: var(--text-lg);
}

.recommend-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.recommend-item:hover {
  background: var(--bg-primary);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.recommend-item:last-child {
  border-bottom: none;
}

.vp-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--text-primary);
  min-width: 60px;
}

.event-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  flex: 1;
}

.arrow {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: 20px 0;
}
</style>
