<template>
  <div class="event-list">
    <TransitionGroup name="slide-up">
      <EventCard
        v-for="(event, index) in events"
        :key="event.event_type"
        :event="event"
        :showBreakdown="showBreakdown"
        :style="{ transitionDelay: `${index * 80}ms` }"
      />
    </TransitionGroup>
  </div>
</template>

<script setup>
import EventCard from '@/components/event/EventCard.vue'

defineProps({
  events: { type: Array, default: () => [] },
  showBreakdown: { type: Boolean, default: false },
})
</script>

<style scoped>
.event-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Staggered slide-up animation */
.slide-up-enter-active {
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.slide-up-leave-active {
  transition: all var(--duration-fast) ease-in;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
