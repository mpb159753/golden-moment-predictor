<template>
  <div
    :class="['date-picker', { 'date-picker--wrap': wrap }]"
    tabindex="0"
    @keydown="handleKeydown"
  >
    <button
      v-for="date in dates"
      :key="date"
      class="date-picker__pill"
      :class="{ 'date-picker__pill--active': date === modelValue }"
      @click="$emit('update:modelValue', date)"
    >
      <span class="date-picker__date">{{ formatShortDate(date) }}</span>
      <span class="date-picker__weekday">{{ formatWeekday(date) }}</span>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: null },
  dates: { type: Array, default: () => [] },
  wrap: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

function formatShortDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatWeekday(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return WEEKDAYS[d.getDay()]
}

function handleKeydown(e) {
  if (!props.dates.length || !props.modelValue) return
  const currentIndex = props.dates.indexOf(props.modelValue)
  if (currentIndex === -1) return

  if (e.key === 'ArrowRight' && currentIndex < props.dates.length - 1) {
    emit('update:modelValue', props.dates[currentIndex + 1])
  } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
    emit('update:modelValue', props.dates[currentIndex - 1])
  }
}
</script>

<style scoped>
.date-picker {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 4px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  outline: none;
}

.date-picker::-webkit-scrollbar {
  display: none;
}

.date-picker--wrap {
  flex-wrap: wrap;
  overflow-x: visible;
  justify-content: center;
  gap: 6px;
}

.date-picker__pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-md, 12px);
  background: var(--bg-card, #fff);
  box-shadow: var(--shadow-card, 0 2px 8px rgba(0, 0, 0, 0.06));
  cursor: pointer;
  transition: all var(--duration-fast, 200ms) ease;
  font-family: inherit;
}

.date-picker--wrap .date-picker__pill {
  min-width: 0;
  width: calc(25% - 5px);
  padding: 6px 4px;
  box-sizing: border-box;
}

.date-picker__pill:hover {
  background: var(--color-primary-light, #93C5FD);
  color: #fff;
}

.date-picker__pill--active {
  background: var(--color-primary, #3B82F6);
  color: #fff;
  box-shadow: var(--shadow-elevated, 0 8px 24px rgba(0, 0, 0, 0.1));
}

.date-picker__date {
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  line-height: 1.2;
}

.date-picker__weekday {
  font-size: var(--text-xs, 0.75rem);
  opacity: 0.8;
  line-height: 1.2;
}
</style>
