<template>
  <div class="route-panel">
    <div class="route-header">
      <h3>{{ route.name }} ({{ route.stops?.length ?? 0 }}站)</h3>
      <button class="close-btn" @click="emit('close')">✕</button>
    </div>

    <div class="stops-list">
      <div
        v-for="(stop, index) in route.stops"
        :key="stop.viewpoint_id"
        :ref="el => stopRefs[stop.viewpoint_id] = el"
        class="stop-item"
        :class="{ active: selectedStopId === stop.viewpoint_id }"
        @click="emit('select-stop', stop)"
      >
        <div class="stop-order">{{ index + 1 }}</div>
        <div class="stop-content">
          <div class="stop-title">
            <span class="stop-name">{{ stop.viewpoint_name }}</span>
            <ScoreRing :score="getStopScore(stop)" size="sm" />
            <EventIcon
              v-for="evt in getStopEvents(stop)"
              :key="evt.event_type"
              :type="evt.event_type"
              size="sm"
            />
          </div>
          <p v-if="stop.stay_note" class="stay-note">{{ stop.stay_note }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ScoreRing from '@/components/score/ScoreRing.vue'
import EventIcon from '@/components/event/EventIcon.vue'

const props = defineProps({
  route: { type: Object, required: true },
  selectedStopId: { type: String, default: null },
})

const emit = defineEmits(['close', 'select-stop'])

const stopRefs = ref({})

function getStopScore(stop) {
  return stop.forecast?.daily?.[0]?.best_event?.score ?? 0
}

function getStopEvents(stop) {
  return stop.forecast?.daily?.[0]?.events?.filter(e => e.score >= 50) ?? []
}

// 供父组件调用: 滚动到指定站点
function scrollToStop(vpId) {
  const el = stopRefs.value[vpId]
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

defineExpose({ scrollToStop })
</script>

<style scoped>
.route-panel {
  padding: 0 16px;
}

.route-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.route-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--text-lg);
  color: var(--text-muted);
  cursor: pointer;
}

.stops-list {
  padding: 8px 0;
}

.stop-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.stop-item:hover,
.stop-item.active {
  background: var(--bg-primary);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.stop-order {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 600;
  flex-shrink: 0;
}

.stop-content {
  flex: 1;
}

.stop-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stop-name {
  font-weight: 600;
  font-size: var(--text-sm);
}

.stay-note {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
