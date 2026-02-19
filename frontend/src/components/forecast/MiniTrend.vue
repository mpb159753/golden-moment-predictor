<script setup>
import { useScoreColor } from '@/composables/useScoreColor'

const props = defineProps({
    daily: {
        type: Array,
        required: true,
    },
    selectedDate: {
        type: String,
        default: null,
    },
})

const emit = defineEmits(['select'])

const { getScoreColor } = useScoreColor()

function dayNumber(dateStr) {
    return parseInt(dateStr.split('-')[2], 10)
}

function scoreColorStyle(score) {
    const { color } = getScoreColor(score)
    return { color }
}
</script>

<template>
    <div class="mini-trend">
        <div
            v-for="day in daily"
            :key="day.date"
            class="trend-day"
            :class="{ selected: day.date === selectedDate }"
            @click="emit('select', day.date)"
        >
            <span class="trend-date">{{ dayNumber(day.date) }}</span>
            <span class="trend-score" :style="scoreColorStyle(day.best_event?.score ?? 0)">
                {{ day.best_event?.score ?? 0 }}
            </span>
        </div>
    </div>
</template>

<style scoped>
.mini-trend {
    display: flex;
    gap: 4px;
}

.trend-day {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 4px 2px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
}

.trend-day:hover {
    background: rgba(255, 255, 255, 0.08);
}

.trend-day.selected {
    background: rgba(59, 130, 246, 0.2);
    box-shadow: inset 0 0 0 1.5px rgba(59, 130, 246, 0.5);
}

.trend-date {
    font-size: 11px;
    color: var(--color-text-secondary, #9CA3AF);
}

.trend-score {
    font-size: 14px;
    font-weight: 700;
}
</style>
