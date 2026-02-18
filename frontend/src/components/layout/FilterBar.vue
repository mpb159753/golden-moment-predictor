<template>
  <div class="filter-bar">
    <div class="filter-bar__events">
      <button
        class="filter-bar__pill"
        :class="{ 'filter-bar__pill--active': !selectedEvent }"
        @click="$emit('update:selectedEvent', null)"
      >
        全部
      </button>
      <button
        v-for="type in eventTypes"
        :key="type"
        class="filter-bar__pill"
        :class="{ 'filter-bar__pill--active': selectedEvent === type }"
        @click="$emit('update:selectedEvent', type)"
      >
        <EventIcon :event-type="type" :size="16" />
        <span>{{ eventName(type) }}</span>
      </button>
    </div>
    <div class="filter-bar__score">
      <span class="filter-bar__score-label">评分 ≥</span>
      <select
        class="filter-bar__select"
        :value="minScore"
        @change="$emit('update:minScore', Number($event.target.value))"
      >
        <option :value="0">0</option>
        <option :value="50">50</option>
        <option :value="80">80</option>
        <option :value="95">95</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import EventIcon from '@/components/event/EventIcon.vue'

defineProps({
  eventTypes: { type: Array, default: () => [] },
  selectedEvent: { type: String, default: null },
  minScore: { type: Number, default: 0 },
})

defineEmits(['update:selectedEvent', 'update:minScore'])

const EVENT_NAMES = {
  sunrise_golden_mountain: '日出金山',
  sunset_golden_mountain: '日落金山',
  cloud_sea: '云海',
  stargazing: '观星',
  frost: '雾凇',
  snow_tree: '树挂积雪',
  ice_icicle: '冰挂',
}

function eventName(type) {
  return EVENT_NAMES[type] ?? type
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.filter-bar::-webkit-scrollbar {
  display: none;
}

.filter-bar__events {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.filter-bar__pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--score-not-recommended, #9CA3AF);
  border-radius: var(--radius-full, 9999px);
  background: var(--bg-card, #fff);
  font-size: var(--text-xs, 0.75rem);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast, 200ms) ease;
  font-family: inherit;
  color: var(--text-secondary, #64748B);
}

.filter-bar__pill:hover {
  border-color: var(--color-primary, #3B82F6);
  color: var(--color-primary, #3B82F6);
}

.filter-bar__pill--active {
  background: var(--color-primary, #3B82F6);
  border-color: var(--color-primary, #3B82F6);
  color: #fff;
}

.filter-bar__score {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: auto;
}

.filter-bar__score-label {
  font-size: var(--text-xs, 0.75rem);
  color: var(--text-muted, #94A3B8);
  white-space: nowrap;
}

.filter-bar__select {
  padding: 4px 8px;
  border: 1px solid var(--score-not-recommended, #9CA3AF);
  border-radius: var(--radius-sm, 8px);
  background: var(--bg-card, #fff);
  font-size: var(--text-xs, 0.75rem);
  cursor: pointer;
  font-family: inherit;
  color: var(--text-primary, #1E293B);
}
</style>
